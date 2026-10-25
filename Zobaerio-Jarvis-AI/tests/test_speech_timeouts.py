from __future__ import annotations

import unittest

from jarvis.speech import _playback_timeout_seconds


class SpeechTimeoutTests(unittest.TestCase):
    def test_playback_timeout_has_a_safe_minimum(self) -> None:
        self.assertEqual(_playback_timeout_seconds(0), 15.0)
        self.assertEqual(_playback_timeout_seconds(100), 15.0)

    def test_longer_responses_get_more_playback_time(self) -> None:
        self.assertGreater(_playback_timeout_seconds(1000), _playback_timeout_seconds(100))

    def test_playback_timeout_is_bounded(self) -> None:
        self.assertEqual(_playback_timeout_seconds(10_000_000), 180.0)

    def test_negative_length_does_not_reduce_timeout(self) -> None:
        self.assertEqual(_playback_timeout_seconds(-100), 15.0)


if __name__ == "__main__":
    unittest.main()
