# Portable Schema Drafts

These files are extracted from `../v3-design-freeze.html`.

Purpose:
- give implementation work a machine-readable draft surface
- keep semantics stable across languages and transports
- avoid re-deriving core objects from prose

Non-goals:
- not a frozen JSON Schema draft version
- not a protobuf/Avro/OpenAPI commitment
- not a database design
- not an IPC or event-bus implementation choice

Files:
- `common-enums.json`
- `core-objects.json`
- `execution-objects.json`
- `state-transitions.json`
- `compatibility-objects.json`
- `interaction-contract.json`
- `json-schema/`
- `examples/`
- `examples/flows/`
- `json-schema/task-replay.schema.json`

JSON Schema projection:
- `json-schema/` contains an implementation-friendly projection using JSON Schema 2020-12
- this is a convenience layer, not the canonical source
- if projection and prose diverge, `../v3-design-freeze.html` wins

Examples:
- `examples/` contains minimal payloads that reflect the frozen semantics
- these are intended for early integration, validation, and fixture building
- `examples/flows/` contains end-to-end replay fixtures for concrete task chains
- replay fixtures validate against `json-schema/task-replay.schema.json`

Validation:
- `python schemas/validate_examples.py`
- requires the local `jsonschema` package
- validates example payloads against the projected schemas in `json-schema/`

Rule:
- if any file here conflicts with `../v3-design-freeze.html`, the HTML spec wins
- these drafts exist to reduce implementation drift, not to replace the canonical freeze
