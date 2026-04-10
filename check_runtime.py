from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

COMMANDS = [
    [sys.executable, str(ROOT / "schemas" / "validate_examples.py")],
    [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"],
    [sys.executable, str(ROOT / "run_replays.py")],
    [sys.executable, str(ROOT / "run_local_crm_scenario.py")],
    [sys.executable, str(ROOT / "run_local_crm_compensation.py")],
    [sys.executable, str(ROOT / "run_http_crm_scenario.py")],
    [sys.executable, str(ROOT / "run_http_crm_compensation.py")],
    [sys.executable, str(ROOT / "rust-core" / "check_skeleton.py")],
    [sys.executable, str(ROOT / "rust-core" / "check_rust.py")],
    [sys.executable, str(ROOT / "rust-core" / "check_parity.py")],
]


def main() -> int:
    for command in COMMANDS:
        rendered = " ".join(command)
        print(f">>> {rendered}", flush=True)
        completed = subprocess.run(command, cwd=ROOT, check=False)
        if completed.returncode != 0:
            print(f"FAILED: {rendered}")
            return completed.returncode
    print("Replay runtime checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
