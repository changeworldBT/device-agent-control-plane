from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from scenarios.http_crm_runner import run_http_crm_scenario, summarize_http_result
from scenarios.mock_http_crm_server import MockHttpCrmServer
from runtime_backend import (
    backend_argument_help,
    exit_backend_missing,
    normalize_backend,
    run_rust_bin,
    rust_backend_available,
)


def run_python() -> int:
    root = Path(__file__).resolve().parent
    seed_dir = root / "sandbox" / "local-crm" / "seed"
    runtime_dir = Path(tempfile.gettempdir()) / "device-agent-doc-http-scenario"
    with MockHttpCrmServer(seed_dir=seed_dir) as server:
        result = run_http_crm_scenario(base_url=server.base_url, runtime_dir=runtime_dir, reset_remote=server.reset)
        print(summarize_http_result(result))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("auto", "python", "rust"), default="auto", help=backend_argument_help())
    args = parser.parse_args()

    backend = normalize_backend(args.backend)
    if backend == "rust":
        if not rust_backend_available():
            return exit_backend_missing()
        return run_rust_bin("run_http_crm")
    return run_python()


if __name__ == "__main__":
    raise SystemExit(main())
