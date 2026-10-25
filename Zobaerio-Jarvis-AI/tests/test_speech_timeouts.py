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

    def test_synthesis_failure_removes_temporary_audio_file(self) -> None:
        import asyncio
        import sys
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, patch

        created_paths: list[Path] = []
        original_named_temp_file = tempfile.NamedTemporaryFile

        def tracked_temp_file(*args, **kwargs):
            handle = original_named_temp_file(*args, **kwargs)
            created_paths.append(Path(handle.name))
            return handle

        communicate = SimpleNamespace(save=AsyncMock(side_effect=RuntimeError("provider failure")))
        edge_tts = SimpleNamespace(Communicate=lambda **_kwargs: communicate)
        pygame = SimpleNamespace(mixer=SimpleNamespace(init=lambda: None, music=SimpleNamespace()))
        engine = __import__("jarvis.speech", fromlist=["SpeechEngine"]).SpeechEngine()

        with patch.dict(sys.modules, {"edge_tts": edge_tts, "pygame": pygame}), patch(
            "jarvis.speech.tempfile.NamedTemporaryFile", side_effect=tracked_temp_file
        ):
            with self.assertRaisesRegex(RuntimeError, "provider failure"):
                asyncio.run(engine._edge_speak("hello", "test-voice"))

        self.assertEqual(len(created_paths), 1)
        self.assertFalse(created_paths[0].exists())

    def test_playback_failure_stops_and_unloads_audio_and_removes_file(self) -> None:
        import asyncio
        import sys
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, Mock, patch

        created_paths: list[Path] = []
        original_named_temp_file = tempfile.NamedTemporaryFile

        def tracked_temp_file(*args, **kwargs):
            handle = original_named_temp_file(*args, **kwargs)
            created_paths.append(Path(handle.name))
            return handle

        music = SimpleNamespace(
            load=Mock(),
            play=Mock(side_effect=RuntimeError("audio device failed")),
            stop=Mock(),
            unload=Mock(),
        )
        pygame = SimpleNamespace(mixer=SimpleNamespace(init=Mock(), music=music))
        edge_tts = SimpleNamespace(Communicate=lambda **_kwargs: SimpleNamespace(save=AsyncMock()))
        engine = __import__("jarvis.speech", fromlist=["SpeechEngine"]).SpeechEngine()

        with patch.dict(sys.modules, {"edge_tts": edge_tts, "pygame": pygame}), patch(
            "jarvis.speech.tempfile.NamedTemporaryFile", side_effect=tracked_temp_file
        ):
            with self.assertRaisesRegex(RuntimeError, "audio device failed"):
                asyncio.run(engine._edge_speak("hello", "test-voice"))

        music.stop.assert_called_once()
        music.unload.assert_called_once()
        self.assertEqual(len(created_paths), 1)
        self.assertFalse(created_paths[0].exists())


if __name__ == "__main__":
    unittest.main()
