from __future__ import annotations

import argparse
import json

from scenarios.local_crm_runner import run_local_crm_scenario
from runtime_backend import (
    backend_argument_help,
    exit_backend_missing,
    normalize_backend,
    run_rust_bin,
    rust_backend_available,
)


def run_python() -> int:
    result = run_local_crm_scenario()
    summary = {
        "replay_id": result.fixture.replay_id,
        "events": len(result.event_log),
        "task_terminal": result.state.current_task_terminal(result.fixture.task_id),
        "approvals": len(result.state.approvals),
        "recoveries": len(result.state.recoveries),
        "verified_facts": [fact_id for fact_id, fact in sorted(result.state.facts.items()) if fact["status"] == "verified"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("auto", "python", "rust"), default="auto", help=backend_argument_help())
    args = parser.parse_args()

    backend = normalize_backend(args.backend)
    if backend == "rust":
        if not rust_backend_available():
            return exit_backend_missing()
        return run_rust_bin("run_local_crm")
    return run_python()


if __name__ == "__main__":
    raise SystemExit(main())
