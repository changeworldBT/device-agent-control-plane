# Project Context

Last updated: 2026-04-15

## Standing Instruction

After every substantial execution turn, update this file before the final response. Preserve enough context for a future session to resume without relying on chat history. Do not record secrets, tokens, private webhook URLs, or credential values.

## Current Goal

Enable a real local model-call path so the user can test live provider invocation from the UI instead of dry-run-only chat.

## Current Branch State

- Repository: `C:\Users\84915\device-agent-doc`
- Branch: `main`
- Remote state before the current uncommitted work was `main...origin/main [ahead 2]`
- Current worktree is intentionally dirty with local-only config/runtime artifacts and ongoing UI/model work. Do not revert unrelated user changes.

## Implemented This Turn

- Added real OpenAI-compatible live chat support for the local UI:
  - new `POST /api/chat`
  - new `GET /api/chat/session?session_id=...`
- Added `model/live_client.py`:
  - sends OpenAI-compatible `POST {base_url}/chat/completions`
  - supports `off`, `mock`, and `live`
  - passes agent `system_contract` as a system message
  - extracts assistant text/finish reason/usage from the provider response
  - retries once with a transport-normalized model ID when the configured model has a vendor prefix and the provider returns an unknown-model error
- Added `model/chat_session.py`:
  - append-only local JSONL session storage under `runtime/chat_sessions/`
  - session load endpoint for UI restore
  - default session id remains `default`
- Updated `ui_backend.py`:
  - route preview now reads merged local env values instead of process env only
  - `/api/route-preview` now accepts current UI env values so unsaved visible inputs can drive route resolution
  - `/api/chat` accepts current UI config plus current env input values, resolves the route, calls the provider, and persists the turn
- Updated UI chat in `ui/app.js`, `ui/index.html`, and `ui/styles.css`:
  - removed fake dry-run reply behavior
  - sends real requests to `/api/chat`
  - loads saved session history from `/api/chat/session`
  - displays live/pending/error message states
  - uses the current visible config/env values rather than only the saved file state
  - updated English/Chinese chat copy to describe live behavior
- Updated docs:
  - `README.md`
  - `README.zh-CN.md`
  - both now state that the bounded live chat path exists for OpenAI-compatible providers and that chat turns are saved locally
- Added ignore rule:
  - `.gitignore` now ignores `runtime/chat_sessions/`
- Simplified the UI information architecture after user feedback that the settings were too hard to understand:
  - `gatewayView` now starts with a prominent Quick Start card
  - Quick Start only exposes the minimum path for a real model test: Provider, current provider values, model discovery, and a direct jump to Chat
  - Models page now folds custom provider management into a collapsed advanced section instead of showing it by default
  - Chat page now shows a current-route summary block above the message log
  - English/Chinese quick-start copy explains the three-step test flow instead of exposing internal concepts first
- Refined the Chat workspace after further user feedback:
  - chat top area is smaller and more compact
  - chat shell now behaves as a fixed workspace with the message log as the scrolling area
  - role/provider/mode/agent-mode/model controls are now placed under the input box instead of occupying the top bar
  - Chat page now exposes `chatModeSelect`, `chatAgentModeSelect`, `chatProviderSelect`, and `chatProviderModelSelect`
  - these controls are synced with the existing model routing state rather than introducing a separate config path
  - later refinement compressed the route summary from a multi-card block into compact inline chips
  - reduced chat-side fonts, paddings, bubble sizes, and composer density so the message log is visually dominant
  - chat control bar under the composer is now forced into a single desktop row with horizontal overflow instead of wrapping into multiple lines

## Real Smoke-Test Result

- Restarted UI server and verified health on `http://127.0.0.1:8765/`
- Current observed UI server PID: `18704`
- Real end-to-end smoke test succeeded through local `/api/chat` using a non-default session id:
  - session id: `smoke_test`
  - route mode: `live`
  - provider: `openai_glm_5_1_low`
  - assistant reply: `OK`
- Important observed nuance:
  - the configured model string included a vendor prefix
  - the provider endpoint expected the transport model id without that leading provider prefix
  - client-side fallback normalization now handles this class of mismatch

## Local Provider Readiness Snapshot

