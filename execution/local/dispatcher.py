from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from replay.schema_support import validate_against_schema


def build_action_spec(*, task_id: str, node: dict[str, Any], action_id: str, occurred_at: datetime) -> dict[str, Any]:
    payload = {
        "action_id": action_id,
        "task_id": task_id,
        "node_id": node["node_id"],
        "action_type": node["node_type"],
        "required_capability": node["required_capabilities"][0] if node["required_capabilities"] else "structured.action",
        "target_scope": {
            "node_id": node["node_id"],
            "risk_class": node["risk_class"],
        },
        "inputs": {
            "objective": node["objective"],
        },
        "preconditions": {
            "node_state": node["state"],
        },
        "expected_artifacts": node.get("artifact_refs", []),
        "postconditions": {
            "evidence_of_done": node["evidence_of_done"],
        },
        "budget": {
            "max_minutes": 5,
            "max_retries": 1,
        },
        "idempotency_key": f"{action_id}:once:{occurred_at.isoformat()}",
    }
    validate_against_schema(payload, "action-spec.schema.json")
    return payload


def build_receipt(
    *,
    action_spec: dict[str, Any],
    grant: dict[str, Any],
    artifact_refs: list[str],
    occurred_at: datetime,
    executor_id: str,
    status: str = "succeeded_with_receipt",
) -> dict[str, Any]:
    payload = {
        "receipt_id": f"receipt_{action_spec['action_id']}",
        "action_id": action_spec["action_id"],
        "task_id": action_spec["task_id"],
        "node_id": action_spec["node_id"],
        "grant_id": grant["grant_id"],
        "executor_id": executor_id,
        "status": status,
        "started_at": occurred_at.isoformat(),
        "ended_at": (occurred_at + timedelta(seconds=30)).isoformat(),
        "artifact_refs": artifact_refs,
        "side_effect_summary": {
            "action_type": action_spec["action_type"],
            "artifacts_emitted": artifact_refs,
        },
        "environment_digest": {
            "executor": executor_id,
            "mode": "replay",
        },
        "retry_index": 0,
    }
    validate_against_schema(payload, "execution-receipt.schema.json")
    return payload
