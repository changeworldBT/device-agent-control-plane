use std::collections::BTreeMap;

use crate::contracts::{CapabilityGrant, Timestamp};
use crate::error::{CoreError, CoreResult};

pub fn is_grant_active(grant: &CapabilityGrant, at_time: Timestamp) -> bool {
    matches!(grant.status.as_str(), "issued" | "active")
        && grant.issued_at <= at_time
        && at_time <= grant.expires_at
}

pub fn find_active_grant(
    grants: &BTreeMap<String, CapabilityGrant>,
    task_id: &str,
    node_id: &str,
    at_time: Timestamp,
) -> Option<CapabilityGrant> {
    grants
        .values()
        .filter(|grant| {
            grant.task_id == task_id && grant.node_id == node_id && is_grant_active(grant, at_time)
        })
        .cloned()
        .max_by(|left, right| left.issued_at.cmp(&right.issued_at))
}

pub fn ensure_dispatch_allowed(
    grants: &BTreeMap<String, CapabilityGrant>,
    task_id: &str,
    node_id: &str,
    at_time: Timestamp,
) -> CoreResult<CapabilityGrant> {
    find_active_grant(grants, task_id, node_id, at_time).ok_or_else(|| CoreError::DispatchDenied {
        task_id: task_id.to_owned(),
        node_id: node_id.to_owned(),
    })
}