- Current local config source is still `config/model-providers.local.json`
- Active provider remains `openai_glm_5_1_high`
- A readiness scan without printing secrets found multiple providers with base URL, API key, and model configured, including:
  - `nvidia_glm5`
  - `nvidia_glm5_low`
  - `nvidia_glm5_medium`
  - `nvidia_glm5_high`
  - `nvidia_glm5_xhigh`
  - `openai_glm_5_1_high`
  - `openai_glm_5_1_low`
  - `openai_glm_5_1_medium`
  - `openai_glm_5_1_xhigh`
  - `openai_my_gpt_5_4`
  - `openai_my_gpt_5_4_low`
  - `openai_my_gpt_5_4_medium`
  - `openai_my_gpt_5_4_high`
  - `openai_my_gpt_5_4_xhigh`

## Verification Run

- `python -m py_compile ui_backend.py model\chat_session.py model\live_client.py`
- `node --check .\ui\app.js`
- `python -m unittest tests.test_ui_backend tests.test_local_env -v`
- `python .\check_runtime.py`
- `GET /api/health`
- `GET /`
- `GET /api/chat/session?session_id=default`
- real local smoke test through `POST /api/chat`
- `git diff --check`
- UI quick-start regression check:
  - `GET /` contains `quickProviderSelect`, `quickProviderFields`, and `quickProviderModelSelect`
  - `GET /app.js` contains `quickStartTitle` and `quickProviderSelect`
- Chat layout regression check:
  - `GET /` contains `chatModeSelect`, `chatProviderSelect`, and `chatProviderModelSelect`

`git diff --check` reported only LF-to-CRLF working-copy warnings for `ui/app.js` and `ui/styles.css`; no whitespace errors were reported.

## Current Worktree Highlights

- Modified tracked files relevant to the latest live-chat work:
  - `.gitignore`
  - `PROJECT_CONTEXT.md`
  - `README.md`
  - `README.zh-CN.md`
  - `tests/test_ui_backend.py`
  - `ui/app.js`
  - `ui/index.html`
  - `ui/styles.css`
  - `ui_backend.py`
- New tracked-intended files:
  - `model/chat_session.py`
  - `model/live_client.py`
- Other modified/untracked files from earlier ongoing work still exist in the worktree and are not part of this turn alone:
  - `cli_welcome.py`
  - `run_bot_channels.py`
  - `run_device_agent.py`
  - `run_ui.py`
  - `rust-core/README.md`
  - `rust-core/src/cli_banner.rs`
  - `rust-core/tests/cli_banner.rs`
  - `tests/test_cli_welcome.py`
  - `local_env.py`
  - `tests/test_local_env.py`

## Known Risks / Boundaries

- The current live model path is intentionally bounded to OpenAI-compatible chat-completions style providers.
- The broader model layer is still not a general multi-provider orchestration runtime.
- Some providers may still need model-id normalization or explicit UI model selection if their transport model names differ from locally grouped config labels.
- Session persistence is local JSONL only. There is no multi-session manager UI yet beyond the default session restore path.

## Next Useful Steps

- Surface the normalized transport model on successful fallback too, not only on failure.
- Add explicit new-session naming/creation in the chat rail instead of relying only on already-saved session ids.
- Extend the live client beyond OpenAI-compatible chat-completions only if a concrete provider protocol needs it.
- If requested, commit the current live-chat implementation and related UI/doc updates.

## 2026-04-15 Rust Boundary Correction

- Corrected the earlier over-split design. The repo no longer defines or depends on a custom user-global Rust support layer.
- Final boundary now follows the user rule:
  - Rust toolchain installation is environment-level and stays global
  - project build configuration stays in `rust-core/.cargo/config.toml`
  - project build outputs stay in `rust-core/target/`
- `runtime_backend.py` was reduced back to a standard cargo adapter:
  - resolve `cargo`
  - read the project target from `rust-core/.cargo/config.toml`
  - run project Rust bins from `rust-core/`
  - no auto-bootstrap, no custom global files, no global target cache
- Replaced the earlier custom global bootstrap script with `bootstrap_rust_env.py`:
  - manual use only
  - checks standard Rust environment
  - installs the required Rust target with `rustup target add ...` if missing
  - does not write custom global Python support files or move project artifacts
