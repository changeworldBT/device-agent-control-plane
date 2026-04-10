use std::fs;
use std::path::{Path, PathBuf};

use serde_json::{json, Value};

use crate::contracts::{CapabilityGrant, ExecutionReceipt, RecoveryRecord, TaskNode, Timestamp};
use crate::error::{CoreError, CoreResult};

#[derive(Debug, Clone)]
pub struct WorkspaceExecutionOutcome {
    pub receipt: ExecutionReceipt,
    pub fact_candidates: Vec<Value>,
    pub verification_evidence: Vec<String>,
    pub recovery: Option<Value>,
    pub side_effect_summary: Value,
}

#[derive(Debug, Clone)]
pub struct WorkspaceRecoveryOutcome {
    pub artifact_refs: Vec<String>,
    pub side_effect_summary: Value,
}

pub trait WorkspaceAdapter {
    fn execute_node(
        &self,
        node: &TaskNode,
        action_spec: &Value,
        grant: &CapabilityGrant,
        occurred_at: Timestamp,
    ) -> CoreResult<WorkspaceExecutionOutcome>;

    fn execute_recovery(
        &self,
        recovery: &RecoveryRecord,
        occurred_at: Timestamp,
    ) -> CoreResult<WorkspaceRecoveryOutcome>;
}

#[derive(Debug, Clone)]
pub struct LocalWorkspaceAdapter {
    workspace_dir: PathBuf,
}

impl LocalWorkspaceAdapter {
    pub fn new(workspace_dir: impl AsRef<Path>) -> Self {
        Self {
            workspace_dir: workspace_dir.as_ref().to_path_buf(),
        }
    }

    pub fn workspace_dir(&self) -> &Path {
        &self.workspace_dir
    }

    pub fn reset_workspace(&self, seed_dir: impl AsRef<Path>) -> CoreResult<()> {
        let runtime_dir = &self.workspace_dir;
        if runtime_dir.exists() {
            fs::remove_dir_all(runtime_dir).map_err(io_error)?;
        }
        copy_dir_all(seed_dir.as_ref(), runtime_dir)
    }

    fn crm_path(&self) -> PathBuf {
        self.workspace_dir.join("crm_record.json")
    }

    fn outbox_path(&self) -> PathBuf {
        self.workspace_dir.join("outbox.json")
    }

    fn artifacts_dir(&self) -> PathBuf {
        self.workspace_dir.join("artifacts")
    }
}

