from __future__ import annotations

from datetime import datetime
from typing import Any

from replay.schema_support import validate_against_schema


def build_minimal_capsule(
    *,
    state: Any,
    task_id: str,
    node_id: str,
    candidate_next_actions: list[dict[str, Any]],
    generated_at: datetime,
) -> dict[str, Any]:
    task = state.tasks[task_id]
    node = state.nodes[node_id]
    capsule = {
        "capsule_id": f"capsule_{task_id}_{node_id}",
        "capsule_type": "resume",
        "task_id": task_id,
        "node_id": node_id,
        "objective": task["objective"],
        "desired_delta": task["desired_delta"],
        "current_task_state": state.current_task_terminal(task_id),
        "verified_facts": [fact_id for fact_id, fact in state.facts.items() if fact["status"] == "verified"],
        "open_questions": [
            fact_id
            for fact_id, fact in state.facts.items()
            if fact["status"] in {"candidate", "stale"} or fact.get("conflict_set")
        ],
        "hard_constraints": [
            f"risk_class={node['risk_class']}",
            "truth_source=event_log",
            "terminal_requires_verification",
        ],
        "soft_constraints": [
            f"max_interruptions={task['attention_budget'].get('max_interruptions', 0)}",
        ],
        "active_grants_summary": [
            {
                "grant_id": grant["grant_id"],
                "node_id": grant["node_id"],
                "status": grant["status"],
            }
            for grant in state.grants.values()
            if grant["task_id"] == task_id and grant["node_id"] == node_id and grant["status"] in {"issued", "active"}
        ],
        "relevant_artifacts": node.get("artifact_refs", []),
        "recent_decisions": [f"node_state={node['state']}"],
        "pending_dependencies": [dep for dep in node.get("dependencies", []) if state.nodes[dep]["state"] != "completed"],
        "candidate_next_actions": candidate_next_actions,
        "failure_or_recovery_context": {},
        "freshness_markers": {
            fact_id: {
                "status": fact["status"],
                "valid_until": fact.get("valid_until"),
            }
            for fact_id, fact in state.facts.items()
        },
        "validator_ref": "state-capsule.schema.json",
        "generated_at": generated_at.isoformat(),
        "generator_ref": "runtime.projector.capsule",
    }
    validate_against_schema(capsule, "state-capsule.schema.json")
    return capsule
