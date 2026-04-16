from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUST_CORE = ROOT / "rust-core"
RUST_CARGO_CONFIG = RUST_CORE / ".cargo" / "config.toml"
DEFAULT_RUST_TARGET = "x86_64-pc-windows-gnullvm"


def load_rust_cargo_config() -> dict:
    if not RUST_CARGO_CONFIG.exists():
        return {}
    with RUST_CARGO_CONFIG.open("rb") as handle:
        return tomllib.load(handle)


def configured_rust_target() -> str | None:
    value = os.environ.get("DEVICE_AGENT_RUST_TARGET", "").strip()
    if value:
        return value

    build = load_rust_cargo_config().get("build", {})
    if not isinstance(build, dict):
        return None

    configured = build.get("target")
    if isinstance(configured, str):
        configured = configured.strip()
        if configured:
            return configured
    return None


def project_target_dir() -> Path:
    return RUST_CORE / "target"


def candidate_cargo_paths() -> list[Path]:
    candidates: list[Path] = []

    which_cargo = shutil.which("cargo")
    if which_cargo:
        candidates.append(Path(which_cargo))

    program_files = Path("C:/Program Files")
    if program_files.exists():
        candidates.extend(sorted(program_files.glob("Rust stable LLVM */bin/cargo.exe"), reverse=True))
        candidates.extend(sorted(program_files.glob("Rust stable MSVC */bin/cargo.exe"), reverse=True))

    candidates.append(Path.home() / ".cargo" / "bin" / "cargo.exe")

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def resolve_cargo() -> Path:
    for candidate in candidate_cargo_paths():
        if candidate.exists():
            return candidate
    raise FileNotFoundError("no cargo executable found in PATH or standard installation locations")


def rust_backend_available() -> bool:
    try:
        return resolve_cargo().exists() and (RUST_CORE / "Cargo.toml").exists()
    except FileNotFoundError:
        return False


def resolve_rust_sysroot_bin(cargo: Path | None = None, *, target: str | None = None) -> Path | None:
    resolved = cargo or resolve_cargo()
    rustc = resolved.parent / "rustc.exe"
    if not rustc.exists():
        rustc = Path("rustc")

    effective_target = target or configured_rust_target() or DEFAULT_RUST_TARGET
    probe_env = os.environ.copy()
    probe_env["PATH"] = str(resolved.parent) + os.pathsep + probe_env.get("PATH", "")
    completed = subprocess.run(
        [str(rustc), "--print", "sysroot"],
        check=False,
        capture_output=True,
        text=True,
        env=probe_env,
    )
    if completed.returncode != 0:
        return None

    sysroot = Path(completed.stdout.strip())
    candidate = sysroot / "lib" / "rustlib" / effective_target / "bin"
    if candidate.exists():
        return candidate
    return None


def rust_env(cargo: Path | None = None) -> dict[str, str]:
    resolved = cargo or resolve_cargo()
    env = os.environ.copy()
    path_entries = [str(resolved.parent)]
    sysroot_bin = resolve_rust_sysroot_bin(resolved)
    if sysroot_bin is not None:
        path_entries.append(str(sysroot_bin))
    path_entries.append(env.get("PATH", ""))
    env["PATH"] = os.pathsep.join([entry for entry in path_entries if entry])
    return env


def normalize_backend(requested: str) -> str:
    if requested == "auto":
        return "rust" if rust_backend_available() else "python"
    return requested


def run_rust_bin(bin_name: str, args: list[str] | None = None) -> int:
    cargo = resolve_cargo()
    command = [str(cargo), "run", "--quiet", "--bin", bin_name]
    target = configured_rust_target()
    if target:
        command.extend(["--target", target])
    if args:
        command.extend(["--", *args])
    completed = subprocess.run(command, cwd=RUST_CORE, check=False, env=rust_env(cargo))
    return completed.returncode


def backend_argument_help() -> str:
    return "execution backend: auto prefers Rust when cargo and the project Rust configuration are available"


def backend_missing_message() -> str:
    return "Rust backend requested but no working cargo installation or project Rust configuration was found"


def exit_backend_missing() -> int:
    print(backend_missing_message(), file=sys.stderr)
    return 1
