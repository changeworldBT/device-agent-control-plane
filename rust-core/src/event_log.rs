use std::collections::HashSet;

use crate::contracts::EventEnvelope;
use crate::error::{CoreError, CoreResult};

#[derive(Debug, Default, Clone)]
pub struct EventLog {
    events: Vec<EventEnvelope>,
    seen_event_ids: HashSet<String>,
}

impl EventLog {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn append(&mut self, event: EventEnvelope) -> CoreResult<bool> {
        if self.seen_event_ids.contains(&event.event_id) {
            return Err(CoreError::DuplicateEventId(event.event_id));
        }
        self.seen_event_ids.insert(event.event_id.clone());
        self.events.push(event);
        Ok(true)
    }

    pub fn extend(&mut self, events: Vec<EventEnvelope>) -> CoreResult<usize> {
        let mut inserted = 0usize;
        for event in events {
            if self.append(event)? {
                inserted += 1;
            }
        }
        Ok(inserted)
    }

    pub fn as_slice(&self) -> &[EventEnvelope] {
        &self.events
    }

    pub fn len(&self) -> usize {
        self.events.len()
    }

    pub fn is_empty(&self) -> bool {
        self.events.is_empty()
    }
}
