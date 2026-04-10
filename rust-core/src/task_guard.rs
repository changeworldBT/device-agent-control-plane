use crate::contracts::NodeState;
use crate::error::{CoreError, CoreResult};

pub fn is_terminal(state: &NodeState) -> bool {
    matches!(
        state,
        NodeState::Completed
            | NodeState::Failed
            | NodeState::RolledBack
            | NodeState::PausedForHuman
            | NodeState::Cancelled
    )
}

pub fn ensure_transition_allowed(
    current_state: &NodeState,
    target_state: &NodeState,
    has_verification: bool,
) -> CoreResult<()> {
    if current_state == target_state {
        return Ok(());
    }

    let allowed = match current_state {
        NodeState::Created => matches!(
            target_state,
            NodeState::Ready | NodeState::Blocked | NodeState::Cancelled
        ),
        NodeState::Ready => matches!(
            target_state,
            NodeState::Blocked
                | NodeState::AwaitingApproval
                | NodeState::Running
                | NodeState::Verifying
                | NodeState::Completed
                | NodeState::PausedForHuman
                | NodeState::Cancelled
        ),
        NodeState::Blocked => matches!(
            target_state,
            NodeState::Ready | NodeState::Cancelled | NodeState::PausedForHuman
        ),
        NodeState::AwaitingApproval => matches!(
            target_state,
            NodeState::Ready | NodeState::Cancelled | NodeState::PausedForHuman
        ),
        NodeState::Running => matches!(
            target_state,
            NodeState::Verifying
                | NodeState::Failed
                | NodeState::PausedForHuman
                | NodeState::Cancelled
        ),
        NodeState::Verifying => matches!(
            target_state,
            NodeState::Completed
                | NodeState::Failed
                | NodeState::RolledBack
                | NodeState::PausedForHuman
                | NodeState::Cancelled
        ),
        NodeState::Completed | NodeState::Failed | NodeState::RolledBack | NodeState::Cancelled => {
            false
        }
        NodeState::PausedForHuman => {
            matches!(target_state, NodeState::Ready | NodeState::Cancelled)
        }
    };

    if !allowed {
        return Err(CoreError::IllegalTaskTransition {
            from: format!("{current_state:?}"),
            to: format!("{target_state:?}"),
        });
    }

    let verification_terminal = matches!(
        target_state,
        NodeState::Completed | NodeState::Failed | NodeState::RolledBack
    );
    if verification_terminal && !has_verification {
        return Err(CoreError::VerificationRequired {
            from: format!("{current_state:?}"),
            to: format!("{target_state:?}"),
        });
    }

    Ok(())
}
