from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib import request

from execution.local.dispatcher import build_receipt


@dataclass
class HttpActionResult:
    artifact_refs: list[str]
    fact_candidates: list[dict[str, Any]]
    verification_evidence: list[str]
    recovery: dict[str, Any] | None = None
    side_effect_summary: dict[str, Any] | None = None


@dataclass
class HttpRecoveryResult:
    artifact_refs: list[str]
    side_effect_summary: dict[str, Any]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _artifact_ref(path: Path) -> str:
    return f"artifact::{path.name}"


class MockCrmHttpAdapter:
    def __init__(self, *, base_url: str, artifact_dir: Path) -> None:
        self.base_url = base_url.rstrip("/")
        self.artifact_dir = artifact_dir

    def execute_node(
        self,
        *,
        node: dict[str, Any],
        action_spec: dict[str, Any],
        grant: dict[str, Any],
        occurred_at: datetime,
    ) -> tuple[dict[str, Any], HttpActionResult]:
        node_id = node["node_id"]
        node_type = node["node_type"]

        if node_type == "observe_sensitive_record":
            crm_record = self._request_json("GET", "/crm/record", grant=grant)["crm_record"]
            baseline_path = self.artifact_dir / f"{node_id}_baseline.json"
            _write_json(baseline_path, crm_record)
            fact = {
                "fact_id": f"fact_{node_id}_baseline",
                "fact_type": "observed",
                "statement": f"HTTP CRM baseline snapshot captured for {crm_record['account_id']}",
                "provenance": {
                    "kind": "http-observation",
                    "url": f"{self.base_url}/crm/record",
                },
                "observed_at": occurred_at.isoformat(),
                "valid_until": (occurred_at + timedelta(hours=2)).isoformat(),
                "attestation_level": "http_read_observation",
                "confidence": 0.95,
                "scope": {"url": f"{self.base_url}/crm/record"},
                "evidence_refs": [_artifact_ref(baseline_path)],
                "status": "candidate",
                "version": 1,
                "conflict_set": [],
            }
            result = HttpActionResult(
                artifact_refs=[_artifact_ref(baseline_path)],
                fact_candidates=[fact],
                verification_evidence=[_artifact_ref(baseline_path)],
                side_effect_summary={"mode": "http_read", "url": f"{self.base_url}/crm/record"},
            )
        elif node_type == "prepare_crm_patch":
            crm_record = self._request_json("GET", "/crm/record", grant=grant)["crm_record"]
            patch_path = self.artifact_dir / f"{node_id}_patch.json"
            draft_path = self.artifact_dir / f"{node_id}_email_draft.json"
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
            result = HttpActionResult(
                artifact_refs=[_artifact_ref(patch_path), _artifact_ref(draft_path)],
                fact_candidates=[],
                verification_evidence=[_artifact_ref(patch_path), _artifact_ref(draft_path)],
                side_effect_summary={"mode": "prepare", "artifacts": [patch_path.name, draft_path.name]},
            )
        elif node_type == "operate_crm_update":
            crm_record = self._request_json("GET", "/crm/record", grant=grant)["crm_record"]
            backup_path = self.artifact_dir / f"{node_id}_backup.json"
            rollback_path = self.artifact_dir / f"{node_id}_rollback_plan.json"
            _write_json(backup_path, crm_record)
            self._request_json(
                "PATCH",
                "/crm/status",
                grant=grant,
                payload={
                    "renewal_status": "ready_to_contact",
                    "at": occurred_at.isoformat(),
                    "event": "status updated to ready_to_contact",
                },
            )
            _write_json(
                rollback_path,
                {
                    "action": "rollback",
                    "restore_status": crm_record["renewal_status"],
                    "target": "/crm/status",
                },
            )
            result = HttpActionResult(
                artifact_refs=[_artifact_ref(backup_path), _artifact_ref(rollback_path)],
                fact_candidates=[],
                verification_evidence=[_artifact_ref(rollback_path)],
                recovery={
                    "recovery_kind": "rollback",
                    "policy_ref": rollback_path.name,
                },
                side_effect_summary={"mode": "http_write", "url": f"{self.base_url}/crm/status", "new_status": "ready_to_contact"},
            )
        elif node_type == "commit_external_send":
            crm_record = self._request_json("GET", "/crm/record", grant=grant)["crm_record"]
            send_artifact = self.artifact_dir / f"{node_id}_sent_email.json"
            compensation_path = self.artifact_dir / f"{node_id}_compensation_plan.json"
            message = {
                "message_id": f"msg_{crm_record['account_id']}",
                "to": crm_record["contact_email"],
                "subject": f"Renewal follow-up for {crm_record['account_name']}",
                "body": "Following up on your renewal review. Let us know a convenient time this week.",
                "sent_at": occurred_at.isoformat(),
            }
            send_result = self._request_json("POST", "/messages/send", grant=grant, payload=message)
            _write_json(send_artifact, send_result["message"])
            _write_json(
                compensation_path,
                {
                    "action": "compensate",
                    "kind": "send_correction_message",
                    "reason": "message send is irreversible; correction message is the bounded compensation path",
                    "target_message_id": send_result["message"]["message_id"],
                },
            )
            result = HttpActionResult(
                artifact_refs=[_artifact_ref(send_artifact), _artifact_ref(compensation_path)],
                fact_candidates=[],
                verification_evidence=[_artifact_ref(send_artifact)],
                recovery={
                    "recovery_kind": "compensate",
                    "policy_ref": compensation_path.name,
                },
                side_effect_summary={"mode": "http_commit", "url": f"{self.base_url}/messages/send", "outbox_entries": send_result["outbox_entries"]},
            )
        else:
            raise ValueError(f"unsupported http node type: {node_type}")

        receipt = build_receipt(
            action_spec=action_spec,
            grant=grant,
            artifact_refs=result.artifact_refs,
            occurred_at=occurred_at,
            executor_id="executor.http.mock_crm",
        )
        receipt["environment_digest"] = {
            "executor": "executor.http.mock_crm",
            "mode": "http",
            "base_url": self.base_url,
        }
        if result.side_effect_summary is not None:
            receipt["side_effect_summary"] = result.side_effect_summary
        return receipt, result

    def execute_recovery(self, *, recovery: dict[str, Any], occurred_at: datetime, grant: dict[str, Any]) -> HttpRecoveryResult:
        policy_path = self.artifact_dir / str(recovery["policy_ref"])
        with policy_path.open("r", encoding="utf-8") as handle:
            policy = json.load(handle)

        if recovery["action"] == "compensate":
            crm_record = self._request_json("GET", "/crm/record", grant=grant)["crm_record"]
            correction = {
                "message_id": f"correction_{policy['target_message_id']}",
                "to": crm_record["contact_email"],
                "subject": f"Correction for {crm_record['account_name']} renewal follow-up",
                "body": "Correction: please disregard the previous follow-up if timing is no longer convenient. We can resend on request.",
                "sent_at": occurred_at.isoformat(),
                "kind": "correction_message",
                "target_message_id": policy["target_message_id"],
            }
            response = self._request_json("POST", "/messages/correction", grant=grant, payload=correction)
            artifact_path = self.artifact_dir / f"{recovery['node_id']}_compensation_executed.json"
            _write_json(artifact_path, response["message"])
            return HttpRecoveryResult(
                artifact_refs=[_artifact_ref(artifact_path)],
                side_effect_summary={
                    "mode": "compensate",
                    "target_message_id": policy["target_message_id"],
                    "outbox_entries": response["outbox_entries"],
                },
            )

        if recovery["action"] == "rollback":
            response = self._request_json(
                "POST",
                "/crm/restore-status",
                grant=grant,
                payload={
                    "renewal_status": policy["restore_status"],
                    "restored_at": occurred_at.isoformat(),
                },
            )
            artifact_path = self.artifact_dir / f"{recovery['node_id']}_rollback_executed.json"
            _write_json(
                artifact_path,
                {
                    "restored_status": response["crm_record"]["renewal_status"],
                    "restored_at": occurred_at.isoformat(),
                },
            )
            return HttpRecoveryResult(
                artifact_refs=[_artifact_ref(artifact_path)],
                side_effect_summary={
                    "mode": "rollback",
                    "restored_status": response["crm_record"]["renewal_status"],
                },
            )

        raise ValueError(f"unsupported recovery action: {recovery['action']}")

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        grant: dict[str, Any],
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "X-Grant-Id": grant["grant_id"],
            "X-Principal-Ref": grant["principal_ref"],
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = request.Request(f"{self.base_url}{path}", method=method, data=body, headers=headers)
        with request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
