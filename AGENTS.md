# Project Agent Instructions

## Context Preservation

- At the end of every substantial execution turn, update `PROJECT_CONTEXT.md` before the final response.
- Keep the context concise and actionable: current goal, implemented changes, verification commands, worktree status, pending decisions, and known risks.
- Do not write secrets, tokens, private webhook URLs, or local credential values into the context file. Redact sensitive paths or values when needed.
- If the task is only a short answer with no project state change, mention that no context file update was needed.

## Reasoning Standard

- Continue using first-principles reasoning: start from the real goal, constraints, observable facts, invariants, costs, and risks.
- Prefer behavior that is easy to verify with tests, schema checks, or explicit CLI output.