- Added/updated tests to verify:
  - `auto` falls back to Python when cargo is unavailable
  - project target comes from `rust-core/.cargo/config.toml`
  - project target dir resolves to `rust-core/target/`
  - bootstrap parsing of required target and rustup target-list output works as expected

## 2026-04-15 Rust Verification

- Passed:
  - `python -m py_compile runtime_backend.py bootstrap_rust_env.py tests\test_runtime_backend.py tests\test_bootstrap_rust_env.py`
  - `python -m unittest tests.test_runtime_backend tests.test_bootstrap_rust_env -v`
  - `python .\bootstrap_rust_env.py`
  - `python .\rust-core\check_skeleton.py`
  - `python .\rust-core\check_rust.py`
  - `python .\run_welcome.py --backend auto --no-color`
- Important observed fact:
  - Rust test binaries executed from `C:\Users\84915\device-agent-doc\rust-core\target\...`, confirming project build outputs returned to the project tree.
- Cleanup status:
  - removed the mistaken earlier custom global support directory and its project-specific contents
  - one older ACL-broken residue under `runtime\tmp-tests\` still resists deletion, so `.gitignore` now excludes `runtime/tmp-tests/` to keep the worktree clean

## 2026-04-15 Chat Model-Rejection Visibility

- Continued the live-chat UI work instead of changing the transport layer shape.
- Added structured provider-rejection metadata in `model/live_client.py` for unknown-model failures:
  - `error_kind = provider_model_rejected`
  - includes `configured_model`
  - includes `tried_models`
  - includes `suggested_transport_model` when a vendor-prefix-stripped candidate exists
  - includes provider-returned error text and HTTP status when available
- Updated `ui_backend.py` so `/api/chat` returns structured JSON error payloads with route/provider/model context instead of flattening everything into one generic error string.
- Updated `ui/app.js` so chat failures render actionable multi-line guidance in the message bubble:
  - explicit provider/model rejection line
  - provider-returned message
  - tried transport model ids
  - suggested transport model when available
  - reminder to fetch `/models` if the endpoint uses different transport ids
- Updated `ui/styles.css` so chat bubbles preserve line breaks and these multi-line error messages remain readable.
- Added regression coverage in `tests/test_ui_backend.py` for the `/api/chat` model-rejection path, including `suggested_transport_model` and `tried_models`.

## 2026-04-15 Chat Model-Rejection Verification

- Passed:
  - `python -m py_compile ui_backend.py model\live_client.py tests\test_ui_backend.py`
  - `node --check .\ui\app.js`
  - `python -m unittest tests.test_ui_backend -v`
  - `git diff --check`
- `git diff --check` reported only LF-to-CRLF working-copy warnings for tracked files; no whitespace errors were reported.

## 2026-04-15 Chat Session Rail

- Continued the chat usability work after model-rejection visibility.
- Added session management primitives in `model/chat_session.py`:
  - list saved chat sessions from `runtime/chat_sessions/`
  - keep `default` visible even when no file exists yet
  - clear a saved session by deleting its JSONL file
- Updated `ui_backend.py` with:
  - `GET /api/chat/sessions`
  - `POST /api/chat/session/clear`
- Updated the chat rail UI in `ui/index.html`, `ui/app.js`, and `ui/styles.css`:
  - the left rail now renders the real saved session list instead of a static default-only pill
  - selecting a session loads that session's saved transcript into the chat workspace
  - a clear-session button removes the current session's saved file and refreshes the rail
  - rail entries now show turn count and a short preview snippet
- Added regression coverage in `tests/test_ui_backend.py` for session listing and clear-session endpoints.

## 2026-04-15 Chat Session Rail Verification

- Passed:
  - `python -m py_compile ui_backend.py model\live_client.py model\chat_session.py tests\test_ui_backend.py`
  - `node --check .\ui\app.js`
  - `python -m unittest tests.test_ui_backend -v`
  - `git diff --check`
- `git diff --check` again reported only LF-to-CRLF working-copy warnings for tracked files; no whitespace errors were reported.

## 2026-04-15 Cleanup Residue Status

- Re-checked repository cleanup status after the chat work.
- The only stubborn leftover remains:
  - `runtime/tmp-tests/tmpn758tavm`
- Confirmed this residue is an ACL/permission problem, not a normal untracked temp directory:
  - plain `Remove-Item` failed with access denied
  - `takeown`, `Rename-Item`, and `cmd /c rd /s /q` also failed from the current non-elevated shell
- Current shell identity is `desktop-ohfsmgr\feng`, and the session is not running as Administrator.
- Prepared an external helper script for elevated cleanup instead of changing repo code:
  - `C:\Users\84915\cleanup_device_agent_tmp_tests.ps1`
- `.gitignore` still excludes both `runtime/chat_sessions/` and `runtime/tmp-tests/`, so the residue does not affect git status beyond warning output when commands enumerate that path.

## 2026-04-15 Cleanup Residue Resolution

- The earlier ACL-broken `runtime/tmp-tests/tmpn758tavm` residue was removed successfully through the elevated cleanup script.
- Re-checks after cleanup confirmed:
  - `runtime/tmp-tests/` no longer contained the broken directory
  - `git status --ignored --short runtime` no longer reported the previous access warning
- `runtime/tmp-tests/` remains ignored in `.gitignore`, but the repository no longer has the earlier cleanup blocker.

## 2026-04-15 Chat Workspace Redesign

- Reshaped `chatView` to follow the OpenClaw-style information architecture without copying features the repo does not have.
- Kept the global left navigation because this project is a multi-surface local control console, not a chat-only product.
- Replaced the old chat-internal left rail with a single chat workspace composed of:
  - breadcrumb/title header
  - top context bar for session, provider, and model
  - secondary control row for role, model mode, agent mode, and model/session actions
  - compact route summary band
  - horizontal recent-session strip
  - single message log and composer
- Preserved existing live-chat behavior and backend contracts:
  - kept `/api/chat`, `/api/chat/session`, `/api/chat/sessions`, and `/api/chat/session/clear`
  - kept existing chat routing controls and model-fetch/apply actions
  - kept session selection by click while also adding a top session dropdown and active-session badge
- Updated `ui/index.html`, `ui/app.js`, and `ui/styles.css` so the redesign mostly reuses the prior state flow and DOM IDs instead of inventing a new interaction path.
- Added DOM regression checks in `tests/test_ui_backend.py` for the new `chatSessionSelect` and `chatSessionBadge` anchors.

## 2026-04-15 Chat Workspace Verification

- Passed:
  - `node --check .\ui\app.js`
  - `python -m py_compile ui_backend.py model\live_client.py model\chat_session.py tests\test_ui_backend.py`
  - `python -m unittest tests.test_ui_backend -v`
  - `git diff --check`
- `git diff --check` again reported only LF-to-CRLF working-copy warnings; no whitespace errors were reported.
- Performed a local visual check by starting the UI on `http://127.0.0.1:8876/`, switching to Chat, and confirming the new workspace shape:
  - top context selectors rendered
  - recent-session strip rendered under the route summary
  - message log and composer remained functional in the redesigned layout