impl WorkspaceAdapter for LocalWorkspaceAdapter {
    fn execute_node(
        &self,
        node: &TaskNode,
        action_spec: &Value,
        grant: &CapabilityGrant,
        occurred_at: Timestamp,
    ) -> CoreResult<WorkspaceExecutionOutcome> {
        let crm_path = self.crm_path();
        let outbox_path = self.outbox_path();
        let artifacts_dir = self.artifacts_dir();
        fs::create_dir_all(&artifacts_dir).map_err(io_error)?;

        let node_id = &node.node_id;
        let node_type = node.node_type.as_str();

        let (artifact_refs, fact_candidates, verification_evidence, recovery, side_effect_summary) =
            match node_type {
                "observe_sensitive_record" => {
                    let crm_record = read_json(&crm_path)?;
                    let baseline_path = artifacts_dir.join(format!("{node_id}_baseline.json"));
                    write_json(&baseline_path, &crm_record)?;
                    let fact = json!({
                        "fact_id": format!("fact_{node_id}_baseline"),
                        "fact_type": "observed",
                        "statement": format!("CRM baseline snapshot captured for {}", crm_record["account_id"].as_str().unwrap_or("unknown")),
                        "provenance": {
                            "kind": "workspace-observation",
                            "path": crm_path.to_string_lossy().to_string(),
                        },
                        "observed_at": occurred_at.to_rfc3339(),
                        "valid_until": (occurred_at + chrono::Duration::hours(2)).to_rfc3339(),
                        "attestation_level": "local_file_observation",
                        "confidence": 0.95,
                        "scope": {"path": crm_path.to_string_lossy().to_string()},
                        "evidence_refs": [artifact_ref(&baseline_path)],
                        "status": "candidate",
                        "version": 1,
                        "conflict_set": []
                    });
                    (
                        vec![artifact_ref(&baseline_path)],
                        vec![fact],
                        vec![artifact_ref(&baseline_path)],
                        None,
                        json!({"mode": "read", "path": crm_path.to_string_lossy().to_string()}),
                    )
                }
                "prepare_crm_patch" => {
                    let crm_record = read_json(&crm_path)?;
                    let patch_path = artifacts_dir.join(format!("{node_id}_patch.json"));
                    let draft_path = artifacts_dir.join(format!("{node_id}_email_draft.json"));
                    let patch = json!({
                        "account_id": crm_record["account_id"],
                        "from_status": crm_record["renewal_status"],
                        "to_status": "ready_to_contact",
                    });
                    let draft = json!({
                        "to": crm_record["contact_email"],
                        "subject": format!("Renewal follow-up for {}", crm_record["account_name"].as_str().unwrap_or("unknown")),
                        "body": "Following up on your renewal review. We have your updated pricing context and can schedule a quick call.",
                    });
                    write_json(&patch_path, &patch)?;
                    write_json(&draft_path, &draft)?;
                    (
                        vec![artifact_ref(&patch_path), artifact_ref(&draft_path)],
                        Vec::new(),
                        vec![artifact_ref(&patch_path), artifact_ref(&draft_path)],
                        None,
                        json!({"mode": "prepare", "artifacts": [patch_path.file_name().unwrap().to_string_lossy(), draft_path.file_name().unwrap().to_string_lossy()]}),
                    )
                }
                "operate_crm_update" => {
                    let mut crm_record = read_json(&crm_path)?;
                    let backup_path = artifacts_dir.join(format!("{node_id}_backup.json"));
                    let rollback_path = artifacts_dir.join(format!("{node_id}_rollback_plan.json"));
                    write_json(&backup_path, &crm_record)?;
                    crm_record["renewal_status"] = json!("ready_to_contact");
                    crm_record["history"]
                    .as_array_mut()
                    .expect("crm history should be an array")
                    .push(json!({"at": occurred_at.to_rfc3339(), "event": "status updated to ready_to_contact"}));
                    write_json(&crm_path, &crm_record)?;
                    write_json(
                        &rollback_path,
                        &json!({
                            "action": "rollback",
                            "restore_from": backup_path.file_name().unwrap().to_string_lossy().to_string(),
                            "target": crm_path.file_name().unwrap().to_string_lossy().to_string(),
                        }),
                    )?;
                    (
                        vec![artifact_ref(&backup_path), artifact_ref(&rollback_path)],
                        Vec::new(),
                        vec![artifact_ref(&rollback_path)],
                        Some(json!({
                            "recovery_kind": "rollback",
                            "policy_ref": rollback_path.file_name().unwrap().to_string_lossy().to_string(),
                        })),
                        json!({"mode": "write", "path": crm_path.to_string_lossy().to_string(), "new_status": "ready_to_contact"}),
                    )
                }
                "commit_external_send" => {
                    let mut crm_record = read_json(&crm_path)?;
                    let mut outbox = read_json(&outbox_path)?;
                    let send_artifact = artifacts_dir.join(format!("{node_id}_sent_email.json"));
                    let compensation_path =
                        artifacts_dir.join(format!("{node_id}_compensation_plan.json"));
                    let message = json!({
                        "message_id": format!("msg_{}", crm_record["account_id"].as_str().unwrap_or("unknown")),
                        "to": crm_record["contact_email"],
                        "subject": format!("Renewal follow-up for {}", crm_record["account_name"].as_str().unwrap_or("unknown")),
                        "body": "Following up on your renewal review. Let us know a convenient time this week.",
                        "sent_at": occurred_at.to_rfc3339(),
                    });
                    outbox
                        .as_array_mut()
                        .expect("outbox should be an array")
                        .push(message.clone());
                    write_json(&outbox_path, &outbox)?;
                    crm_record["renewal_status"] = json!("follow_up_sent");
                    crm_record["last_follow_up_at"] = json!(occurred_at.to_rfc3339());
                    crm_record["history"]
                    .as_array_mut()
                    .expect("crm history should be an array")
                    .push(json!({"at": occurred_at.to_rfc3339(), "event": "follow-up email sent"}));
                    write_json(&crm_path, &crm_record)?;
                    write_json(&send_artifact, &message)?;
                    write_json(
                        &compensation_path,
                        &json!({
                            "action": "compensate",
                            "kind": "send_correction_message",
                            "reason": "email send is irreversible; correction message is the bounded compensation path",
                            "target_message_id": message["message_id"],
                        }),
                    )?;
                    let outbox_entries = outbox.as_array().map(|items| items.len()).unwrap_or(0);
                    (
                        vec![
                            artifact_ref(&send_artifact),
                            artifact_ref(&compensation_path),
                        ],
                        Vec::new(),
                        vec![artifact_ref(&send_artifact)],
                        Some(json!({
                            "recovery_kind": "compensate",
                            "policy_ref": compensation_path.file_name().unwrap().to_string_lossy().to_string(),
                        })),
                        json!({"mode": "commit", "outbox_entries": outbox_entries}),
                    )
                }
                other => {
                    return Err(CoreError::NotYetImplemented(format!(
                        "unsupported local node type: {other}"
                    )))
                }
            };

        let action_id = action_spec
            .get("action_id")
            .and_then(|value| value.as_str())
            .unwrap_or("action_local_workspace");

        let receipt = ExecutionReceipt {
            receipt_id: format!("receipt_{node_id}_{}", occurred_at.format("%H%M%S")),
            action_id: action_id.to_owned(),
            task_id: node.task_id.clone(),
            node_id: node.node_id.clone(),
            grant_id: grant.grant_id.clone(),
            executor_id: "executor.local.workspace".to_owned(),
            status: "succeeded_with_receipt".to_owned(),
            started_at: occurred_at,
            ended_at: occurred_at + chrono::Duration::seconds(1),
            artifact_refs: artifact_refs.clone(),
            side_effect_summary: side_effect_summary.clone(),
            environment_digest: json!({
                "executor": "executor.local.workspace",
                "mode": "workspace",
                "workspace_dir": self.workspace_dir.to_string_lossy().to_string(),
            }),
            retry_index: 0,
            error_summary: json!({}),
        };

        Ok(WorkspaceExecutionOutcome {
            receipt,
            fact_candidates,
            verification_evidence,
            recovery,
            side_effect_summary,
        })
    }

