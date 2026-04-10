from __future__ import annotations


TERMINAL_STATES = {"completed", "failed", "rolled_back", "paused_for_human", "cancelled"}
STRICT_VERIFICATION_TERMINALS = {"completed", "failed", "rolled_back"}

ALLOWED_TRANSITIONS = {
    "created": {"ready", "blocked", "cancelled"},
    "ready": {"blocked", "awaiting_approval", "running", "verifying", "completed", "paused_for_human", "cancelled"},
    "blocked": {"ready", "cancelled", "paused_for_human"},
    "awaiting_approval": {"ready", "cancelled", "paused_for_human"},
    "running": {"verifying", "failed", "paused_for_human", "cancelled"},
    "verifying": {"completed", "failed", "rolled_back", "paused_for_human", "cancelled"},
    "completed": set(),
    "failed": set(),
    "rolled_back": set(),
    "paused_for_human": {"ready", "cancelled"},
    "cancelled": set(),
}


def is_terminal(state: str) -> bool:
    return state in TERMINAL_STATES


def ensure_transition_allowed(current_state: str, target_state: str, *, has_verification: bool) -> None:
    if current_state == target_state:
        return
    if target_state not in ALLOWED_TRANSITIONS.get(current_state, set()):
        raise ValueError(f"illegal task transition: {current_state} -> {target_state}")
    if target_state in STRICT_VERIFICATION_TERMINALS and not has_verification:
        raise ValueError(f"verification required for terminal transition: {current_state} -> {target_state}")
