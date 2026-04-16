from __future__ import annotations

import argparse

from local_env import load_project_env
from ui_backend import serve_ui


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1", help="host for the local UI server")
    parser.add_argument("--port", type=int, default=8765, help="port for the local UI server")
    parser.add_argument("--no-open", action="store_true", help="do not open the browser automatically")
    args = parser.parse_args()

    load_project_env()
    return serve_ui(host=args.host, port=args.port, open_browser=not args.no_open)


if __name__ == "__main__":
    raise SystemExit(main())
