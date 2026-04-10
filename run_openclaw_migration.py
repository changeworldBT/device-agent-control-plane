from __future__ import annotations

import argparse
import json
from pathlib import Path

from compat.openclaw_migration import DEFAULT_OPENCLAW_CONFIG, migrate_openclaw, write_local_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_OPENCLAW_CONFIG, help="path to OpenClaw openclaw.json")
    parser.add_argument("--workspace", type=Path, default=None, help="optional OpenClaw workspace path override")
    parser.add_argument("--write-local-config", action="store_true", help="write generated config to config/model-providers.local.json")
    parser.add_argument("--output", type=Path, default=None, help="override local config output path when writing")
    parser.add_argument("--force", action="store_true", help="overwrite an existing local config output")
    args = parser.parse_args()

    report = migrate_openclaw(config_path=args.config, workspace_path=args.workspace)

    if args.write_local_config:
        output_path = write_local_config(
            report["generated_config"],
            output_path=args.output if args.output is not None else None,
            force=args.force,
        )
        report["written_config_path"] = str(output_path)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
