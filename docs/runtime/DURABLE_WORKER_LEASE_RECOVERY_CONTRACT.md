## Implementation checkpoint — 2026-11-20

This section records candidate implementation state without changing the acceptance requirements below.

- **WP-09G-A — journal primitive:** integrated on the development branch by PR #257 at `2eff621e4ff24e98250bc085b2c652cd366a5e2e`.
- **WP-09G-B — durable allocator:** implemented and exact-head verified on PR #258 at `43aac3cbb3a42e8dd822ee5d56efcab1d1e01719`. A stacked integration candidate adds the `ResourceAllocatorPort` contract so `ModuleRuntime` can accept either the existing in-memory allocator or an explicitly host-injected `DurableResourceAllocator`. The durable allocator exposes its host-configured capacity through the same port.
- The stacked ModuleRuntime integration candidate is not merged or accepted. It preserves the default in-memory behavior and does not automatically select a durable storage root.
- Direct multiprocess allocator contention tests remain required; the PR #258 allocator concurrency test exercises multiple instances with threads.
- **WP-09G-C/D/E** remain not implemented: supervisor OS process identity hand-off, startup process-tree reconciliation, and authenticated/audited operator recovery.
- No sandbox, privilege separation, filesystem/network isolation, or OS CPU/memory/I/O enforcement is claimed.

The lifecycle remains IMPLEMENTED → VERIFIED → INTEGRATED → ACCEPTED. PR-head verification does not establish integration or acceptance.

---

