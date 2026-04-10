use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CoreError {
    DuplicateEventId(String),
    UnsupportedEventType(String),
    IllegalTaskTransition { from: String, to: String },
    VerificationRequired { from: String, to: String },
    DispatchDenied { task_id: String, node_id: String },
    ApprovalDenied { task_id: String, node_id: String },
    InvalidConfiguration(String),
    Serialization(String),
    NotYetImplemented(String),
}

impl Display for CoreError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::DuplicateEventId(event_id) => write!(formatter, "duplicate event id: {event_id}"),
            Self::UnsupportedEventType(event_type) => {
                write!(formatter, "unsupported event type: {event_type}")
            }
            Self::IllegalTaskTransition { from, to } => {
                write!(formatter, "illegal task transition: {from} -> {to}")
            }
            Self::VerificationRequired { from, to } => {
                write!(
                    formatter,
                    "verification required for transition: {from} -> {to}"
                )
            }
            Self::DispatchDenied { task_id, node_id } => {
                write!(
                    formatter,
                    "dispatch denied: no active grant for task={task_id} node={node_id}"
                )
            }
            Self::ApprovalDenied { task_id, node_id } => {
                write!(
                    formatter,
                    "grant denied: approval required for task={task_id} node={node_id}"
                )
            }
            Self::InvalidConfiguration(message) => {
                write!(formatter, "invalid configuration: {message}")
            }
            Self::Serialization(message) => write!(formatter, "serialization error: {message}"),
            Self::NotYetImplemented(message) => write!(formatter, "not implemented: {message}"),
        }
    }
}

impl Error for CoreError {}

pub type CoreResult<T> = Result<T, CoreError>;
