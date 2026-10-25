from __future__ import annotations

import unittest
from unittest.mock import patch

from jarvis import automation


class WhatsAppMessageDraftTests(unittest.TestCase):
    def test_valid_phone_opens_prefilled_draft_without_sending(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            result = automation.prepare_whatsapp_message("+880 1712-345678", "Hello there!\nHow are you?")
        open_url.assert_called_once_with(
            "https://web.whatsapp.com/send?phone=8801712345678&text=Hello%20there%21%0AHow%20are%20you%3F"
        )
        self.assertIn("Nothing was sent", result)
        self.assertIn("click Send yourself", result)

    def test_invalid_phone_does_not_open_browser(self) -> None:
        for phone in ("", "abc12345", "1234567", "1234567890123456", "+88012/345678"):
            with self.subTest(phone=phone), patch("jarvis.automation.webbrowser.open") as open_url:
                result = automation.prepare_whatsapp_message(phone, "Hello")
                open_url.assert_not_called()
                self.assertIn("blocked", result)

    def test_empty_message_does_not_open_browser(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            result = automation.prepare_whatsapp_message("+8801712345678", "  ")
        open_url.assert_not_called()
        self.assertIn("empty", result)

    def test_oversized_message_does_not_open_browser(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            result = automation.prepare_whatsapp_message("+8801712345678", "x" * 4001)
        open_url.assert_not_called()
        self.assertIn("4,000", result)

    def test_message_special_characters_are_url_encoded(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            automation.prepare_whatsapp_message("+8801712345678", "Hi & bye / now")
        self.assertEqual(open_url.call_count, 1)
        self.assertIn("text=Hi%20%26%20bye%20%2F%20now", open_url.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
