from __future__ import annotations

import argparse

from cli_welcome import render_welcome
from ui_backend import serve_ui


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interface", choices=("cli", "ui"), default="cli", help="choose the CLI or local UI surface")
    parser.add_argument("--host", default="127.0.0.1", help="host for --interface ui")
    parser.add_argument("--port", type=int, default=8765, help="port for --interface ui")
    parser.add_argument("--no-open", action="store_true", help="do not open the browser for --interface ui")
    parser.add_argument("--no-color", action="store_true", help="render the CLI welcome banner without ANSI colors")
    args = parser.parse_args()

    if args.interface == "ui":
        return serve_ui(host=args.host, port=args.port, open_browser=not args.no_open)

    print(render_welcome(color=not args.no_color))
    print()
    print("Choose UI later with: python .\\run_device_agent.py --interface ui")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
