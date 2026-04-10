from __future__ import annotations

import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"


def load_cargo() -> dict:
    with (ROOT / "Cargo.toml").open("rb") as handle:
        return tomllib.load(handle)


def declared_modules() -> list[str]:
    lib_rs = (SRC / "lib.rs").read_text(encoding="utf-8")
    return re.findall(r"^pub mod ([a-zA-Z0-9_]+);$", lib_rs, flags=re.MULTILINE)


def check() -> int:
    cargo = load_cargo()
    package_name = cargo.get("package", {}).get("name")
    if package_name != "device-agent-core":
        print(f"unexpected crate name: {package_name}")
        return 1

    missing = []
    for module in declared_modules():
        if not (SRC / f"{module}.rs").exists():
            missing.append(module)

    if missing:
        print(f"missing module files: {', '.join(missing)}")
        return 1

    if not (ROOT / "README.md").exists():
        print("missing README.md")
        return 1

    print("Rust structure checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(check())
