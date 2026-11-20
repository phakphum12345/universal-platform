import subprocess
import sys
import time

from universal_platform.runtime.resources.durable_allocator import (
    DurableResourceAllocator,
)
from universal_platform.runtime.resources.models import ResourceMetric


def test_durable_allocator_serializes_capacity_across_os_processes(tmp_path):
    capacity = (ResourceMetric("cpu.cores", 2, "cores"),)
    pool_id = "multiprocess-race"
    DurableResourceAllocator(tmp_path, capacity, pool_id=pool_id)
    start_file = tmp_path / "start-all"
    worker_count = 6
    script = r"""
import sys
import time
from pathlib import Path
from universal_platform.runtime.resources.durable_allocator import DurableResourceAllocator
from universal_platform.runtime.resources.models import ResourceMetric

root = Path(sys.argv[1])
index = sys.argv[2]
start_file = Path(sys.argv[3])
(root / ("ready-" + index)).touch()
deadline = time.monotonic() + 20
while not start_file.exists():
    if time.monotonic() >= deadline:
        raise TimeoutError("parent did not release process barrier")
    time.sleep(0.01)

allocator = DurableResourceAllocator(
    root,
    (ResourceMetric("cpu.cores", 2, "cores"),),
    pool_id="multiprocess-race",
)
try:
    allocator.allocate(
        "owner-" + index,
        (ResourceMetric("cpu.cores", 1, "cores"),),
        ttl_seconds=None,
    )
except RuntimeError as error:
    if "resource capacity exceeded" not in str(error):
        raise
    print("FULL")
else:
    print("ACQUIRED")
"""
    children = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(tmp_path), str(index), str(start_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(worker_count)
    ]
    try:
        deadline = time.monotonic() + 20
        while not all((tmp_path / f"ready-{index}").exists() for index in range(worker_count)):
            if time.monotonic() >= deadline:
                raise TimeoutError("worker processes did not reach the start barrier")
            if any(child.poll() is not None for child in children):
                raise RuntimeError("a worker process exited before the start barrier")
            time.sleep(0.01)
        start_file.touch()
        results = [child.communicate(timeout=30) for child in children]
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)

    outcomes = []
    for child, (stdout, stderr) in zip(children, results):
        assert child.returncode == 0, stderr
        outcomes.append(stdout.strip())

    assert outcomes.count("ACQUIRED") == 2
    assert outcomes.count("FULL") == worker_count - 2

    recovered = DurableResourceAllocator(tmp_path, capacity, pool_id=pool_id)
    assert len(recovered.active_leases()) == 2
    assert recovered.available()[0].value == 0