## 2026-04-15 Chat Turn Cards

- Continued the OpenClaw-inspired chat redesign without adding fake backend capabilities.
- Kept the same message/session payloads, but changed the chat rendering layer in `ui/app.js` to group the linear `chatMessages` array into per-turn UI cards.
- Each turn now renders as:
  - a compact prompt card for the user input
  - a larger assistant result card
  - metadata chips derived only from existing fields already present in the message/route payload:
    - agent id
    - provider name
    - model
    - mode
    - role
- Added a status pill on assistant result cards for normal / pending / error states instead of relying only on plain text styling.
- Updated `sendChatMessage()` so in-memory user messages also carry the selected role, allowing prompt/result cards to stay aligned inside the same turn.
- Updated `ui/styles.css` so the chat log now reads as a sequence of run cards instead of a simple bubble list.

## 2026-04-15 Chat Turn Card Verification

- Passed:
  - `node --check .\ui\app.js`
  - `python -m py_compile ui_backend.py model\live_client.py model\chat_session.py tests\test_ui_backend.py`
  - `python -m unittest tests.test_ui_backend -v`
- Performed a second local visual check on `http://127.0.0.1:8877/`:
  - chat turns rendered as prompt/result card pairs
  - assistant cards rendered the expected route-derived chips
  - existing saved-session content still displayed correctly in the new grouped layout

