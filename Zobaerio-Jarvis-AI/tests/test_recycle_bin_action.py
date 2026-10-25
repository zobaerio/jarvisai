from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jarvis import automation


class RecycleBinFileActionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.roots = {
            "desktop": root / "Desktop",
            "documents": root / "Documents",
            "downloads": root / "Downloads",
        }
        for path in self.roots.values():
            path.mkdir(parents=True)
        patcher = patch.dict(automation.ROOTS, self.roots)
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake_trash_module(self, trash):
        module = types.ModuleType("send2trash")
        module.send2trash = trash
        return module

    def test_cancelled_action_preserves_file_and_never_calls_trash(self) -> None:
        target = self.roots["documents"] / "estimate.xlsx"
        target.write_bytes(b"budget")
        trash = Mock()
        with patch("jarvis.automation._is_windows_platform", return_value=True), patch.dict(sys.modules, {"send2trash": self.fake_trash_module(trash)}):
            result = automation.move_file_to_recycle_bin("Documents", "estimate.xlsx", lambda *_: False)
        self.assertIn("Cancelled", result)
        self.assertTrue(target.is_file())
        trash.assert_not_called()

    def test_approved_action_sends_exact_file_to_trash(self) -> None:
        target = self.roots["desktop"] / "old-notes.txt"
        target.write_text("archive", encoding="utf-8")
        approval = Mock(return_value=True)
        trash = Mock()
        with patch("jarvis.automation._is_windows_platform", return_value=True), patch.dict(sys.modules, {"send2trash": self.fake_trash_module(trash)}):
            result = automation.move_file_to_recycle_bin("Desktop", "old-notes.txt", approval)
        self.assertIn("Moved to the Windows Recycle Bin", result)
        approval.assert_called_once()
        self.assertIn(str(target), approval.call_args.args[1])
        self.assertIn("not be permanently deleted", approval.call_args.args[1])
        trash.assert_called_once_with(str(target.resolve()))

    def test_blocks_traversal_and_symbolic_links_before_approval(self) -> None:
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("keep", encoding="utf-8")
        link = self.roots["documents"] / "linked.txt"
        link.symlink_to(outside)
        approval = Mock(return_value=True)
        result = automation.move_file_to_recycle_bin("Documents", "../outside.txt", approval)
        self.assertIn("Recycle Bin operation blocked", result)
        result = automation.move_file_to_recycle_bin("Documents", "linked.txt", approval)
        self.assertIn("Symbolic links are not supported", result)
        approval.assert_not_called()
        self.assertTrue(outside.exists())

    def test_directories_and_missing_files_are_not_recycled(self) -> None:
        (self.roots["downloads"] / "folder").mkdir()
        approval = Mock(return_value=True)
        with patch("jarvis.automation._is_windows_platform", return_value=True):
            result = automation.move_file_to_recycle_bin("Downloads", "folder", approval)
            self.assertIn("not a regular file", result)
            result = automation.move_file_to_recycle_bin("Downloads", "missing.txt", approval)
            self.assertIn("not a regular file", result)
        approval.assert_not_called()

    def test_file_changed_during_confirmation_is_not_recycled(self) -> None:
        target = self.roots["documents"] / "report.txt"
        target.write_text("version one", encoding="utf-8")
        trash = Mock()
        def change_file(_title, _detail):
            target.write_text("version two with different size", encoding="utf-8")
            return True
        with patch("jarvis.automation._is_windows_platform", return_value=True), patch.dict(sys.modules, {"send2trash": self.fake_trash_module(trash)}):
            result = automation.move_file_to_recycle_bin("Documents", "report.txt", change_file)
        self.assertIn("changed after confirmation", result)
        trash.assert_not_called()

    def test_send2trash_failure_is_not_reported_as_success(self) -> None:
        target = self.roots["documents"] / "report.txt"
        target.write_text("keep", encoding="utf-8")
        trash = Mock(side_effect=OSError("Recycle Bin unavailable"))
        with patch("jarvis.automation._is_windows_platform", return_value=True), patch.dict(sys.modules, {"send2trash": self.fake_trash_module(trash)}):
            result = automation.move_file_to_recycle_bin("Documents", "report.txt", lambda *_: True)
        self.assertIn("Could not move the file to the Recycle Bin", result)
        self.assertNotIn("Moved to the Windows Recycle Bin", result)
        self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main()
