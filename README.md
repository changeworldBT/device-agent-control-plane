# Device Agent Control Plane

Developer-preview repository for a controlled device-agent execution core.

This repo contains:
- the canonical design freeze and companion docs
- a Python oracle runtime used to prove semantics first
- a Rust core that now matches the Python oracle on the current validated slice
- replay fixtures, schemas, and local filesystem-backed scenarios

## Current Product Status

This is usable as a developer preview, not a finished end-user product.

What is already working:
- append-only event log plus materialized state projection
- task, fact, grant, approval, verification, and recovery semantics
- replay execution for the built-in research and CRM fixtures
- a real local workspace adapter with controlled side effects
- a mock HTTP CRM adapter with controlled remote-style side effects
- compensation execution for the local CRM scenario
- compensation execution for the mock HTTP CRM scenario
- Rust and Python parity checks on the validated slice

What is intentionally not finished:
- remote adapters
- browser automation
- multi-agent orchestration beyond the design/spec level
- packaging, installer, and end-user UX

## Repository Layout

- `v3-design-freeze.html`: canonical specification
- `schemas/`: JSON schemas, examples, replay fixtures
- `runtime/`, `control/`, `domain/`, `selector/`, `verification/`: Python oracle runtime
- `rust-core/`: Rust implementation of the same control-plane slice
- `sandbox/local-crm/seed/`: deterministic seed data for the local CRM scenario

## Quick Start

Requirements:
- Python 3.13+
- Rust toolchain if you want the Rust-first path

Validated on Windows.

Run the full validation gate:

```powershell
python .\check_runtime.py
```

Run replay summaries:

```powershell
python .\run_replays.py
python .\run_replays.py --backend python
python .\run_replays.py --backend rust
```

Run the local CRM scenario:

```powershell
python .\run_local_crm_scenario.py
python .\run_local_crm_compensation.py
```

Run the mock HTTP CRM scenario:

```powershell
python .\run_http_crm_scenario.py
python .\run_http_crm_compensation.py
```

Top-level scripts support `--backend auto|python|rust`. `auto` prefers Rust when a working cargo toolchain is present.

## Publishing Position

This repo is published as:
- a control-plane specification
- a replay-driven semantic reference
- a Rust migration in progress guarded by Python parity

It should be evaluated as infrastructure and reference implementation, not as a polished product UI.

## Validation Gate

The canonical validation command is:

```powershell
python .\check_runtime.py
```

GitHub Actions runs the same command on Windows for every push and pull request.

## License

MIT
