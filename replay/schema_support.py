from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "schemas" / "json-schema"
EXAMPLE_DIR = ROOT / "schemas" / "examples"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def build_registry() -> Registry:
    registry = Registry()
    for schema_path in SCHEMA_DIR.glob("*.json"):
        schema_obj = load_json(schema_path)
        resource = Resource.from_contents(schema_obj)
        registry = registry.with_resource(schema_path.name, resource)
        registry = registry.with_resource(schema_path.resolve().as_uri(), resource)
    return registry


def validate_against_schema(instance: Any, schema_name: str) -> None:
    schema_path = SCHEMA_DIR / schema_name
    validator = Draft202012Validator(load_json(schema_path), registry=build_registry())
    errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.absolute_path))
    if not errors:
        return

    lines = []
    for error in errors:
        path = "/".join(str(part) for part in error.absolute_path) or "<root>"
        lines.append(f"{path}: {error.message}")
    raise ValueError(f"{schema_name} validation failed:\n" + "\n".join(lines))
