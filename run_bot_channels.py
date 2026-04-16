from __future__ import annotations

import argparse
import json
from pathlib import Path

from channels.bot_config import load_bot_channel_config
from channels.bot_gateway import active_bot_config_path, list_channels, send_or_preview
from local_env import load_project_env


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=active_bot_config_path(), help="bot channel config path")
    parser.add_argument("--list", action="store_true", help="list configured channels")
    parser.add_argument("--channel", default=None, help="channel name; defaults to config.default_channel")
    parser.add_argument("--text", default="Device Agent test message", help="message text for preview or live send")
    parser.add_argument("--live", action="store_true", help="send using live channel credentials; default is dry-run preview")
    args = parser.parse_args()

    load_project_env()
    config = load_bot_channel_config(args.config)
    if args.list:
        print(json.dumps({"channels": list_channels(config)}, indent=2, ensure_ascii=False))
        return 0

    dispatch = send_or_preview(config, text=args.text, channel_name=args.channel, live=args.live)
    print(json.dumps(dispatch, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
