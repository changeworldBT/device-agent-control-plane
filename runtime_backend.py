from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUST_CORE = ROOT / "rust-core"


def candidate_cargo_paths() -> list[Path]:
    candidates: list[Path] = []
    program_files = Path("C:/Program Files")
    if program_files.exists():
        candidates.extend(sorted(program_files.glob("Rust stable LLVM */bin/cargo.exe"), reverse=True))
        candidates.extend(sorted(program_files.glob("Rust stable MSVC */bin/cargo.exe"), reverse=True))
    candidates.append(Path.home() / ".cargo" / "bin" / "cargo.exe")
    return candidates


def resolve_cargo() -> Path:
    for candidate in candidate_cargo_paths():
        if candidate.exists():
            return candidate
    raise FileNotFoundError("no cargo executable found in known locations")


def rust_backend_available() -> bool:
    try:
        return resolve_cargo().exists() and (RUST_CORE / "Cargo.toml").exists()
    except FileNotFoundError:
        return False


def rust_env(cargo: Path | None = None) -> dict[str, str]:
    resolved = cargo or resolve_cargo()
    env = os.environ.copy()
    env["PATH"] = str(resolved.parent) + os.pathsep + env.get("PATH", "")
    return env


def normalize_backend(requested: str) -> str:
    if requested == "auto":
        return "rust" if rust_backend_available() else "python"
    return requested


def run_rust_bin(bin_name: str, args: list[str] | None = None) -> int:
    cargo = resolve_cargo()
    command = [str(cargo), "run", "--quiet", "--bin", bin_name]
    if args:
        command.extend(["--", *args])
    completed = subprocess.run(command, cwd=RUST_CORE, check=False, env=rust_env(cargo))
    return completed.returncode


def backend_argument_help() -> str:
    return "execution backend: auto prefers Rust when cargo and rust-core are available"


def backend_missing_message() -> str:
    return "Rust backend requested but no working cargo installation was found"


def exit_backend_missing() -> int:
    print(backend_missing_message(), file=sys.stderr)
    return 1