## 2026-04-15 Chat Top Context Density

- Continued the OpenClaw-inspired redesign by increasing the information density of the chat workspace header instead of changing backend behavior.
- Reworked the old compact route chip row into a structured route context panel in `ui/app.js` / `ui/styles.css`:
  - route header copy
  - five stat cards for agent, provider, model, mode, and role
- Added an active-session summary card beside the recent-session strip:
  - current session id
  - updated timestamp when available
  - preview text
  - compact chips for session count, provider, and model
- Enriched session pills with a compact timestamp row while keeping the same selection behavior and underlying session payloads.
- Added a small DOM regression check for the new `chatSessionSummary` container.
- Ensured language switching now also re-renders chat-session UI so localized timestamps and labels stay in sync with the selected locale.

## 2026-04-15 Chat Top Context Verification

- Passed:
  - `node --check .\ui\app.js`
  - `python -m py_compile ui_backend.py model\live_client.py model\chat_session.py tests\test_ui_backend.py`
  - `python -m unittest tests.test_ui_backend -v`
- Performed a third local visual check on `http://127.0.0.1:8878/`:
  - route context rendered as stat cards instead of loose chips
  - active-session summary card rendered beside the session strip
  - session pills rendered compact timestamps without breaking selection layout

## 2026-04-15 Sidebar Hierarchy Refresh

- Continued the OpenClaw-inspired UI alignment by redesigning the global left sidebar instead of only refining the chat workspace.
- Kept the same navigation behavior and `data-view` bindings, but restructured the sidebar markup in `ui/index.html`:
  - compact brand cluster with `brand-mark`
  - smaller product/title stack with `heroLede`
  - compact console/status block under the brand
  - section headers now render a small count badge
  - nav items now render a glyph column plus copy column
- Updated `ui/styles.css` so the sidebar now reads as a control-plane rail rather than a large hero banner:
  - reduced visual dominance of the old sidebar title
  - tightened spacing and hierarchy
  - stronger grouping boundaries between navigation sections
  - active navigation state now highlights both the item and its glyph tile
- Added a minimal DOM regression check in `tests/test_ui_backend.py` for `brand-mark` and `nav-section__count`.

## 2026-04-15 Sidebar Verification

- Passed:
  - `node --check .\ui\app.js`
  - `python -m py_compile ui_backend.py model\live_client.py model\chat_session.py tests\test_ui_backend.py`
  - `python -m unittest tests.test_ui_backend -v`
  - `git diff --check`
- `git diff --check` again reported only LF-to-CRLF working-copy warnings; no whitespace errors were reported.
- Performed a local visual check on `http://127.0.0.1:8879/`:
  - sidebar brand block rendered in the new compact format on the dashboard view
  - grouped navigation and active item treatment remained correct on the chat view

## 2026-04-15 Workbench Header Refresh

- Continued the UI unification by redesigning the global right-side `workbench-head` so non-chat views share more of the same control-plane language already used in the chat workspace.
- Kept the existing `viewEyebrow`, `viewTitle`, `viewDescription`, and `sourceBadge` behavior, but restructured the header in `ui/index.html` to include:
  - a kicker row
  - a metadata chip row
  - a right-side source/status stack
  - compact stat cards for provider count, route count, and channel count
- Added lightweight header-state rendering in `ui/app.js`:
  - current provider
  - current model mode
  - current agent mode
  - provider / route / channel counts derived from current in-memory state
- Ensured the header state re-renders when:
  - config loads/renders
  - bot channels load
  - view header copy changes
- Added DOM regression checks for:
  - `workbenchViewMeta`
  - `workbenchProviderCount`

## 2026-04-15 Workbench Header Verification

- Passed:
  - `node --check .\ui\app.js`
  - `python -m py_compile ui_backend.py model\live_client.py model\chat_session.py tests\test_ui_backend.py`
  - `python -m unittest tests.test_ui_backend -v`
