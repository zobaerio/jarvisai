from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jarvis import automation


class ApprovedOpenFileTests(unittest.TestCase):
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

    def test_open_requires_approval_and_rechecks_selected_file(self) -> None:
        target = self.roots["documents"] / "plan.pdf"
        target.write_bytes(b"%PDF sample")
        denied = Mock(return_value=False)
        with patch("jarvis.automation._is_windows_platform", return_value=True), patch(
            "jarvis.automation._launch_file_with_default_app"
        ) as launch:
            result = automation.open_file("Documents", "plan.pdf", denied)
        self.assertIn("Cancelled", result)
        denied.assert_called_once()
        self.assertIn(str(target), denied.call_args.args[1])
        launch.assert_not_called()

        approved = Mock(return_value=True)
        with patch("jarvis.automation._is_windows_platform", return_value=True), patch(
            "jarvis.automation._launch_file_with_default_app"
        ) as launch:
            result = automation.open_file("Documents", "plan.pdf", approved)
        self.assertIn("Asked Windows to open", result)
        launch.assert_called_once_with(target.resolve())

    def test_blocks_executable_and_script_extensions(self) -> None:
        for filename in ("payload.exe", "script.py", "run.bat", "shell.ps1"):
            with self.subTest(filename=filename):
                (self.roots["downloads"] / filename).write_text("do not launch", encoding="utf-8")
                approval = Mock(return_value=True)
                result = automation.open_file("Downloads", filename, approval)
                self.assertIn("Executables and scripts are blocked", result)
                approval.assert_not_called()

    def test_blocks_path_traversal_and_symbolic_link(self) -> None:
        outside = Path(self.temp.name) / "outside.pdf"
        outside.write_bytes(b"%PDF sample")
        traversal = automation.open_file("Documents", "../outside.pdf", lambda *_: True)
        self.assertIn("File open blocked", traversal)
        link = self.roots["documents"] / "linked.pdf"
        link.symlink_to(outside)
        result = automation.open_file("Documents", "linked.pdf", lambda *_: True)
        self.assertIn("Symbolic links are not supported", result)

    def test_non_windows_runtime_does_not_ask_for_approval(self) -> None:
        if automation._is_windows_platform():
            self.skipTest("This test covers non-Windows CI.")
        (self.roots["documents"] / "plan.pdf").write_bytes(b"%PDF sample")
        approval = Mock(return_value=True)
        result = automation.open_file("Documents", "plan.pdf", approval)
        self.assertIn("supported only on Windows", result)
        approval.assert_not_called()


if __name__ == "__main__":
    unittest.main()
