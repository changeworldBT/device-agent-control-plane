# device-agent-core

Rust implementation of the control-plane semantics first proven in the Python oracle runtime.

Scope:
- append-only event log
- materialized state projector
- fact time and freshness semantics
- task transition guards
- grant and approval guards
- selector scoring
- replay harness
- local workspace adapter
- local CRM scenario runner
- CLI bins for replay and local CRM scenarios

Non-goals in this phase:
- expanding product scope beyond the current control-plane slice
- removing the Python oracle or parity checks
- adding remote or browser adapters before the local path is stable

Local status:
- the crate compiles under the installed GNU/LLVM Rust bundle
- core semantics tests run via `check_rust.py`
- replay execution matches the Python oracle for the built-in fixtures
- local workspace and CRM compensation scenarios run with real filesystem side effects
- top-level Python entrypoints default to Rust when available and can still be forced to Python

Reference implementation used to derive semantics:
- `runtime/events/log.py`
- `runtime/projector/state.py`
- `replay/runner.py`
- `control/approvals/guards.py`
- `control/grants/guards.py`
- `domain/facts/semantics.py`
- `domain/tasks/guards.py`
- `selector/v0/scoring.py`
- `execution/local/workspace_adapter.py`

Current validation:
1. `python check_skeleton.py`
2. `python check_rust.py`
3. `python check_parity.py`

User-facing entrypoints:
1. `python ..\\run_replays.py`
2. `python ..\\run_local_crm_scenario.py`
3. `python ..\\run_local_crm_compensation.py`

All three support `--backend auto|python|rust`. The default is `auto`, which prefers Rust when a working cargo toolchain is present.

Suggested next step:
1. keep parity green while shifting user-facing execution toward Rust
2. migrate orchestration only when it reduces duplication without weakening the oracle fence
3. add the first non-local adapter only after the local Rust path remains stable
