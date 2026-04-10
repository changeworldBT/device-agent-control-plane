from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from execution.local.dispatcher import build_receipt


@dataclass
class LocalActionResult:
    artifact_refs: list[str]
    fact_candidates: list[dict[str, Any]]
    verification_evidence: list[str]
    recovery: dict[str, Any] | None = None
    side_effect_summary: dict[str, Any] | None = None


@dataclass
class LocalRecoveryResult:
    artifact_refs: list[str]
    side_effect_summary: dict[str, Any]


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def reset_workspace(*, seed_dir: Path, runtime_dir: Path) -> None:
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    shutil.copytree(seed_dir, runtime_dir)


def execute_node(
    *,
    workspace_dir: Path,
    node: dict[str, Any],
    action_spec: dict[str, Any],
    grant: dict[str, Any],
    occurred_at: datetime,
) -> tuple[dict[str, Any], LocalActionResult]:
    crm_path = workspace_dir / "crm_record.json"
    outbox_path = workspace_dir / "outbox.json"
    artifacts_dir = workspace_dir / "artifacts"
    node_id = node["node_id"]
    node_type = node["node_type"]

    if node_type == "observe_sensitive_record":
        crm_record = _read_json(crm_path)
        baseline_path = artifacts_dir / f"{node_id}_baseline.json"
        _write_json(baseline_path, crm_record)
        fact = {
            "fact_id": f"fact_{node_id}_baseline",
            "fact_type": "observed",
            "statement": f"CRM baseline snapshot captured for {crm_record['account_id']}",
            "provenance": {
                "kind": "workspace-observation",
                "path": str(crm_path),
            },
            "observed_at": occurred_at.isoformat(),
            "valid_until": occurred_at.replace(hour=min(occurred_at.hour + 2, 23)).isoformat(),
            "attestation_level": "local_file_observation",
            "confidence": 0.95,
            "scope": {"path": str(crm_path)},
            "evidence_refs": [f"artifact::{baseline_path.name}"],
            "status": "candidate",
            "version": 1,
            "conflict_set": []
        }
        result = LocalActionResult(
            artifact_refs=[f"artifact::{baseline_path.name}"],
            fact_candidates=[fact],
            verification_evidence=[f"artifact::{baseline_path.name}"],
            side_effect_summary={"mode": "read", "path": str(crm_path)},
        )
    elif node_type == "prepare_crm_patch":
        crm_record = _read_json(crm_path)
        patch_path = artifacts_dir / f"{node_id}_patch.json"
        draft_path = artifacts_dir / f"{node_id}_email_draft.json"
        patch = {
            "account_id": crm_record["account_id"],
            "from_status": crm_record["renewal_status"],
            "to_status": "ready_to_contact",
        }
        draft = {
            "to": crm_record["contact_email"],
            "subject": f"Renewal follow-up for {crm_record['account_name']}",
            "body": "Following up on your renewal review. We have your updated pricing context and can schedule a quick call.",
        }
        _write_json(patch_path, patch)
        _write_json(draft_path, draft)
        result = LocalActionResult(
            artifact_refs=[f"artifact::{patch_path.name}", f"artifact::{draft_path.name}"],
            fact_candidates=[],
            verification_evidence=[f"artifact::{patch_path.name}", f"artifact::{draft_path.name}"],
            side_effect_summary={"mode": "prepare", "artifacts": [patch_path.name, draft_path.name]},
        )
    elif node_type == "operate_crm_update":
        crm_record = _read_json(crm_path)
        backup_path = artifacts_dir / f"{node_id}_backup.json"
        rollback_path = artifacts_dir / f"{node_id}_rollback_plan.json"
        _write_json(backup_path, crm_record)
        crm_record["renewal_status"] = "ready_to_contact"
        crm_record["history"].append({"at": occurred_at.isoformat(), "event": "status updated to ready_to_contact"})
        _write_json(crm_path, crm_record)
        _write_json(
            rollback_path,
            {
                "action": "rollback",
                "restore_from": backup_path.name,
                "target": crm_path.name,
            },
        )
        result = LocalActionResult(
            artifact_refs=[f"artifact::{backup_path.name}", f"artifact::{rollback_path.name}"],
            fact_candidates=[],
            verification_evidence=[f"artifact::{rollback_path.name}"],
            recovery={
                "recovery_kind": "rollback",
                "policy_ref": rollback_path.name,
            },
            side_effect_summary={"mode": "write", "path": str(crm_path), "new_status": "ready_to_contact"},
        )
    elif node_type == "commit_external_send":
        crm_record = _read_json(crm_path)
        outbox = _read_json(outbox_path)
        send_artifact = artifacts_dir / f"{node_id}_sent_email.json"
        compensation_path = artifacts_dir / f"{node_id}_compensation_plan.json"
        message = {
            "message_id": f"msg_{crm_record['account_id']}",
            "to": crm_record["contact_email"],
            "subject": f"Renewal follow-up for {crm_record['account_name']}",
            "body": "Following up on your renewal review. Let us know a convenient time this week.",
            "sent_at": occurred_at.isoformat(),
        }
        outbox.append(message)
        _write_json(outbox_path, outbox)
        crm_record["renewal_status"] = "follow_up_sent"
        crm_record["last_follow_up_at"] = occurred_at.isoformat()
        crm_record["history"].append({"at": occurred_at.isoformat(), "event": "follow-up email sent"})
        _write_json(crm_path, crm_record)
        _write_json(send_artifact, message)
        _write_json(
            compensation_path,
            {
                "action": "compensate",
                "kind": "send_correction_message",
                "reason": "email send is irreversible; correction message is the bounded compensation path",
                "target_message_id": message["message_id"],
            },
        )
        result = LocalActionResult(
            artifact_refs=[f"artifact::{send_artifact.name}", f"artifact::{compensation_path.name}"],
            fact_candidates=[],
            verification_evidence=[f"artifact::{send_artifact.name}"],
            recovery={
                "recovery_kind": "compensate",
                "policy_ref": compensation_path.name,
            },
            side_effect_summary={"mode": "commit", "outbox_entries": len(outbox)},
        )
    else:
        raise ValueError(f"unsupported local node type: {node_type}")

    receipt = build_receipt(
        action_spec=action_spec,
        grant=grant,
        artifact_refs=result.artifact_refs,
        occurred_at=occurred_at,
        executor_id="executor.local.workspace",
    )
    receipt["environment_digest"] = {
        "executor": "executor.local.workspace",
        "mode": "workspace",
        "workspace_dir": str(workspace_dir),
    }
    if result.side_effect_summary is not None:
        receipt["side_effect_summary"] = result.side_effect_summary
    return receipt, result


