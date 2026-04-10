from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from replay.schema_support import validate_against_schema


def load_bot_channel_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    validate_bot_channel_config(config)
    return config


def validate_bot_channel_config(config: Mapping[str, Any]) -> None:
    validate_against_schema(config, "bot-channel-config.schema.json")
    channels = config["channels"]
    default_channel = str(config["default_channel"])
    if default_channel not in channels:
        raise ValueError(f"default_channel references unknown channel: {default_channel}")
