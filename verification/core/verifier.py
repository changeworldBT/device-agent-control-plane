from __future__ import annotations

from datetime import datetime

from replay.schema_support import validate_against_schema


def build_verification_result(
    *,
    task_id: str,
    node_id: str,
    receipt_refs: list[str],
    supporting_evidence: list[str],
    occurred_at: datetime,
    verifier_id: str,
    target_state: str,
    fact_promotions: list[str] | None = None,
    recommended_recovery_action: str | None = None,
) -> dict[str, object]:
    transition: dict[str, object] = {"to": target_state}
    if fact_promotions:
        transition["fact_promotions"] = fact_promotions
    payload: dict[str, object] = {
        "verification_id": f"verification_{task_id}_{node_id}_{occurred_at.strftime('%H%M%S')}",
        "task_id": task_id,
        "node_id": node_id,
        "receipt_refs": receipt_refs,
        "result": "verified_success",
        "supporting_evidence": supporting_evidence,
        "remaining_uncertainties": [],
        "state_transition": transition,
        "verified_at": occurred_at.isoformat(),
        "verifier_id": verifier_id,
    }
    if recommended_recovery_action:
        payload["recommended_recovery_action"] = recommended_recovery_action
    validate_against_schema(payload, "verification-result.schema.json")
    return payload
