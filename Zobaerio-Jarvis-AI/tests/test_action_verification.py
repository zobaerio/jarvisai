from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import automation


class LocalActionVerificationTests(unittest.TestCase):
    def test_verifies_existing_file_in_allowed_user_folder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "report.md").write_text("# Verified", encoding="utf-8")
            with patch.dict(automation.ROOTS, {"downloads": root}):
                result = automation.verify_local_action("file", "report.md", "Downloads")
        self.assertIn("Verified file exists", result)
        self.assertIn("10 bytes", result)

    def test_verifies_existing_folder_and_does_not_claim_missing_folder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "Project").mkdir()
            with patch.dict(automation.ROOTS, {"documents": root}):
                exists = automation.verify_local_action("folder", "Project", "Documents")
                missing = automation.verify_local_action("folder", "Unknown", "Documents")
        self.assertIn("Verified folder exists", exists)
        self.assertIn("Not verified", missing)

    def test_rejects_paths_outside_allowlisted_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with patch.dict(automation.ROOTS, {"downloads": root}):
                result = automation.verify_local_action("file", "../secret.txt", "Downloads")
        self.assertIn("Verification blocked", result)

    def test_window_verification_is_explicit_about_non_windows(self) -> None:
        if os.name == "nt":
            self.skipTest("This test validates unsupported-platform messaging on CI.")
        result = automation.verify_local_action("window", "Notepad")
        self.assertIn("only on Windows", result)

    def test_unknown_verification_kind_is_rejected(self) -> None:
        result = automation.verify_local_action("process", "notepad.exe")
        self.assertIn("must be window, file, or folder", result)


if __name__ == "__main__":
    unittest.main()
