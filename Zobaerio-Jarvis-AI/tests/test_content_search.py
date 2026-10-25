from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jarvis import automation


class LocalContentSearchTests(unittest.TestCase):
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

    def test_search_requires_approval_and_returns_only_matching_lines(self) -> None:
        target = self.roots["documents"] / "estimate.md"
        target.write_text("# Estimate\nConcrete volume = 12 m3\nPrivate unrelated line", encoding="utf-8")
        denied = Mock(return_value=False)
        result = automation.search_file_contents("concrete", "Documents", denied)
        self.assertIn("Cancelled", result)
        denied.assert_called_once()
        self.assertIn("may be sent to the configured AI provider", denied.call_args.args[1])

        approved = Mock(return_value=True)
        result = automation.search_file_contents("concrete", "Documents", approved)
        self.assertIn("Found 1 matching line", result)
        self.assertIn("Concrete volume = 12 m3", result)
        self.assertNotIn("Private unrelated line", result)

    def test_search_all_folders_and_ignores_binary_extensions(self) -> None:
        (self.roots["desktop"] / "note.txt").write_text("rebar count 12", encoding="utf-8")
        (self.roots["downloads"] / "design.png").write_bytes(b"rebar count 12")
        result = automation.search_file_contents("rebar", "All", lambda *_: True)
        self.assertIn("rebar count 12", result)
        self.assertIn("Desktop, Documents, Downloads", result)
        self.assertNotIn("design.png", result)

    def test_search_skips_oversized_files_and_reports_limit(self) -> None:
        (self.roots["documents"] / "big.txt").write_text("needle " * 100, encoding="utf-8")
        with patch("jarvis.automation.MAX_CONTENT_SEARCH_FILE_BYTES", 32):
            result = automation.search_file_contents("needle", "Documents", lambda *_: True)
        self.assertIn("No matching lines found", result)
        self.assertIn("skipped 1 large/binary file", result)

    def test_search_skips_null_byte_text_files(self) -> None:
        (self.roots["documents"] / "binary.txt").write_bytes(b"needle\x00payload")
        result = automation.search_file_contents("needle", "Documents", lambda *_: True)
        self.assertIn("No matching lines found", result)
        self.assertIn("skipped 1 large/binary file", result)

    def test_search_skips_symlink_files(self) -> None:
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("secretneedle", encoding="utf-8")
        link = self.roots["documents"] / "linked.txt"
        link.symlink_to(outside)
        result = automation.search_file_contents("secretneedle", "Documents", lambda *_: True)
        self.assertIn("No matching lines found", result)

    def test_search_refuses_too_short_query_without_approval(self) -> None:
        approval = Mock(return_value=True)
        result = automation.search_file_contents("x", "All", approval)
        self.assertIn("at least 2 characters", result)
        approval.assert_not_called()


if __name__ == "__main__":
    unittest.main()
