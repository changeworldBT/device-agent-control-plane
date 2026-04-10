from __future__ import annotations

import unittest

from cli_welcome import render_welcome


class CliWelcomeTests(unittest.TestCase):
    def test_welcome_renders_golden_dragon_banner(self) -> None:
        rendered = render_welcome(color=False)

        self.assertIn("/0  0  \\__", rendered)
        self.assertIn("DEVICE AGENT CONTROL PLANE", rendered)
        self.assertIn("golden dragon console", rendered)
        self.assertNotIn("\x1b[", rendered)

    def test_welcome_can_render_with_ansi_gold(self) -> None:
        rendered = render_welcome(color=True)

        self.assertIn("\x1b[38;5;220m", rendered)
        self.assertIn("DEVICE AGENT CONTROL PLANE", rendered)


if __name__ == "__main__":
    unittest.main()
