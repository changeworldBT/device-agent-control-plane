use std::collections::BTreeMap;

use crate::contracts::{ApprovalRecord, RiskBand, Task, TaskNode};
use crate::error::{CoreError, CoreResult};

pub fn approval_required(node: &TaskNode, task: &Task, composite_risk_score: Option<f64>) -> bool {
    if matches!(node.risk_class, RiskBand::R3 | RiskBand::R2) {
        return true;
    }
    if node.node_type.starts_with("commit_") {
        return true;
    }
    if task.attention_budget.must_confirm_before_commit && matches!(node.risk_class, RiskBand::R2 | RiskBand::R3) {
        return true;
    }
    composite_risk_score.map(|score| score >= 4.0).unwrap_or(false)
}

pub fn has_active_approval(
    approvals: &BTreeMap<String, ApprovalRecord>,
    task_id: &str,
    node_id: &str,
) -> bool {
    approvals
        .values()
        .any(|approval| approval.task_id == task_id && approval.node_id == node_id && approval.status == "approved")
}

pub fn ensure_approval_for_grant(
    approvals: &BTreeMap<String, ApprovalRecord>,
    node: &TaskNode,
    task: &Task,
    composite_risk_score: Option<f64>,
) -> CoreResult<()> {
    if !approval_required(node, task, composite_risk_score) {
        return Ok(());
    }
    if has_active_approval(approvals, &task.task_id, &node.node_id) {
        return Ok(());
    }
    Err(CoreError::ApprovalDenied {
        task_id: task.task_id.clone(),
        node_id: node.node_id.clone(),
    })
}
