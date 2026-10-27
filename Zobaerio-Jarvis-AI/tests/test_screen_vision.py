from __future__ import annotations

import sys
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from jarvis.vision import analyze_screen


class ScreenVisionTests(unittest.TestCase):
    def test_declined_consent_captures_nothing_and_sends_nothing(self) -> None:
        fake_pyautogui = Mock()
        with patch.dict(sys.modules, {"pyautogui": fake_pyautogui}), patch(
            "jarvis.vision.requests.post"
        ) as post:
            result = analyze_screen(
                {"api_base_url": "http://localhost:11434/v1", "model": "vision-model"},
                approval=lambda *_: False,
                prompt="What error is visible?",
            )
        self.assertIn("cancelled", result.casefold())
        fake_pyautogui.screenshot.assert_not_called()
        post.assert_not_called()

    def test_approved_screenshot_is_sent_as_in_memory_data_url(self) -> None:
        fake_pyautogui = Mock()
        fake_pyautogui.screenshot.return_value = Image.new("RGB", (320, 200), "white")
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"choices": [{"message": {"content": "The screen is mostly blank."}}]}
        approvals: list[tuple[str, str]] = []

        def approve(title: str, message: str) -> bool:
            approvals.append((title, message))
            return True

        with patch.dict(sys.modules, {"pyautogui": fake_pyautogui}), patch(
            "jarvis.vision.get_api_key", return_value="test-key"
        ), patch("jarvis.vision.requests.post", return_value=response) as post:
            result = analyze_screen(
                {"api_base_url": "https://example.invalid/v1", "model": "vision-model"},
                approval=approve,
                prompt="Describe the screen",
            )

        self.assertEqual(result, "The screen is mostly blank.")
        self.assertEqual(len(approvals), 1)
        fake_pyautogui.screenshot.assert_called_once_with()
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        user_content = kwargs["json"]["messages"][1]["content"]
        self.assertEqual(user_content[0]["text"], "Describe the screen")
        self.assertTrue(user_content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
        self.assertNotIn("tools", kwargs["json"])

    def test_non_vision_endpoint_error_is_actionable_and_redacted(self) -> None:
        response = Mock()
        response.status_code = 400
        response.text = "private provider response"
        with patch("jarvis.vision.get_api_key", return_value="test-key"), patch(
            "jarvis.vision.requests.post", return_value=response
        ), patch("pyautogui.screenshot", side_effect=AssertionError("capture should not be called")):
            # A declined consent must stop before screenshot capture regardless of endpoint support.
            result = analyze_screen(
                {"api_base_url": "https://example.invalid/v1", "model": "text-only-model"},
                approval=lambda *_: False,
                prompt="Read the visible text",
            )
        self.assertIn("cancelled", result.casefold())
        self.assertNotIn("private provider response", result)


if __name__ == "__main__":
    unittest.main()
