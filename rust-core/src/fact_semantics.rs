use chrono::Duration;

use crate::contracts::{FactRecord, FactStatus, Timestamp};

pub fn effective_valid_until(fact: &FactRecord) -> Option<Timestamp> {
    if let Some(valid_until) = fact.valid_until {
        return Some(valid_until);
    }
    fact.ttl
        .map(|seconds| fact.observed_at + Duration::seconds(seconds))
}

pub fn is_fact_expired(fact: &FactRecord, as_of: Timestamp) -> bool {
    effective_valid_until(fact)
        .map(|valid_until| as_of >= valid_until)
        .unwrap_or(false)
}

pub fn materialize_fact_status(fact: &FactRecord, as_of: Timestamp) -> FactStatus {
    if fact.status == FactStatus::Revoked {
        return FactStatus::Revoked;
    }
    if is_fact_expired(fact, as_of) {
        return FactStatus::Stale;
    }
    fact.status.clone()
}
