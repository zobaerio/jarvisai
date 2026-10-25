from __future__ import annotations

import os
import unittest
from unittest.mock import Mock

from jarvis import automation


class ForegroundActionPolicyTests(unittest.TestCase):
    def test_normalizes_allowlisted_shortcuts(self) -> None:
        self.assertEqual(automation.normalize_allowed_shortcut("ctrl+s"), ("ctrl", "s"))
        self.assertEqual(automation.normalize_allowed_shortcut("SHIFT+TAB"), ("shift", "tab"))
        self.assertEqual(automation.normalize_allowed_shortcut("esc"), ("esc",))

    def test_blocks_submission_and_system_shortcuts(self) -> None:
        for shortcut in ("ENTER", "ALT+F4", "WIN+R", "CTRL+ALT+DELETE", "CTRL+L"):
            with self.subTest(shortcut=shortcut), self.assertRaises(ValueError):
                automation.normalize_allowed_shortcut(shortcut)

    def test_foreground_action_does_not_execute_or_approve_on_non_windows(self) -> None:
        if os.name == "nt":
            self.skipTest("This assertion is for non-Windows CI hosts.")
        approve = Mock(return_value=True)
        self.assertIn("only on Windows", automation.paste_text_into_window("hello", "Notepad", approve))
        self.assertIn("only on Windows", automation.press_allowed_shortcut("CTRL+S", "Notepad", approve))
        approve.assert_not_called()

    def test_list_open_windows_does_not_claim_to_read_contents(self) -> None:
        result = automation.list_open_windows()
        if os.name != "nt":
            self.assertIn("only on Windows", result)
        else:
            self.assertTrue(
                "Visible window titles" in result or "No titled application windows" in result,
                result,
            )


if __name__ == "__main__":
    unittest.main()