def execute_recovery(*, workspace_dir: Path, recovery: dict[str, Any], occurred_at: datetime) -> LocalRecoveryResult:
    crm_path = workspace_dir / "crm_record.json"
    outbox_path = workspace_dir / "outbox.json"
    artifacts_dir = workspace_dir / "artifacts"
    policy_path = artifacts_dir / str(recovery["policy_ref"])
    policy = _read_json(policy_path)

    if recovery["action"] == "compensate":
        crm_record = _read_json(crm_path)
        outbox = _read_json(outbox_path)
        correction = {
            "message_id": f"correction_{policy['target_message_id']}",
            "to": crm_record["contact_email"],
            "subject": f"Correction for {crm_record['account_name']} renewal follow-up",
            "body": "Correction: please disregard the previous follow-up if timing is no longer convenient. We can resend on request.",
            "sent_at": occurred_at.isoformat(),
            "kind": "correction_message",
            "target_message_id": policy["target_message_id"],
        }
        outbox.append(correction)
        _write_json(outbox_path, outbox)
        crm_record["history"].append({"at": occurred_at.isoformat(), "event": "compensation correction sent"})
        crm_record["last_compensation_at"] = occurred_at.isoformat()
        _write_json(crm_path, crm_record)
        artifact_path = artifacts_dir / f"{recovery['node_id']}_compensation_executed.json"
        _write_json(artifact_path, correction)
        return LocalRecoveryResult(
            artifact_refs=[f"artifact::{artifact_path.name}"],
            side_effect_summary={
                "mode": "compensate",
                "target_message_id": policy["target_message_id"],
                "outbox_entries": len(outbox),
            },
        )

    if recovery["action"] == "rollback":
        restore_payload = _read_json(policy_path)
        restore_from = artifacts_dir / str(restore_payload["restore_from"])
        baseline = _read_json(restore_from)
        _write_json(crm_path, baseline)
        artifact_path = artifacts_dir / f"{recovery['node_id']}_rollback_executed.json"
        _write_json(
            artifact_path,
            {
                "restored_from": restore_payload["restore_from"],
                "restored_at": occurred_at.isoformat(),
            },
        )
        return LocalRecoveryResult(
            artifact_refs=[f"artifact::{artifact_path.name}"],
            side_effect_summary={
                "mode": "rollback",
                "restored_from": restore_payload["restore_from"],
            },
        )

    raise ValueError(f"unsupported recovery action: {recovery['action']}")
