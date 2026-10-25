from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from jarvis import automation


class SafeZipArchiveTests(unittest.TestCase):
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

    def test_creates_valid_zip_and_keeps_source_files_unchanged(self) -> None:
        first = self.roots["documents"] / "plan.txt"
        second = self.roots["documents"] / "quantities.csv"
        first.write_text("floor plan notes", encoding="utf-8")
        second.write_text("item,qty\nConcrete,12", encoding="utf-8")
        before = (first.read_bytes(), second.read_bytes())
        approval = Mock(return_value=True)

        result = automation.create_zip_archive(
            "Documents", ["plan.txt", "quantities.csv"], "project.zip", approval
        )
        archive_path = self.roots["documents"] / "project.zip"
        self.assertIn("Created ZIP archive", result)
        approval.assert_called_once()
        self.assertIn(str(archive_path), approval.call_args.args[1])
        self.assertIn("plan.txt", approval.call_args.args[1])
        self.assertIn("quantities.csv", approval.call_args.args[1])
        with zipfile.ZipFile(archive_path, "r") as archive:
            self.assertEqual(archive.namelist(), ["plan.txt", "quantities.csv"])
            self.assertEqual(archive.read("plan.txt"), b"floor plan notes")
            self.assertEqual(archive.read("quantities.csv"), b"item,qty\nConcrete,12")
        self.assertEqual(first.read_bytes(), before[0])
        self.assertEqual(second.read_bytes(), before[1])

    def test_cancel_does_not_create_archive(self) -> None:
        source = self.roots["desktop"] / "notes.txt"
        source.write_text("keep", encoding="utf-8")
        result = automation.create_zip_archive("Desktop", ["notes.txt"], "notes.zip", lambda *_: False)
        self.assertIn("Cancelled", result)
        self.assertFalse((self.roots["desktop"] / "notes.zip").exists())
        self.assertEqual(source.read_text(encoding="utf-8"), "keep")

    def test_existing_destination_is_never_overwritten(self) -> None:
        source = self.roots["desktop"] / "notes.txt"
        destination = self.roots["desktop"] / "notes.zip"
        source.write_text("new contents", encoding="utf-8")
        destination.write_bytes(b"keep existing archive")
        approval = Mock(return_value=True)
        result = automation.create_zip_archive("Desktop", ["notes.txt"], "notes.zip", approval)
        self.assertIn("destination already exists", result)
        self.assertEqual(destination.read_bytes(), b"keep existing archive")
        approval.assert_not_called()

    def test_destination_created_during_approval_is_not_overwritten(self) -> None:
        source = self.roots["desktop"] / "notes.txt"
        destination = self.roots["desktop"] / "new.zip"
        source.write_text("source", encoding="utf-8")
        def create_destination(_title, _detail):
            destination.write_bytes(b"created while asking")
            return True
        result = automation.create_zip_archive("Desktop", ["notes.txt"], "new.zip", create_destination)
        self.assertIn("appeared after confirmation", result)
        self.assertEqual(destination.read_bytes(), b"created while asking")
        self.assertTrue(source.exists())

    def test_atomic_publish_race_never_overwrites_existing_destination(self) -> None:
        source = self.roots["documents"] / "notes.txt"
        destination = self.roots["documents"] / "race.zip"
        source.write_text("source contents", encoding="utf-8")

        def race_commit(_temp, final_path):
            Path(final_path).write_bytes(b"another process created this")
            raise FileExistsError("destination already created")

        with patch("jarvis.automation.os.link", side_effect=race_commit):
            result = automation.create_zip_archive("Documents", ["notes.txt"], "race.zip", lambda *_: True)

        self.assertIn("destination already exists", result)
        self.assertEqual(destination.read_bytes(), b"another process created this")
        self.assertEqual(source.read_text(encoding="utf-8"), "source contents")
        self.assertFalse(any(p.name.endswith(".tmp") for p in self.roots["documents"].iterdir()))

    def test_blocks_traversal_symlinks_directories_and_duplicate_names(self) -> None:
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        symlink = self.roots["documents"] / "linked.txt"
        symlink.symlink_to(outside)
        (self.roots["documents"] / "folder").mkdir()
        (self.roots["documents"] / "a.txt").write_text("a", encoding="utf-8")
        (self.roots["documents"] / "A.TXT").write_text("A", encoding="utf-8")

        for filenames in (["../outside.txt"], ["linked.txt"], ["folder"], ["a.txt", "a.txt"], ["a.txt", "A.TXT"]):
            with self.subTest(filenames=filenames):
                result = automation.create_zip_archive("Documents", filenames, "out.zip", lambda *_: True)
                self.assertNotIn("Created ZIP archive", result)
                self.assertFalse((self.roots["documents"] / "out.zip").exists())

    def test_rejects_invalid_extension_too_many_files_and_total_size_limit(self) -> None:
        source = self.roots["downloads"] / "a.txt"
        source.write_text("a", encoding="utf-8")
        self.assertIn("must end with .zip", automation.create_zip_archive("Downloads", ["a.txt"], "out.rar", lambda *_: True))
        self.assertIn("at most", automation.create_zip_archive("Downloads", ["a.txt"] * 101, "out.zip", lambda *_: True))
        with patch("jarvis.automation.MAX_ARCHIVE_TOTAL_BYTES", 0):
            result = automation.create_zip_archive("Downloads", ["a.txt"], "out.zip", lambda *_: True)
            self.assertNotIn("Created ZIP archive", result)

    def test_refuses_file_changed_during_approval(self) -> None:
        source = self.roots["documents"] / "plan.md"
        source.write_text("before", encoding="utf-8")
        def mutate(_title, _detail):
            source.write_text("changed with a longer payload", encoding="utf-8")
            return True
        result = automation.create_zip_archive("Documents", ["plan.md"], "plan.zip", mutate)
        self.assertIn("changed after confirmation", result)
        self.assertFalse((self.roots["documents"] / "plan.zip").exists())

    def test_temp_archive_is_cleaned_if_zip_build_fails(self) -> None:
        source = self.roots["documents"] / "plan.md"
        source.write_text("before", encoding="utf-8")
        with patch("jarvis.automation.zipfile.ZipFile", side_effect=OSError("simulated write failure")):
            result = automation.create_zip_archive("Documents", ["plan.md"], "plan.zip", lambda *_: True)
        self.assertIn("stopped safely", result)
        self.assertFalse((self.roots["documents"] / "plan.zip").exists())
        self.assertFalse(any(p.name.endswith(".tmp") for p in self.roots["documents"].iterdir()))


if __name__ == "__main__":
    unittest.main()
