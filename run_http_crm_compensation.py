from __future__ import annotations

import tempfile
from pathlib import Path

from scenarios.http_crm_runner import run_http_crm_with_compensation, summarize_http_result
from scenarios.mock_http_crm_server import MockHttpCrmServer


def main() -> int:
    root = Path(__file__).resolve().parent
    seed_dir = root / "sandbox" / "local-crm" / "seed"
    runtime_dir = Path(tempfile.gettempdir()) / "device-agent-doc-http-compensation"
    with MockHttpCrmServer(seed_dir=seed_dir) as server:
        result = run_http_crm_with_compensation(base_url=server.base_url, runtime_dir=runtime_dir, reset_remote=server.reset)
        print(summarize_http_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
