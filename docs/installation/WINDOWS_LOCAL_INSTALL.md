# Windows Local Installation — CAD Generator and Control Center

**Status:** local foreground launcher candidate, backed by the existing loopback-only CAD Generator API. This is a Python-installed local web application, not an MSI installer or Windows service.

## Requirements

- Windows 10/11, PowerShell, and Python 3.11 or newer.
- The repository declares Python `>=3.11`; CI currently validates Python 3.12. Python 3.14 meets the declared minimum but is not yet a dedicated CI matrix target.
- No paid service, cloud account, database server or third-party runtime dependency is required.

## Install from a repository checkout

Open PowerShell in the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

If PowerShell blocks activation, use a process-scoped policy change for this terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

To install the test and quality tools as well, use `python -m pip install -e ".[dev,quality]"`.

## Start the local application

```powershell
up-cad-generator
```

The launcher:
- Binds only to `127.0.0.1`; there is no host/wildcard/LAN option.
- Uses port `0` by default so Windows selects an available port. The actual port is printed at startup. A fixed port can be selected explicitly with `--port 8765`.
- Opens no browser automatically. Copy the printed Control Center URL into your browser.
- Generates a bearer token when `UP_CAD_BEARER_TOKEN` is not set. The token is printed once to stdout for the current process so it can be pasted into the Control Center's local token field. The launcher does not write it to an application file, URL, cookie or application audit log; however, terminal transcripts, shell logging, process supervisors or redirected stdout may capture it. Treat terminal output as secret and do not share it.
- If `UP_CAD_BEARER_TOKEN` is supplied, it must contain at least 32 UTF-8 bytes and is not echoed to the console.
- Stops and closes the listening socket when you press **Ctrl+C**.

The output includes both:
- `http://127.0.0.1:<port>/` — CAD Generator workbench.
- `http://127.0.0.1:<port>/control-center` — Control Center shell.

Use `up-cad-generator --help` to see the supported arguments. The equivalent module command is `python -m universal_platform.engineering.cad_generator_server`.

## Persistent data

By default, data is stored under:

```text
%LOCALAPPDATA%\UniversalPlatform\CADGenerator
```

The directory contains separate SQLite files for FeatureHistory revisions, FeatureArtifact cache and HTTP audit events. The data directory is independent of the current working directory. Override it explicitly with:

```powershell
up-cad-generator --data-dir "$env:LOCALAPPDATA\UniversalPlatform\CADGenerator"
```

The port is dynamic by default and may change after restart. The bearer token is also regenerated after restart unless you provide `UP_CAD_BEARER_TOKEN` in the current process environment.

## Security boundary

- Local-only HTTP over IPv4 loopback; do not configure port forwarding, LAN firewall exceptions, reverse proxies, SSH tunnels or public exposure.
- The bearer token is required for API requests, including health checks.
- Keep the token private. Anyone with the token and access to the local user account is inside this local trust boundary.
- The Control Center's current health check describes CAD Generator health only; it is not platform-wide health.
- This launcher does not start physical hardware, flash firmware, deploy software, or claim OS sandbox/resource isolation.

## Stop, troubleshoot and uninstall

- Press **Ctrl+C** in the terminal running the launcher.
- If `up-cad-generator` is not found, activate the repository's `.venv` and run `python -m pip install -e .` again.
- If startup reports an invalid token, unset or replace the current-shell environment variable: `Remove-Item Env:UP_CAD_BEARER_TOKEN`.
- If a selected fixed port is occupied, omit `--port` and let the OS choose a dynamic port.
- To remove the development environment, stop the service, run `deactivate`, then remove only the repository's `.venv` directory. The persistent data directory is intentionally retained; do not delete it unless you separately intend to remove user data.

## Verification

From the activated environment:

```powershell
python -m pytest -q tests/test_cad_generator_http_api.py tests/test_cad_generator_server.py
```

The repository's full acceptance suite and Windows Process Supervisor workflow remain the authoritative CI gates.
