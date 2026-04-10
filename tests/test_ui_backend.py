from __future__ import annotations

import copy
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request
from urllib.request import urlopen

from model.provider_config import load_model_config
from ui_backend import EXAMPLE_CONFIG, make_handler, route_preview


class UiBackendTests(unittest.TestCase):
    def test_route_preview_redacts_secret_values(self) -> None:
        config = load_model_config(EXAMPLE_CONFIG)

        routes = route_preview(config)

        self.assertEqual([route["role"] for route in routes], ["planner", "classifier", "summarizer", "verifier"])
        self.assertTrue(all("api_key_configured" in route for route in routes))
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
            index = urlopen(f"{base_url}/", timeout=5).read().decode("utf-8")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(health["status"], "ok")
        self.assertIn("config", config)
        self.assertIn("Device Agent Console", index)

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
