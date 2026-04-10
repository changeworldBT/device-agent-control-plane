from __future__ import annotations

import argparse

from cli_welcome import render_welcome
from runtime_backend import (
    backend_argument_help,
    exit_backend_missing,
    normalize_backend,
    run_rust_bin,
    rust_backend_available,
)


def run_python(*, color: bool) -> int:
    print(render_welcome(color=color))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("auto", "python", "rust"), default="auto", help=backend_argument_help())
    parser.add_argument("--no-color", action="store_true", help="render the welcome banner without ANSI colors")
    args = parser.parse_args()

    backend = normalize_backend(args.backend)
    if backend == "rust":
        if not rust_backend_available():
            return exit_backend_missing()
        rust_args = ["--no-color"] if args.no_color else []
        return run_rust_bin("device_agent", rust_args)
    return run_python(color=not args.no_color)


if __name__ == "__main__":
    raise SystemExit(main())
