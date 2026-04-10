from __future__ import annotations

from copy import deepcopy
import unittest

from channels.bot_config import load_bot_channel_config
from channels.bot_gateway import EXAMPLE_CONFIG, build_dispatch, list_channels, send_or_preview


class BotChannelTests(unittest.TestCase):
    def test_example_config_lists_mainstream_channels(self) -> None:
        config = load_bot_channel_config(EXAMPLE_CONFIG)

        channels = list_channels(config)

        self.assertEqual(
            [channel["kind"] for channel in channels],
            ["feishu_webhook", "generic_webhook", "qq_official", "telegram", "whatsapp_cloud"],
        )

    def test_telegram_dispatch_redacts_token(self) -> None:
        config = load_bot_channel_config(EXAMPLE_CONFIG)

        dispatch = build_dispatch(
            config,
            channel_name="telegram_ops",
            text="hello",
            env={"TELEGRAM_BOT_TOKEN": "real-token", "TELEGRAM_CHAT_ID": "chat-1"},
        ).as_redacted_dict()

        self.assertIn("***", dispatch["endpoint"])
        self.assertNotIn("real-token", str(dispatch))
        self.assertEqual(dispatch["body"]["chat_id"], "chat-1")

    def test_whatsapp_dispatch_uses_cloud_api_shape(self) -> None:
        config = load_bot_channel_config(EXAMPLE_CONFIG)

        dispatch = build_dispatch(
            config,
            channel_name="whatsapp_ops",
            text="hello",
            env={
                "WHATSAPP_ACCESS_TOKEN": "token",
                "WHATSAPP_TO": "15551234567",
                "WHATSAPP_PHONE_NUMBER_ID": "phone-id",
                "WHATSAPP_GRAPH_API_VERSION": "v99.0",
            },
        ).as_redacted_dict()

        self.assertEqual(dispatch["body"]["messaging_product"], "whatsapp")
        self.assertEqual(dispatch["body"]["text"]["body"], "hello")
        self.assertEqual(dispatch["endpoint"], "https://graph.facebook.com/v99.0/phone-id/messages")
        self.assertNotIn("token", str(dispatch))

    def test_live_dispatch_requires_configured_environment(self) -> None:
        config = deepcopy(load_bot_channel_config(EXAMPLE_CONFIG))
        config["mode"] = "live"

        with self.assertRaisesRegex(ValueError, "environment variables"):
            send_or_preview(config, channel_name="telegram_ops", text="hello", env={}, live=True)

    def test_webhook_dispatch_keeps_raw_endpoint_but_redacts_preview(self) -> None:
        config = load_bot_channel_config(EXAMPLE_CONFIG)
        webhook_url = "https://example.test/hook/secret-token?token=another-secret"

        dispatch = build_dispatch(
            config,
            channel_name="feishu_ops",
            text="hello",
            env={"FEISHU_BOT_WEBHOOK_URL": webhook_url},
        )
        rendered = dispatch.as_redacted_dict()

        self.assertEqual(dispatch.endpoint, webhook_url)
        self.assertEqual(rendered["endpoint"], "https://example.test/?redacted=1")
        self.assertNotIn("secret-token", str(rendered))
        self.assertNotIn("another-secret", str(rendered))

    def test_feishu_signed_webhook_is_not_live_until_signing_exists(self) -> None:
        config = deepcopy(load_bot_channel_config(EXAMPLE_CONFIG))
        config["mode"] = "live"
        config["channels"]["feishu_ops"]["enabled"] = True

        with self.assertRaisesRegex(NotImplementedError, "Signed Feishu"):
            send_or_preview(
                config,
                channel_name="feishu_ops",
                text="hello",
                env={"FEISHU_BOT_WEBHOOK_URL": "https://example.test/hook", "FEISHU_BOT_SECRET": "secret"},
                live=True,
            )

    def test_qq_dispatch_is_dry_run_only_until_dedicated_adapter_exists(self) -> None:
        config = load_bot_channel_config(EXAMPLE_CONFIG)

        dispatch = send_or_preview(config, channel_name="qq_ops", text="hello")

        self.assertTrue(dispatch["dry_run"])
        self.assertFalse(dispatch["live_supported"])
        self.assertEqual(dispatch["method"], "SDK_OR_GATEWAY")


if __name__ == "__main__":
    unittest.main()