    fn execute_recovery(
        &self,
        recovery: &RecoveryRecord,
        occurred_at: Timestamp,
    ) -> CoreResult<WorkspaceRecoveryOutcome> {
        let crm_path = self.crm_path();
        let outbox_path = self.outbox_path();
        let artifacts_dir = self.artifacts_dir();
        let policy_path = artifacts_dir.join(&recovery.policy_ref);
        let policy = read_json(&policy_path)?;

        match recovery.action.as_str() {
            "compensate" => {
                let mut crm_record = read_json(&crm_path)?;
                let mut outbox = read_json(&outbox_path)?;
                let correction = json!({
                    "message_id": format!("correction_{}", policy["target_message_id"].as_str().unwrap_or("unknown")),
                    "to": crm_record["contact_email"],
                    "subject": format!("Correction for {} renewal follow-up", crm_record["account_name"].as_str().unwrap_or("unknown")),
                    "body": "Correction: please disregard the previous follow-up if timing is no longer convenient. We can resend on request.",
                    "sent_at": occurred_at.to_rfc3339(),
                    "kind": "correction_message",
                    "target_message_id": policy["target_message_id"],
                });
                outbox
                    .as_array_mut()
                    .expect("outbox should be an array")
                    .push(correction.clone());
                write_json(&outbox_path, &outbox)?;
                crm_record["history"]
                    .as_array_mut()
                    .expect("crm history should be an array")
                    .push(json!({"at": occurred_at.to_rfc3339(), "event": "compensation correction sent"}));
                crm_record["last_compensation_at"] = json!(occurred_at.to_rfc3339());
                write_json(&crm_path, &crm_record)?;
                let artifact_path =
                    artifacts_dir.join(format!("{}_compensation_executed.json", recovery.node_id));
                write_json(&artifact_path, &correction)?;
                Ok(WorkspaceRecoveryOutcome {
                    artifact_refs: vec![artifact_ref(&artifact_path)],
                    side_effect_summary: json!({
                        "mode": "compensate",
                        "target_message_id": policy["target_message_id"],
                        "outbox_entries": outbox.as_array().map(|items| items.len()).unwrap_or(0),
                    }),
                })
            }
            "rollback" => {
                let restore_from = policy["restore_from"].as_str().ok_or_else(|| {
                    CoreError::Serialization("rollback policy missing restore_from".to_owned())
                })?;
                let restore_path = artifacts_dir.join(restore_from);
                let baseline = read_json(&restore_path)?;
                write_json(&crm_path, &baseline)?;
                let artifact_path =
                    artifacts_dir.join(format!("{}_rollback_executed.json", recovery.node_id));
                write_json(
                    &artifact_path,
                    &json!({
                        "restored_from": restore_from,
                        "restored_at": occurred_at.to_rfc3339(),
                    }),
                )?;
                Ok(WorkspaceRecoveryOutcome {
                    artifact_refs: vec![artifact_ref(&artifact_path)],
                    side_effect_summary: json!({
                        "mode": "rollback",
                        "restored_from": restore_from,
                    }),
                })
            }
            other => Err(CoreError::NotYetImplemented(format!(
                "unsupported recovery action: {other}"
            ))),
        }
    }
}

fn artifact_ref(path: &Path) -> String {
    format!(
        "artifact::{}",
        path.file_name()
            .expect("artifact path should have file name")
            .to_string_lossy()
    )
}

fn read_json(path: &Path) -> CoreResult<Value> {
    let raw = fs::read_to_string(path).map_err(io_error)?;
    serde_json::from_str(&raw).map_err(|error| CoreError::Serialization(error.to_string()))
}

fn write_json(path: &Path, payload: &Value) -> CoreResult<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(io_error)?;
    }
    let serialized = serde_json::to_string_pretty(payload)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    fs::write(path, serialized).map_err(io_error)
}

fn copy_dir_all(src: &Path, dst: &Path) -> CoreResult<()> {
    fs::create_dir_all(dst).map_err(io_error)?;
    for entry in fs::read_dir(src).map_err(io_error)? {
        let entry = entry.map_err(io_error)?;
        let source_path = entry.path();
        let destination_path = dst.join(entry.file_name());
        if source_path.is_dir() {
            copy_dir_all(&source_path, &destination_path)?;
        } else {
            fs::copy(&source_path, &destination_path).map_err(io_error)?;
        }
    }
    Ok(())
}

fn io_error(error: std::io::Error) -> CoreError {
    CoreError::Serialization(error.to_string())
}
