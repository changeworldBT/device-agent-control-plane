# Project Context

Last updated: 2026-04-10

## Standing Instruction

After every substantial execution turn, update this file before the final response. Preserve enough context for a future session to resume without relying on chat history. Do not record secrets, tokens, private webhook URLs, or credential values.

## Current Branch State

- Repository: `C:\Users\84915\device-agent-doc`
- Branch: `main`
- Remote state before committing the bot-channel work: `main...origin/main [ahead 1]`
- Existing local commit ahead of origin: `edc9743 Add provider config UI and OpenClaw migration`
- This context snapshot is saved with the bot-channel/context-preservation commit. After that commit is created, the branch is expected to be ahead of origin by 2 local commits until pushed.

## Implemented In Latest Work

- Added mainstream bot-channel configuration and dispatch preview support.
- Supported channel kinds in config/schema: `telegram`, `whatsapp_cloud`, `feishu_webhook`, `qq_official`, and `generic_webhook`.
- Added CLI entrypoint `run_bot_channels.py`, defaulting to local bot config when present and example config otherwise.
- Added `channels/bot_config.py` and `channels/bot_gateway.py`.
- Added UI backend endpoints for bot-channel listing and preview.
- Added a Bot Channels panel to the local static UI.
- Added bot-channel environment-variable placeholders to `.env.example`.
- Updated README English and Chinese docs with bot-channel setup, current boundaries, and preview commands.
- Added schema validation and unit tests for bot channels.

## Important Boundaries

- Telegram, WhatsApp Cloud API, Feishu/Lark webhook, and generic webhook support is outbound text dispatch first.
- Live dispatch is gated by `mode=live`, enabled channel config, explicit `--live`, and complete environment variables.
- Feishu/Lark signed webhook live send is blocked until request signing is implemented.
- QQ official bot remains dry-run only until a dedicated official gateway/OpenAPI adapter is implemented. It is intentionally not treated as a generic webhook.
- Webhook preview output redacts URLs to host-level form to avoid leaking path or query tokens.

## Verification Already Run

- `python -m unittest tests.test_bot_channels tests.test_ui_backend -v`
- `python .\schemas\validate_examples.py`
- `python .\run_bot_channels.py --list`
- `python .\run_bot_channels.py --channel qq_ops --text hello`
- `python .\run_bot_channels.py --channel telegram_ops --text hello`
- `python .\check_runtime.py`
- `node --check .\ui\app.js`
- `git diff --check`

`git diff --check` reported only LF-to-CRLF working-copy warnings for `.env.example`, `ui/app.js`, and `ui/styles.css`; no whitespace errors were reported.

## Scope Saved In Bot-Channel Commit

- Modified tracked files: `.env.example`, `README.md`, `README.zh-CN.md`, `schemas/validate_examples.py`, `tests/test_ui_backend.py`, `ui/app.js`, `ui/index.html`, `ui/styles.css`, `ui_backend.py`
- New files: `AGENTS.md`, `PROJECT_CONTEXT.md`, `channels/bot_config.py`, `channels/bot_gateway.py`, `config/bot-channels.example.json`, `run_bot_channels.py`, `schemas/json-schema/bot-channel-config.schema.json`, `tests/test_bot_channels.py`

## Next Useful Steps

- If requested, push the two local commits to origin.
- Implement the dedicated QQ official bot adapter only after choosing the specific QQ official gateway/OpenAPI auth and target model.
- Implement Feishu signed webhook request signing before enabling live sends for signed Feishu bots.
- Add inbound webhook/gateway handling if the product goal moves from outbound notification to interactive bot conversation.
