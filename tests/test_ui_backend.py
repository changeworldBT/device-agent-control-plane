from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request
from urllib.request import urlopen
from unittest import mock

from channels.bot_config import load_bot_channel_config
from channels.bot_gateway import EXAMPLE_CONFIG as BOT_EXAMPLE_CONFIG
from model.chat_session import append_chat_turn, chat_session_payload, clear_chat_session, list_chat_sessions, load_chat_turns
from model.provider_config import load_model_config
from ui_backend import EXAMPLE_CONFIG, chat_payload, env_values_payload, fetch_provider_models, make_handler, route_preview


class UiBackendTests(unittest.TestCase):
    def test_route_preview_redacts_secret_values(self) -> None:
        config = load_model_config(EXAMPLE_CONFIG)
        old_key = os.environ.get("DEVICE_AGENT_PRIMARY_API_KEY")
        os.environ["DEVICE_AGENT_PRIMARY_API_KEY"] = "secret-value"

        try:
            routes = route_preview(config)
        finally:
            if old_key is None:
                os.environ.pop("DEVICE_AGENT_PRIMARY_API_KEY", None)
            else:
                os.environ["DEVICE_AGENT_PRIMARY_API_KEY"] = old_key

        self.assertEqual([route["role"] for route in routes], ["planner", "classifier", "summarizer", "verifier"])
        self.assertTrue(all("api_key_configured" in route for route in routes))
        self.assertTrue(routes[0]["api_key_configured"])
        self.assertNotIn("secret", str(routes).lower())

    def test_route_preview_rejects_unknown_provider(self) -> None:
        config = copy.deepcopy(load_model_config(EXAMPLE_CONFIG))
        config["default_provider"] = "missing_provider"

        with self.assertRaisesRegex(ValueError, "unknown entry"):
            route_preview(config)

    def test_ui_server_exposes_health_config_and_index(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"

        try:
            health = json.loads(urlopen(f"{base_url}/api/health", timeout=5).read().decode("utf-8"))
            config = json.loads(urlopen(f"{base_url}/api/config", timeout=5).read().decode("utf-8"))
            channels = json.loads(urlopen(f"{base_url}/api/bot-channels", timeout=5).read().decode("utf-8"))
            env_values = json.loads(urlopen(f"{base_url}/api/env", timeout=5).read().decode("utf-8"))
            index = urlopen(f"{base_url}/", timeout=5).read().decode("utf-8")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(health["status"], "ok")
        self.assertIn("config", config)
        self.assertTrue(any(channel["kind"] == "telegram" for channel in channels["channels"]))
        self.assertIsInstance(env_values["fields"], list)
        self.assertIn("Device Agent Console", index)
        self.assertIn("appShell", index)
        self.assertIn("shell-nav", index)
        self.assertIn("topbarViewTitle", index)
        self.assertIn("side-nav", index)
        self.assertIn("nav-section", index)
        self.assertIn("brand-mark", index)
        self.assertIn("nav-section__count", index)
        self.assertIn("workbenchViewMeta", index)
        self.assertIn("workbenchProviderCount", index)
        self.assertIn("dashboardAttentionList", index)
        self.assertIn("quickProviderSelect", index)
        self.assertIn("quickProviderFields", index)
        self.assertIn("quickProviderModelSelect", index)
        self.assertIn("providerManagement", index)
        self.assertIn("selectedProviderDetail", index)
        self.assertIn("selectedChannelDetail", index)
        self.assertIn("fetchProviderModelsButton", index)
        self.assertIn("chatModeSelect", index)
        self.assertIn("chatProviderSelect", index)
        self.assertIn("chatProviderModelSelect", index)
        self.assertIn("chatSessionSelect", index)
        self.assertIn("chatSessionBadge", index)
        self.assertIn("chatSessionSummary", index)
        self.assertIn("chatCurrentRoute", index)
        self.assertIn("chatComposerForm", index)
        self.assertIn("chatSetupPanel", index)
        self.assertIn("chatView", index)
        self.assertIn("languageSelect", index)
        self.assertNotIn("valuesView", index)

    def test_env_values_payload_echoes_local_values_for_config_refs(self) -> None:
        model_config = load_model_config(EXAMPLE_CONFIG)
        bot_config = load_bot_channel_config(BOT_EXAMPLE_CONFIG)
        payload = env_values_payload(
            model_config=model_config,
            bot_config=bot_config,
            env_values={
                "DEVICE_AGENT_PRIMARY_API_KEY": "secret-value",
                "DEVICE_AGENT_PRIMARY_BASE_URL": "https://models.example.test/v1",
                "TELEGRAM_BOT_TOKEN": "telegram-secret",
            },
        )

        fields = {field["key"]: field for field in payload["fields"]}
        self.assertEqual(fields["DEVICE_AGENT_PRIMARY_API_KEY"]["value"], "secret-value")
        self.assertEqual(fields["DEVICE_AGENT_PRIMARY_BASE_URL"]["value"], "https://models.example.test/v1")
        self.assertEqual(fields["TELEGRAM_BOT_TOKEN"]["value"], "telegram-secret")
        self.assertTrue(fields["DEVICE_AGENT_PRIMARY_API_KEY"]["secret_like"])

    def test_fetch_provider_models_reads_openai_compatible_model_list(self) -> None:
        class ModelListHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path != "/v1/models":
                    self.send_response(404)
                    self.end_headers()
                    return
                payload = json.dumps({"data": [{"id": "model-a"}, {"id": "model-b"}]}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), ModelListHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}/v1"

        try:
            models = fetch_provider_models(base_url, "secret-value")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(models, ["model-a", "model-b"])
        self.assertNotIn("secret-value", str(models))

    def test_route_preview_uses_supplied_env_values(self) -> None:
        config = load_model_config(EXAMPLE_CONFIG)
        routes = route_preview(
            config,
            env_values={
                "DEVICE_AGENT_PRIMARY_API_KEY": "secret-value",
                "DEVICE_AGENT_PRIMARY_BASE_URL": "https://models.example.test/v1",
                "DEVICE_AGENT_PRIMARY_MODEL": "provider-model",
                "DEVICE_AGENT_SMALL_MODEL": "small-model",
            },
        )

        planner = routes[0]
        self.assertEqual(planner["provider_name"], "primary_cloud")
        self.assertTrue(planner["api_key_configured"])
        self.assertEqual(planner["base_url"], "https://models.example.test/v1")
        self.assertNotIn("secret-value", str(routes))

    def test_chat_payload_live_invocation_saves_session(self) -> None:
        class ChatHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                if self.path != "/v1/chat/completions":
                    self.send_response(404)
                    self.end_headers()
                    return

                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                assert self.headers.get("Authorization") == "Bearer secret-value"
                messages = body.get("messages", [])
                assert messages[0]["role"] == "system"
                assert messages[-1]["content"] == "Say hello"
                if body.get("model") == "vendor/stub-model":
                    payload = json.dumps({"error": {"message": "Unknown model: vendor/stub-model"}}).encode("utf-8")
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                assert body.get("model") == "stub-model"

                payload = json.dumps(
                    {
                        "id": "chatcmpl-test",
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {"role": "assistant", "content": "hello from live stub"},
                            }
                        ],
                        "usage": {"total_tokens": 21},
                    }
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: object) -> None:
                return

        provider_server = ThreadingHTTPServer(("127.0.0.1", 0), ChatHandler)
        provider_thread = threading.Thread(target=provider_server.serve_forever, daemon=True)
        provider_thread.start()
        base_url = f"http://127.0.0.1:{provider_server.server_port}/v1"

        config = {
            "$schema": "../schemas/json-schema/model-config.schema.json",
            "version": 1,
            "mode": "live",
            "default_provider": "live_stub",
            "active_provider": "live_stub",
            "providers": {
                    "live_stub": {
                        "kind": "openai_compatible",
                        "base_url_env": "TEST_BASE_URL",
                        "api_key_env": "TEST_API_KEY",
                        "default_model": "vendor/stub-model",
                        "capabilities": ["planner"],
                    }
                },
            "agents": {
                "mode": "single_agent",
                "default_agent": "tester",
                "members": {
                    "tester": {
                        "provider": "live_stub",
                        "roles": ["planner"],
                        "system_contract": "Return concise replies only.",
                    }
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir)
            with (
                mock.patch("ui_backend.load_chat_turns", side_effect=lambda session_id: load_chat_turns(session_id, session_dir=session_dir)),
                mock.patch(
                    "ui_backend.append_chat_turn",
                    side_effect=lambda session_id, *, route, user_message, assistant_message: append_chat_turn(
                        session_id,
                        route=route,
                        user_message=user_message,
                        assistant_message=assistant_message,
                        session_dir=session_dir,
                    ),
                ),
            ):
                payload = chat_payload(
                    {
                        "session_id": "default",
                        "role": "planner",
                        "message": "Say hello",
                        "config": config,
                        "env_values": {
                            "DEVICE_AGENT_MODEL_MODE": "live",
                            "DEVICE_AGENT_AGENT_MODE": "single_agent",
                            "TEST_BASE_URL": base_url,
                            "TEST_API_KEY": "secret-value",
                        },
                    }
                )
                saved_session = chat_session_payload("default", session_dir=session_dir)

        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=5)

        self.assertEqual(payload["reply"], "hello from live stub")
        self.assertEqual(payload["provider_name"], "live_stub")
        self.assertEqual(saved_session["count"], 1)
        self.assertEqual(saved_session["messages"][0]["text"], "Say hello")
        self.assertEqual(saved_session["messages"][1]["text"], "hello from live stub")
        self.assertNotIn("secret-value", str(payload))

    def test_ui_server_chat_returns_structured_model_rejection_payload(self) -> None:
        class RejectingChatHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                if self.path != "/v1/chat/completions":
                    self.send_response(404)
                    self.end_headers()
                    return

                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                model = body.get("model") or "unknown"
                payload = json.dumps({"error": {"message": f"Unknown model: {model}"}}).encode("utf-8")
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: object) -> None:
                return

        provider_server = ThreadingHTTPServer(("127.0.0.1", 0), RejectingChatHandler)
        provider_thread = threading.Thread(target=provider_server.serve_forever, daemon=True)
        provider_thread.start()
        provider_base_url = f"http://127.0.0.1:{provider_server.server_port}/v1"

        ui_server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler())
        ui_thread = threading.Thread(target=ui_server.serve_forever, daemon=True)
        ui_thread.start()
        ui_base_url = f"http://127.0.0.1:{ui_server.server_port}"

        config = {
            "$schema": "../schemas/json-schema/model-config.schema.json",
            "version": 1,
            "mode": "live",
            "default_provider": "live_stub",
            "active_provider": "live_stub",
            "providers": {
                "live_stub": {
                    "kind": "openai_compatible",
                    "base_url_env": "TEST_BASE_URL",
                    "api_key_env": "TEST_API_KEY",
                    "default_model": "vendor/missing-model",
                    "capabilities": ["planner"],
                }
            },
            "agents": {
                "mode": "single_agent",
                "default_agent": "tester",
                "members": {
                    "tester": {
                        "provider": "live_stub",
                        "roles": ["planner"],
                        "system_contract": "Return concise replies only.",
                    }
                },
            },
        }

        request = Request(
            f"{ui_base_url}/api/chat",
            data=json.dumps(
                {
                    "session_id": "default",
                    "role": "planner",
                    "message": "Say hello",
                    "config": config,
                    "env_values": {
                        "DEVICE_AGENT_MODEL_MODE": "live",
                        "DEVICE_AGENT_AGENT_MODE": "single_agent",
                        "TEST_BASE_URL": provider_base_url,
                        "TEST_API_KEY": "secret-value",
                    },
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with self.assertRaises(HTTPError) as context:
                urlopen(request, timeout=5)
            payload = json.loads(context.exception.read().decode("utf-8"))
        finally:
            ui_server.shutdown()
            ui_server.server_close()
            ui_thread.join(timeout=5)
            provider_server.shutdown()
            provider_server.server_close()
            provider_thread.join(timeout=5)

        self.assertEqual(context.exception.code, 400)
        self.assertEqual(payload["error_kind"], "provider_model_rejected")
        self.assertEqual(payload["provider_name"], "live_stub")
        self.assertEqual(payload["model"], "vendor/missing-model")
        self.assertEqual(payload["tried_models"], ["vendor/missing-model", "missing-model"])
        self.assertEqual(payload["suggested_transport_model"], "missing-model")
        self.assertEqual(payload["route"]["provider_name"], "live_stub")
        self.assertEqual(payload["route"]["model"], "vendor/missing-model")
        self.assertIn("provider rejected configured model", payload["error"])
        self.assertNotIn("secret-value", str(payload))

    def test_ui_server_chat_session_endpoint_reads_saved_messages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir)
            config = load_model_config(EXAMPLE_CONFIG)
            route = next(iter(route_preview(config)))
            append_chat_turn(
                "default",
                route=type(
                    "Route",
                    (),
                    {
                        "role": route["role"],
                        "mode": route["mode"],
                        "provider_kind": route["provider_kind"],
                        "agent_id": route["agent_id"],
                        "provider_name": route["provider_name"],
                        "model": route["model"],
                    },
                )(),
                user_message="saved user",
                assistant_message="saved assistant",
                session_dir=session_dir,
            )

            with mock.patch(
                "ui_backend.chat_session_payload",
                side_effect=lambda session_id: chat_session_payload(session_id, session_dir=session_dir),
            ):
                server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler())
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                base_url = f"http://127.0.0.1:{server.server_port}"

                try:
                    payload = json.loads(
                        urlopen(f"{base_url}/api/chat/session?session_id=default", timeout=5).read().decode("utf-8")
                    )
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)

        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["messages"][0]["text"], "saved user")
        self.assertEqual(payload["messages"][1]["text"], "saved assistant")

    def test_ui_server_chat_sessions_list_and_clear_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir)
            config = load_model_config(EXAMPLE_CONFIG)
            route = next(iter(route_preview(config)))
            route_obj = type(
                "Route",
                (),
                {
                    "role": route["role"],
                    "mode": route["mode"],
                    "provider_kind": route["provider_kind"],
                    "agent_id": route["agent_id"],
                    "provider_name": route["provider_name"],
                    "model": route["model"],
                },
            )()

            append_chat_turn(
                "default",
                route=route_obj,
                user_message="default user",
                assistant_message="default assistant",
                session_dir=session_dir,
            )
            append_chat_turn(
                "smoke_test",
                route=route_obj,
                user_message="smoke user",
                assistant_message="smoke assistant",
                session_dir=session_dir,
            )

            with (
                mock.patch(
                    "ui_backend.list_chat_sessions",
                    side_effect=lambda: list_chat_sessions(session_dir=session_dir),
                ),
                mock.patch(
                    "ui_backend.clear_chat_session",
                    side_effect=lambda session_id: clear_chat_session(session_id, session_dir=session_dir),
                ),
            ):
                server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler())
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                base_url = f"http://127.0.0.1:{server.server_port}"
                clear_request = Request(
                    f"{base_url}/api/chat/session/clear",
                    data=b'{"session_id":"smoke_test"}',
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )

                try:
                    sessions_payload = json.loads(urlopen(f"{base_url}/api/chat/sessions", timeout=5).read().decode("utf-8"))
                    cleared_payload = json.loads(urlopen(clear_request, timeout=5).read().decode("utf-8"))
                    sessions_after_clear = json.loads(urlopen(f"{base_url}/api/chat/sessions", timeout=5).read().decode("utf-8"))
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)

        self.assertEqual([item["session_id"] for item in sessions_payload["sessions"]], ["default", "smoke_test"])
        self.assertEqual(cleared_payload["session_id"], "smoke_test")
        self.assertTrue(cleared_payload["removed"])
        self.assertEqual([item["session_id"] for item in sessions_after_clear["sessions"]], ["default"])

    def test_ui_server_bot_channel_preview_redacts_token(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        request = Request(
            f"{base_url}/api/bot-channels/preview",
            data=b'{"channel":"telegram_ops","text":"hello"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            preview = json.loads(urlopen(request, timeout=5).read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(preview["channel"], "telegram_ops")
        self.assertTrue(preview["dry_run"])

    def test_ui_server_openclaw_preview_endpoint_reports_bad_path(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        request = Request(
            f"{base_url}/api/openclaw/preview",
            data=b'{"config_path":"C:/definitely/missing/openclaw.json"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with self.assertRaises(HTTPError) as context:
                urlopen(request, timeout=5)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertEqual(context.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
