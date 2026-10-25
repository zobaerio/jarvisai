from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib.parse import unquote

from jarvis import automation


class EmailDraftTests(unittest.TestCase):
    def test_valid_email_opens_prefilled_draft_without_sending(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            result = automation.prepare_email_draft(
                "engineer@example.com", "Site update & plan", "Hello,\nPlease review the drawing."
            )
        open_url.assert_called_once()
        url = open_url.call_args.args[0]
        self.assertTrue(url.startswith("mailto:engineer@example.com?"))
        self.assertIn("subject=Site%20update%20%26%20plan", url)
        self.assertIn("body=Hello%2C%0APlease%20review%20the%20drawing.", url)
        self.assertIn("Nothing was sent", result)
        self.assertIn("send it yourself", result)

    def test_invalid_recipient_does_not_open_app(self) -> None:
        for address in ("", "not-an-email", "name <user@example.com>", "user@localhost", "a@b.c", "user@example.com\r\nBcc:x@y.com"):
            with self.subTest(address=address), patch("jarvis.automation.webbrowser.open") as open_url:
                result = automation.prepare_email_draft(address, "Subject", "Body")
                open_url.assert_not_called()
                self.assertIn("blocked", result)

    def test_empty_body_does_not_open_app(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            result = automation.prepare_email_draft("user@example.com", "Subject", "  ")
        open_url.assert_not_called()
        self.assertIn("empty", result)

    def test_subject_and_body_limits_are_enforced(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            subject_result = automation.prepare_email_draft("user@example.com", "x" * 201, "Body")
            body_result = automation.prepare_email_draft("user@example.com", "", "x" * 5001)
        open_url.assert_not_called()
        self.assertIn("200", subject_result)
        self.assertIn("5,000", body_result)

    def test_header_control_characters_are_rejected(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            result = automation.prepare_email_draft("user@example.com", "Hi\r\nBcc:evil@example.com", "Body")
        open_url.assert_not_called()
        self.assertIn("control characters", result)


if __name__ == "__main__":
    unittest.main()
