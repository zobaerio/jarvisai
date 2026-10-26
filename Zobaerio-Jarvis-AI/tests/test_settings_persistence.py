from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import settings


class DurableSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.primary = self.root / "settings.json"
        self.backup = self.root / "settings.json.bak"
        self.app_dir_patch = patch.object(settings, "APP_DIR", self.root)
        self.file_patch = patch.object(settings, "SETTINGS_FILE", self.primary)
        self.app_dir_patch.start()
        self.file_patch.start()
        self.addCleanup(self.file_patch.stop)
        self.addCleanup(self.app_dir_patch.stop)

    def test_save_and_load_round_trip_uses_only_allowlisted_keys(self) -> None:
        settings.save_settings({
            "api_base_url": "https://api.example.com/v1",
            "model": "sample-model",
            "unknown_private_field": "must not be written",
        })
        loaded = settings.load_settings()
        self.assertEqual(loaded["api_base_url"], "https://api.example.com/v1")
        self.assertEqual(loaded["model"], "sample-model")
        self.assertEqual(loaded["voice"], settings.DEFAULTS["voice"])
        stored = json.loads(self.primary.read_text(encoding="utf-8"))
        self.assertNotIn("unknown_private_field", stored)
        self.assertTrue(self.backup.is_file())

    def test_corrupt_primary_recovers_from_valid_backup(self) -> None:
        backup_data = {**settings.DEFAULTS, "model": "recovered-model"}
        self.backup.write_text(json.dumps(backup_data), encoding="utf-8")
        self.primary.write_text("{truncated settings", encoding="utf-8")
        loaded = settings.load_settings()
        self.assertEqual(loaded["model"], "recovered-model")
        self.assertEqual(loaded["api_base_url"], settings.DEFAULTS["api_base_url"])

    def test_invalid_primary_and_backup_fall_back_to_defaults(self) -> None:
        self.primary.write_text("not json", encoding="utf-8")
        self.backup.write_text("[]", encoding="utf-8")
        self.assertEqual(settings.load_settings(), settings.DEFAULTS)

    def test_failed_primary_fsync_preserves_existing_file_and_cleans_temp(self) -> None:
        settings.save_settings({**settings.DEFAULTS, "model": "last-known-good"})
        previous_primary = self.primary.read_bytes()
        previous_backup = self.backup.read_bytes()
        with patch("jarvis.settings.os.fsync", side_effect=OSError("simulated write failure")):
            with self.assertRaises(OSError):
                settings.save_settings({**settings.DEFAULTS, "model": "must-not-commit"})
        self.assertEqual(self.primary.read_bytes(), previous_primary)
        self.assertEqual(self.backup.read_bytes(), previous_backup)
        self.assertEqual(settings.load_settings()["model"], "last-known-good")
        self.assertFalse(any(path.name.endswith(".tmp") for path in self.root.iterdir()))

    def test_backup_failure_does_not_fail_committed_primary(self) -> None:
        original = settings._atomic_write_text
        calls = {"count": 0}
        def fail_backup(destination: Path, payload: str) -> None:
            calls["count"] += 1
            if calls["count"] == 2:
                raise OSError("simulated backup failure")
            original(destination, payload)
        with patch("jarvis.settings._atomic_write_text", side_effect=fail_backup):
            settings.save_settings({**settings.DEFAULTS, "model": "primary-committed"})
        self.assertEqual(settings.load_settings()["model"], "primary-committed")

    def test_concurrent_saves_do_not_produce_partial_json(self) -> None:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [
                executor.submit(settings.save_settings, {**settings.DEFAULTS, "model": f"model-{index}"})
                for index in range(24)
            ]
            [future.result() for future in futures]
        primary = json.loads(self.primary.read_text(encoding="utf-8"))
        backup = json.loads(self.backup.read_text(encoding="utf-8"))
        self.assertIn(primary["model"], {f"model-{index}" for index in range(24)})
        self.assertEqual(primary["model"], backup["model"])


    def test_floating_hud_preferences_survive_save_and_load(self) -> None:
        preferences = {
            "floating_hud_x": 310,
            "floating_hud_y": 180,
            "floating_hud_topmost": False,
            "floating_hud_mini": True,
            "floating_hud_width": 240,
            "floating_hud_height": 280,
            "floating_hud_opacity": 0.85,
        }
        settings.save_settings({**settings.DEFAULTS, **preferences})
        loaded = settings.load_settings()
        for key, value in preferences.items():
            self.assertEqual(loaded[key], value, key)



if __name__ == "__main__":
    unittest.main()
