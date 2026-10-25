from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jarvis import automation


class SafeDuplicateFinderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.roots = {
            "desktop": root / "Desktop",
            "documents": root / "Documents",
            "downloads": root / "Downloads",
        }
        for folder in self.roots.values():
            folder.mkdir(parents=True)
        patcher = patch.dict(automation.ROOTS, self.roots)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_finds_identical_content_and_never_returns_file_contents(self) -> None:
        first = self.roots["documents"] / "estimate.txt"
        second = self.roots["documents"] / "estimate-copy.txt"
        first.write_text("private construction estimate 12345", encoding="utf-8")
        second.write_text("private construction estimate 12345", encoding="utf-8")
        # Same-size content but different bytes must not be called a duplicate.
        distinct = self.roots["documents"] / "secured.txt"
        distinct.write_text("secured construction estimate 12345", encoding="utf-8")
        before = {p.name: p.read_bytes() for p in (first, second, distinct)}
        approval = Mock(return_value=True)

        result = automation.find_duplicate_files("Documents", approval)

        self.assertIn("Found 1 duplicate group", result)
        self.assertIn("estimate.txt", result)
        self.assertIn("estimate-copy.txt", result)
        self.assertIn("SHA-256", result)
        self.assertNotIn("private construction estimate", result)
        self.assertNotIn("secured.txt", result)
        self.assertIn("may be sent to the configured AI provider", approval.call_args.args[1])
        self.assertIn("\n\n", approval.call_args.args[1])
        self.assertEqual({p.name: p.read_bytes() for p in (first, second, distinct)}, before)

    def test_declined_approval_does_not_hash_any_file(self) -> None:
        (self.roots["desktop"] / "a.txt").write_text("same", encoding="utf-8")
        with patch("jarvis.automation._sha256_if_unchanged") as hash_file:
            result = automation.find_duplicate_files("Desktop", lambda *_: False)
        self.assertIn("Cancelled", result)
        hash_file.assert_not_called()

    def test_all_scope_includes_every_approved_root(self) -> None:
        (self.roots["desktop"] / "a.bin").write_bytes(b"same")
        (self.roots["documents"] / "b.bin").write_bytes(b"same")
        (self.roots["downloads"] / "c.bin").write_bytes(b"same")
        result = automation.find_duplicate_files("All", lambda *_: True)
        self.assertIn("Desktop, Documents, Downloads", result)
        self.assertIn("3 identical files", result)

    def test_skips_hidden_generated_directories_and_symbolic_links(self) -> None:
        root = self.roots["documents"]
        (root / "visible.txt").write_text("same", encoding="utf-8")
        hidden = root / ".secret"
        hidden.mkdir()
        (hidden / "secret.txt").write_text("same", encoding="utf-8")
        generated = root / "node_modules"
        generated.mkdir()
        (generated / "generated.txt").write_text("same", encoding="utf-8")
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("same", encoding="utf-8")
        (root / "linked.txt").symlink_to(outside)

        result = automation.find_duplicate_files("Documents", lambda *_: True)

        self.assertIn("No identical-file groups", result)
        self.assertNotIn("secret.txt", result)
        self.assertNotIn("generated.txt", result)
        self.assertNotIn("linked.txt", result)

    def test_respects_scan_entry_and_hash_byte_budgets(self) -> None:
        root = self.roots["downloads"]
        (root / "a.txt").write_bytes(b"same")
        (root / "b.txt").write_bytes(b"same")
        with patch("jarvis.automation.MAX_DUPLICATE_SCAN_FILES", 1):
            result = automation.find_duplicate_files("Downloads", lambda *_: True)
        self.assertIn("stopped at the 1-entry scan limit", result)
        with patch("jarvis.automation.MAX_DUPLICATE_HASH_BYTES", 1):
            result = automation.find_duplicate_files("Downloads", lambda *_: True)
        self.assertIn("hash budget", result)

    def test_skips_files_over_single_file_limit(self) -> None:
        root = self.roots["documents"]
        (root / "large-a.txt").write_bytes(b"12345")
        (root / "large-b.txt").write_bytes(b"12345")
        with patch("jarvis.automation.MAX_DUPLICATE_SINGLE_FILE_BYTES", 4):
            result = automation.find_duplicate_files("Documents", lambda *_: True)
        self.assertIn("skipped 2 file(s) above", result)
        self.assertIn("No identical-file groups", result)

    def test_file_mutation_during_hash_is_not_reported_as_duplicate(self) -> None:
        target = self.roots["documents"] / "mutable.txt"
        target.write_bytes(b"original bytes")
        metadata = target.stat()
        with patch("jarvis.automation.hashlib.sha256") as make_hash:
            make_hash.return_value.update.side_effect = lambda _data: target.write_bytes(b"changed")
            result = automation._sha256_if_unchanged(target, metadata)
        self.assertIsNone(result)

    def test_rejects_unknown_scope_before_asking_for_approval(self) -> None:
        approval = Mock(return_value=True)
        result = automation.find_duplicate_files("unknown location", approval)
        self.assertIn("Location must be", result)
        approval.assert_not_called()


if __name__ == "__main__":
    unittest.main()
