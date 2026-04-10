use serde_json::json;

use crate::approval_guard::{approval_required, has_active_approval};
use crate::contracts::{FactStatus, NodeState, RiskBand, SelectionDecision, Task, TaskNode, Timestamp};
use crate::projector::MaterializedState;
use crate::task_guard::is_terminal;

fn surface_from_node_type(node_type: &str) -> &'static str {
    if node_type.starts_with("observe_") {
        "Observe"
    } else if node_type.starts_with("synthesize_") {
        "Synthesize"
    } else if node_type.starts_with("prepare_") {
        "Prepare"
    } else if node_type.starts_with("operate_") {
        "Operate"
    } else if node_type.starts_with("commit_") {
        "Commit"
    } else {
        "Prepare"
    }
}

fn risk_cost(risk_band: &RiskBand) -> f64 {
    match risk_band {
        RiskBand::R0 => 0.0,
        RiskBand::R1 => 1.0,
        RiskBand::R2 => 3.0,
        RiskBand::R3 => 6.0,
    }
}

fn attention_cost(risk_band: &RiskBand) -> u32 {
    match risk_band {
        RiskBand::R0 | RiskBand::R1 => 0,
        RiskBand::R2 => 1,
        RiskBand::R3 => 2,
    }
}

fn surface_cost(surface: &str) -> f64 {
    match surface {
        "Observe" => 0.0,
        "Synthesize" => 0.5,
        "Prepare" => 1.0,
        "Operate" => 2.0,
        "Commit" => 4.0,
        "Monitor" => 1.0,
        _ => 1.0,
    }
}

pub fn composite_risk_score(node: &TaskNode, task: &Task, state: &MaterializedState) -> (f64, serde_json::Value) {
    let action_surface_cost = surface_cost(surface_from_node_type(&node.node_type));
    let target_sensitivity_cost = if ["sensitive", "crm", "commit"]
        .iter()
        .any(|token| node.node_type.contains(token))
    {
        1.5
    } else {
        0.5
    };
    let context_cost = if task.attention_budget.must_confirm_before_commit { 1.0 } else { 0.0 };
    let sequence_cost = 0.5
        * state
            .nodes
            .values()
            .filter(|peer| peer.task_id == task.task_id && peer.state == NodeState::Completed)
            .count() as f64;
    let base_band_cost = risk_cost(&node.risk_class);
    let total = base_band_cost + action_surface_cost + target_sensitivity_cost + context_cost + sequence_cost;
    (
        total,
        json!({
            "base_band_cost": base_band_cost,
            "action_surface_cost": action_surface_cost,
            "target_sensitivity_cost": target_sensitivity_cost,
            "context_cost": context_cost,
            "sequence_cost": sequence_cost,
        }),
    )
}

fn dependencies_satisfied(node: &TaskNode, state: &MaterializedState) -> bool {
    node.dependencies.iter().all(|dependency_id| {
        state
            .nodes
            .get(dependency_id)
            .map(|dependency| dependency.state == NodeState::Completed)
            .unwrap_or(false)
    })
}

fn candidate_score(node: &TaskNode, state: &MaterializedState, max_interruptions: u32) -> Option<(f64, serde_json::Value)> {
    let interruption_cost = attention_cost(&node.risk_class);
    if interruption_cost > max_interruptions {
        return None;
    }

    let task = state.tasks.get(&node.task_id)?;
    let (composite_score, composite_parts) = composite_risk_score(node, task, state);
    let verified_facts = state
        .facts
        .values()
        .filter(|fact| fact.status == FactStatus::Verified)
        .count();
    let verification_bonus = (verified_facts as f64 * 0.1).min(0.5);
    let freshness_bonus = 1.0;
    let dependency_penalty = if dependencies_satisfied(node, state) { 0.0 } else { 10.0 };
    let ready_bonus = if node.state == NodeState::Ready { 0.5 } else { 0.0 };
    let approval_needed = approval_required(node, task, Some(composite_score));
    let approval_present = has_active_approval(&state.approvals, &task.task_id, &node.node_id);
    if approval_needed && !approval_present {
        return None;
    }

    let score = 5.0 + ready_bonus + freshness_bonus + verification_bonus - composite_score - dependency_penalty;
    Some((
        score,
        json!({
            "risk_cost": composite_score,
            "interruption_cost": interruption_cost,
            "freshness_bonus": freshness_bonus,
            "verification_bonus": verification_bonus,
            "dependency_penalty": dependency_penalty,
            "ready_bonus": ready_bonus,
            "approval_required": approval_needed,
            "approval_present": approval_present,
            "composite_risk": composite_parts,
        }),
    ))
}

pub fn select_next_node(state: &MaterializedState, task: &Task, _at_time: Timestamp) -> SelectionDecision {
    let max_interruptions = task.attention_budget.max_interruptions;
    let mut candidates: Vec<(String, f64, serde_json::Value)> = state
        .nodes
        .values()
        .filter(|node| node.task_id == task.task_id)
        .filter(|node| !is_terminal(&node.state))
        .filter(|node| matches!(node.state, NodeState::Created | NodeState::Ready))
        .filter(|node| dependencies_satisfied(node, state))
        .filter_map(|node| {
            candidate_score(node, state, max_interruptions).map(|(score, rationale)| (node.node_id.clone(), score, rationale))
        })
        .collect();

    if candidates.is_empty() {
        return SelectionDecision {
            node_id: None,
            path_kind: "ask".to_owned(),
            score: None,
            rationale: json!({
                "reason": "no eligible candidate within attention budget and dependency constraints",
                "max_interruptions": max_interruptions,
            }),
            max_interruptions,
        };
    }

    candidates.sort_by(|left, right| {
        right
            .1
            .partial_cmp(&left.1)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| left.0.cmp(&right.0))
    });

    let (node_id, score, rationale) = candidates.remove(0);
    SelectionDecision {
        node_id: Some(node_id),
        path_kind: "structured".to_owned(),
        score: Some(score),
        rationale,
        max_interruptions,
    }
}
