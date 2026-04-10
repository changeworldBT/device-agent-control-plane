from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime_backend import resolve_cargo, rust_env
from runtime_backend import configured_rust_target


def main() -> int:
    cargo = resolve_cargo()
    env = rust_env(cargo)
    command = [str(cargo), "test", "--lib", "--tests"]
    target = configured_rust_target()
    if target:
        command.extend(["--target", target])
    commands = [command]
    for command in commands:
        print(f">>> {' '.join(command)}", flush=True)
        completed = subprocess.run(command, cwd=ROOT, check=False, env=env)
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
