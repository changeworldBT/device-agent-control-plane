from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent


def run_json(command: list[str], *, cwd: Path) -> object:
    print(f">>> {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.returncode != 0:
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        raise SystemExit(completed.returncode)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        print(completed.stderr, file=sys.stderr, end="")
        raise SystemExit(f"failed to parse JSON output from {' '.join(command)}: {exc}") from exc


def main() -> int:
    cases = [
        (
            [sys.executable, str(PROJECT_ROOT / "run_replays.py"), "--backend", "python"],
            [sys.executable, str(PROJECT_ROOT / "run_replays.py"), "--backend", "rust"],
            "replay summary",
        ),
        (
            [sys.executable, str(PROJECT_ROOT / "run_local_crm_scenario.py"), "--backend", "python"],
            [sys.executable, str(PROJECT_ROOT / "run_local_crm_scenario.py"), "--backend", "rust"],
            "local crm scenario summary",
        ),
        (
            [sys.executable, str(PROJECT_ROOT / "run_local_crm_compensation.py"), "--backend", "python"],
            [sys.executable, str(PROJECT_ROOT / "run_local_crm_compensation.py"), "--backend", "rust"],
            "local crm compensation summary",
        ),
    ]

    for python_command, rust_command, label in cases:
        python_output = run_json(python_command, cwd=PROJECT_ROOT)
        rust_output = run_json(rust_command, cwd=PROJECT_ROOT)
        if python_output != rust_output:
            print(f"parity mismatch for {label}", file=sys.stderr)
            print("python:", json.dumps(python_output, indent=2, ensure_ascii=False), file=sys.stderr)
            print("rust:", json.dumps(rust_output, indent=2, ensure_ascii=False), file=sys.stderr)
            return 1

    print("Rust and Python summaries are in parity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
