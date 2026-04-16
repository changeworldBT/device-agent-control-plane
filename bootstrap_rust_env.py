from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from runtime_backend import DEFAULT_RUST_TARGET, configured_rust_target, resolve_cargo


def required_rust_target() -> str:
    return configured_rust_target() or DEFAULT_RUST_TARGET


def resolve_rustc(cargo: Path | None = None) -> Path:
    candidates: list[Path] = []

    if cargo is not None:
        sibling = cargo.parent / "rustc.exe"
        if sibling.exists():
            candidates.append(sibling)

    which_rustc = shutil.which("rustc")
    if which_rustc:
        candidates.append(Path(which_rustc))

    candidates.append(Path.home() / ".cargo" / "bin" / "rustc.exe")

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate
    raise FileNotFoundError("no rustc executable found in PATH or standard installation locations")


def resolve_rustup(cargo: Path | None = None) -> Path:
    candidates: list[Path] = []

    if cargo is not None:
        sibling = cargo.parent / "rustup.exe"
        if sibling.exists():
            candidates.append(sibling)

    which_rustup = shutil.which("rustup")
    if which_rustup:
        candidates.append(Path(which_rustup))

    candidates.append(Path.home() / ".cargo" / "bin" / "rustup.exe")

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate
    raise FileNotFoundError("no rustup executable found in PATH or standard installation locations")


def installed_targets(rustup: Path) -> set[str]:
    completed = subprocess.run(
        [str(rustup), "target", "list", "--installed"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "failed to list installed Rust targets")
    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def target_is_usable(rustc: Path, target: str) -> bool:
    completed = subprocess.run(
        [str(rustc), "--print", "target-libdir", "--target", target],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return False

    target_libdir = completed.stdout.strip()
    return bool(target_libdir) and Path(target_libdir).exists()


def print_version(label: str, command: list[str]) -> None:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode == 0:
        print(f"{label}: {completed.stdout.strip()}")
        return
    stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
    print(f"{label}: {stderr}", file=sys.stderr)


def ensure_required_target(rustup: Path, target: str) -> int:
    installed = installed_targets(rustup)
    if target in installed:
        print(f"required target already installed: {target}")
        return 0

    print(f"installing missing target: {target}")
    completed = subprocess.run([str(rustup), "target", "add", target], check=False)
    if completed.returncode != 0:
        print(f"failed to install target: {target}", file=sys.stderr)
        return completed.returncode

    print(f"installed target: {target}")
    return 0


def main() -> int:
    try:
        cargo = resolve_cargo()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        print("install Rust first, for example with rustup-init or a standard Rust bundle.", file=sys.stderr)
        return 1

    try:
        rustc = resolve_rustc(cargo)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        print("install rustc or ensure it is available in PATH.", file=sys.stderr)
        return 1

    target = required_rust_target()
    print(f"cargo: {cargo}")
    print(f"rustc: {rustc}")
    print(f"required target: {target}")
    print_version("cargo version", [str(cargo), "--version"])
    print_version("rustc version", [str(rustc), "--version"])

    if target_is_usable(rustc, target):
        print(f"required target already usable: {target}")
        return 0

    try:
        rustup = resolve_rustup(cargo)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        print("rustup is required only when the target is missing and needs installation.", file=sys.stderr)
        return 1

    print(f"rustup: {rustup}")
    print_version("rustup version", [str(rustup), "--version"])

    try:
        return ensure_required_target(rustup, target)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