- Local run state:
  - UI server is currently running at `http://127.0.0.1:8880/`
  - browser launch was requested after startup so the user can inspect the latest UI directly

## 2026-04-15 Saved OpenClaw HTML Mapping

- The user provided a local reference bundle under `C:\Users\84915\Downloads\openclawui`.
- Mapped the saved HTML files by the active breadcrumb/page content:
  - `page-with-style.html` -> chat page
  - `page-with-style (4).html` -> overview page
  - `page-with-style (2).html` -> config page
  - `page-with-style (3).html` -> usage page
  - `page-with-style (1).html` -> skills page
- Decided to use the saved HTML files as the primary source of truth instead of prior screenshot-only inference.
- Current alignment priority after mapping:
  - chat page
  - overview page
  - config page

## 2026-04-15 Reference Shell Alignment

- Began replacing the previous warm/glass approximation with a darker shell patterned directly after the saved OpenClaw chat/overview/config HTML.
- Updated `ui/index.html` root structure from the old two-column `app-frame` into a reference-style shell:
  - `#appShell.shell`
  - sticky `topbar`
  - `shell-nav`
  - `content` work area
- Added shell controls while preserving current app behavior and ids:
  - `#navCollapseButton`
  - `#navDrawerToggleButton`
  - `#shellNavBackdrop`
  - topbar breadcrumb/status anchors
- Simplified the sidebar to a compact control-plane rail:
  - removed the oversized hero/dragon treatment
  - kept `brand-mark`, nav sections, counts, and `data-view` bindings
  - moved status/language into a compact footer stack
- Added lightweight nav state in `ui/app.js`:
  - desktop collapse state persisted in local storage
  - mobile drawer open/close state
  - shell `data-active-view` flag so the global header can hide on chat
- Updated topbar/workbench header state rendering so current view, source, provider, mode, and agent mode are reflected in the new shell chrome.
- Changed chat rendering from paired turn cards to reference-style grouped message rows:
  - avatar column
  - bubble row per message
  - footer metadata chips and timestamp
  - assistant-side execution context card derived only from existing route/mode fields
- Extended `model/chat_session.py` so session payload messages now include timestamps, enabling chat footer timestamps without inventing data.
- Added DOM regression checks for the new shell anchors:
  - `appShell`
  - `shell-nav`
  - `topbarViewTitle`

## 2026-04-15 Reference Shell Verification

- Passed:
  - `node --check .\ui\app.js`
  - `python -m py_compile ui_backend.py model\live_client.py model\chat_session.py tests\test_ui_backend.py`
  - `python -m unittest tests.test_ui_backend -v`
  - `git diff --check`
- `git diff --check` reported only existing LF-to-CRLF working-copy warnings; no whitespace errors were introduced.
- Confirmed the already-running local UI process on `http://127.0.0.1:8880/` is still healthy via `/api/health`.

## 2026-04-16 Chat UX Reset

- Reframed the current UI pass around first-principles chat usability instead of closer visual mimicry.
- Main problem statement for this round:
  - the app opened into an overloaded dashboard instead of the primary task
  - chat put setup controls ahead of reading and sending messages
  - sending behavior used developer-centric `Ctrl/Cmd+Enter` rather than default chat interaction
- Updated `ui/index.html` to make chat the default active view and re-order the chat page around the primary task:
  - compact top bar with session picker, active session badge, route badge, and clear action
  - visible recent session strip
  - message log before any advanced configuration
  - composer converted to a real form (`#chatComposerForm`)
  - advanced provider/model/role/mode controls moved into collapsed `#chatSetupPanel`
- Updated `ui/app.js` accordingly:
  - default `activeView` is now `chatView`
  - invalid/fallback view resolution now returns to chat instead of gateway
  - chat submit is handled through form submit
  - textarea behavior changed to:
    - `Enter` sends
    - `Shift+Enter` inserts newline
  - added new i18n copy for folded diagnostics/setup labels and revised chat description/composer note in both English and Chinese
- Updated `ui/styles.css` to support the new usability-focused layout:
  - compact chat primary bar
  - non-sticky composer aligned under the log
  - folded diagnostics/setup panels
  - single-column quick-start fold treatment
  - reduced visual prominence of advanced chat controls
