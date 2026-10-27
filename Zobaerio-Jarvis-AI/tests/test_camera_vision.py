from __future__ import annotations

import json
import sys
import unittest
from unittest.mock import Mock, patch

import numpy as np

from jarvis.camera_vision import analyze_camera


class CameraVisionTests(unittest.TestCase):
    def test_declined_consent_never_opens_camera_or_sends_image(self) -> None:
        fake_cv2 = Mock()
        with patch.dict(sys.modules, {"cv2": fake_cv2}), patch("jarvis.camera_vision.requests.post") as post:
            result = analyze_camera(
                {"api_base_url": "http://localhost:11434/v1", "model": "vision-model"},
                approval=lambda *_: False,
                prompt="Describe the camera view",
            )
        self.assertIn("cancelled", result.casefold())
        fake_cv2.VideoCapture.assert_not_called()
        post.assert_not_called()

    def test_multiline_prompt_is_allowed_when_consent_is_declined(self) -> None:
        result = analyze_camera(
            {"api_base_url": "http://localhost:11434/v1", "model": "vision-model"},
            approval=lambda *_: False,
            prompt="Describe this scene.\\nMention visible objects.",
        )
        self.assertIn("cancelled", result.casefold())

    def test_approved_camera_frame_is_sent_and_camera_is_released(self) -> None:
        fake_cv2 = Mock()
        capture = Mock()
        capture.isOpened.return_value = True
        capture.read.return_value = (True, np.zeros((48, 64, 3), dtype=np.uint8))
        fake_cv2.VideoCapture.return_value = capture
        fake_cv2.CAP_DSHOW = 700
        fake_cv2.CAP_PROP_FRAME_WIDTH = 3
        fake_cv2.CAP_PROP_FRAME_HEIGHT = 4
        fake_cv2.COLOR_BGR2RGB = 5
        fake_cv2.cvtColor.side_effect = lambda frame, _code: frame[:, :, ::-1].copy()
        response = Mock()
        response.status_code = 200
        response.iter_content.return_value = [json.dumps({"choices": [{"message": {"content": [
            {"type": "text", "text": "A room is visible."},
            {"type": "text", "text": "Second line."},
        ]}}]}).encode()]
        with patch.dict(sys.modules, {"cv2": fake_cv2}), patch(
            "jarvis.camera_vision.get_api_key", return_value="test-key"
        ), patch("jarvis.camera_vision.requests.post", return_value=response) as post:
            result = analyze_camera(
                {"api_base_url": "https://example.invalid/v1", "model": "vision-model"},
                approval=lambda *_: True,
                prompt="Describe the camera view",
            )
        self.assertEqual(result, "A room is visible.\\nSecond line.")
        capture.read.assert_called_once_with()
        capture.release.assert_called_once_with()
        user_content = post.call_args.kwargs["json"]["messages"][1]["content"]
        self.assertEqual(user_content[0]["text"], "Describe the camera view")
        self.assertTrue(user_content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))

    def test_camera_index_rejects_boolean_and_out_of_range_values(self) -> None:
        for index in (True, -1, 4, "0"):
            with self.subTest(index=index):
                result = analyze_camera(
                    {"api_base_url": "http://localhost:11434/v1", "model": "vision-model"},
                    approval=lambda *_: True,
                    camera_index=index,
                )
                self.assertIn("camera index", result.casefold())


if __name__ == "__main__":
    unittest.main()
