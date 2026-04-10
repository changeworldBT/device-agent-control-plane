from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parent

PAIRS = [
    ("json-schema/task.schema.json", "examples/task.example.json"),
    ("json-schema/task-node.schema.json", "examples/task-node.example.json"),
    ("json-schema/fact.schema.json", "examples/fact.example.json"),
    ("json-schema/capability-grant.schema.json", "examples/capability-grant.example.json"),
    ("json-schema/action-spec.schema.json", "examples/action-spec.example.json"),
    ("json-schema/execution-receipt.schema.json", "examples/execution-receipt.example.json"),
    ("json-schema/verification-result.schema.json", "examples/verification-result.example.json"),
    ("json-schema/state-capsule.schema.json", "examples/state-capsule.example.json"),
    ("json-schema/event-envelope.schema.json", "examples/event-envelope.example.json"),
    ("json-schema/task-replay.schema.json", "examples/flows/research-brief-flow.json"),
    ("json-schema/task-replay.schema.json", "examples/flows/crm-followup-flow.json"),
]


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_registry() -> Registry:
    registry = Registry()
    for schema_path in (ROOT / "json-schema").glob("*.json"):
        schema_obj = load_json(schema_path)
        resource = Resource.from_contents(schema_obj)
        registry = registry.with_resource(schema_path.name, resource)
        registry = registry.with_resource(schema_path.resolve().as_uri(), resource)
    return registry


def main() -> int:
    registry = build_registry()
    failures = []

    for schema_rel, example_rel in PAIRS:
        schema_path = ROOT / schema_rel
        example_path = ROOT / example_rel
        schema = load_json(schema_path)
        example = load_json(example_path)

        validator = Draft202012Validator(schema, registry=registry)
        errors = sorted(validator.iter_errors(example), key=lambda e: list(e.absolute_path))

        if errors:
            failures.append((schema_path.name, example_path.name, errors))
            continue

        print(f"OK {example_path.name} against {schema_path.name}")

    if not failures:
        return 0

    for schema_name, example_name, errors in failures:
        print(f"FAIL {example_name} against {schema_name}")
        for error in errors:
            path = "/".join(str(x) for x in error.absolute_path) or "<root>"
            print(f"  {path}: {error.message}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