- Added DOM regression checks in `tests/test_ui_backend.py` for:
  - `chatComposerForm`
  - `chatSetupPanel`

## 2026-04-16 Chat UX Verification

- Passed:
  - `node --check .\ui\app.js`
  - `python -m py_compile ui_backend.py model\live_client.py model\chat_session.py tests\test_ui_backend.py`
  - `python -m unittest tests.test_ui_backend -v`
  - `git diff --check`
- `git diff --check` still reports only LF-to-CRLF working-copy warnings.
- Browser-level local verification on `http://127.0.0.1:8880/` confirmed:
  - initial load lands directly on chat
  - the session picker and send box are visible without opening setup
  - pressing `Enter` sends immediately
  - the textarea clears after send
  - the new message appears in the chat log and session preview

## 2026-04-16 Fixed-Height Shell Correction

- After user review, identified a more fundamental layout problem:
  - the interface was still behaving like a long document page instead of a fixed-height application shell
  - `workbench` content stacked vertically in the normal page flow
  - `chat-workspace` still carried a viewport-based `min-height` that encouraged overlong layout
- Updated `ui/styles.css` to enforce application-style shell behavior:
  - `html`, `body`, and `.shell` are now fixed to viewport height with document scrolling disabled
  - `.workbench` is now a column flex container with internal view scrolling instead of page scrolling
  - `.view-panel.active` fills the remaining work area and scrolls internally
  - chat view is a stricter special case:
    - active chat panel itself does not page-scroll
    - `.chat-workspace` is a full-height column layout
    - `.chat-log` owns the remaining height and becomes the primary scroll region
- This correction keeps the whole window visually pinned while preserving access to tall secondary pages through internal panel scrolling.

## 2026-04-16 Fixed-Height Verification

- Passed:
  - `python -m unittest tests.test_ui_backend -v`
  - `git diff --check`
- Browser-level verification with the running localhost UI confirmed:
  - `document.scrollingElement.scrollHeight <= window.innerHeight + 1` on chat
  - the same fixed-height condition also holds on dashboard and models views
  - screenshots captured after the correction:
    - `C:\Users\84915\Downloads\uxshots\screenshot-1776306176049.png`

## 2026-04-16 Chat Noise Reduction

- The fixed-height shell still left the chat page too noisy because too much secondary information remained in the primary viewport.
- Applied a stricter first-principles rule for chat:
  - visible default surface should only prioritize:
    - choosing the current session
    - reading messages
    - sending the next message
  - everything else must leave the main canvas
- Updated `ui/index.html` chat structure accordingly:
  - removed visible session summary card and visible recent-session ribbon from the main chat canvas
  - moved session history and route/provider controls into the setup dropdown
  - removed the composer note from the visible chat footer
  - kept `chatSessionBadge` / `chatRouteBadge` in DOM but out of the visible layout so existing state flow stays intact
- Updated `ui/app.js` chat rendering:
  - assistant messages no longer prepend the route-context card in the visible conversation stream
  - footer metadata chips are no longer rendered in the visible chat footer
  - sender labels were simplified to plain `You` / `Device Agent`
  - route preview inside setup is now a compact chip row instead of a large five-card panel
  - session summary/list rendering was reduced to compact text and pills instead of card-like blocks
- Updated `ui/styles.css`:
  - setup became a compact header dropdown instead of a large bottom block
  - chat top bar reduced to a session select plus setup trigger
  - chat log styling was simplified to let message bubbles dominate the available space
  - composer reduced to a compact single-bar input shell
  - chat-page global status line is hidden while chat is the active view

## 2026-04-16 Chat Noise Verification

- Passed:
  - `node --check .\ui\app.js`
  - `python -m unittest tests.test_ui_backend -v`
  - `git diff --check`
- Browser verification on the running localhost UI confirmed:
  - the chat viewport now exposes only session select, setup trigger, message stream, and composer on first view
  - the previous bottom status/path line no longer appears on chat
  - screenshots captured after the simplification:
    - `C:\Users\84915\Downloads\uxshots\screenshot-1776317302483.png`
    - `C:\Users\84915\Downloads\uxshots\screenshot-1776317391414.png`
