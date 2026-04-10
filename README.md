# Device Agent Control Plane

English | [中文](README.zh-CN.md)

Developer-preview repository for a controlled device-agent execution core. The project defines and validates a control-plane slice for device-agent work: event-backed state, scoped grants, explicit approvals, verification, recovery, and replayable execution.

## Status

This is a developer preview, not a finished end-user product.

Working today:
- Append-only event log and materialized state projector.
- Task, node, fact, grant, approval, receipt, verification, and recovery semantics.
- Replay execution for the built-in research and CRM fixtures.
- Python oracle runtime for proving semantics first.
- Rust core that matches the Python oracle on the validated slice.
- Local filesystem CRM scenario with controlled side effects and compensation.
- Mock HTTP CRM scenario with controlled remote-style side effects and compensation.
- Python/Rust parity checks for replay, local CRM, and mock HTTP CRM paths.

Not finished:
- General-purpose remote adapters beyond the validated mock HTTP CRM slice.
- Browser automation.
- Multi-agent orchestration beyond the design/spec level.
- Packaging, installer, and end-user UX.

## Architecture

The repository is intentionally split into an oracle runtime and a Rust implementation:

- Python oracle: source of semantic truth for the current slice. It keeps the behavior easy to inspect and compare while the Rust core catches up.
- Rust core: production-direction implementation of the same control-plane behavior.
- Replay fixtures: deterministic flow inputs used to prove state transitions and parity.
- Scenario runners: local filesystem and mock HTTP CRM flows that exercise real side effects under scoped grants and recovery rules.

The design favors falsifiable behavior over broad claims. A path is considered part of the validated slice only when it is covered by schema validation, tests, and Python/Rust parity where applicable.

## Repository Layout

- `v3-design-freeze.html`: canonical design snapshot.
- `schemas/`: JSON schemas, examples, and replay fixtures.
- `runtime/`, `control/`, `domain/`, `selector/`, `verification/`: Python oracle runtime.
- `execution/`: Python local and mock HTTP execution adapters.
- `scenarios/`: Python scenario runners and mock HTTP CRM server.
- `rust-core/`: Rust implementation, tests, and CLI bins.
- `sandbox/local-crm/seed/`: deterministic seed data for local and mock HTTP CRM scenarios.
- `tests/`: Python validation tests.

## Requirements

- Python 3.13+
- Rust toolchain for the Rust-first path
- Windows is the currently validated environment

The top-level scripts support `--backend auto|python|rust`. `auto` prefers Rust when a working cargo toolchain is available and falls back to Python otherwise.

## Quick Start

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

## Validation

The canonical validation command is:

```powershell
python .\check_runtime.py
```

It runs:
- Schema validation for examples and replay fixtures.
- Python unit tests.
- Top-level replay, local CRM, and mock HTTP CRM entrypoints.
- Rust structure checks.
- Rust tests.
- Python/Rust parity checks.

GitHub Actions runs the same validation gate on Windows for every push and pull request.

## Publishing Position

This repo should be evaluated as infrastructure and reference implementation:

- A control-plane specification.
- A replay-driven semantic reference.
- A Rust migration guarded by Python parity.
- A developer preview of bounded side-effect execution and recovery.

It is not positioned as a polished product UI or a general-purpose agent runtime yet.

## License

MIT
