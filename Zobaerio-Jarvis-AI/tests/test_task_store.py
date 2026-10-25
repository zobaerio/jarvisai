from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jarvis.task_store import MAX_TASKS, TaskStore


class TaskStoreTests(unittest.TestCase):
    def test_create_update_and_reload_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            store = TaskStore(path)
            created = store.create_task("Open Notepad")
            self.assertEqual(created["status"], "running")
            self.assertTrue(created["id"])
            store.update_task(created["id"], step="Contacting AI model")
            finished = store.update_task(
                created["id"], status="completed", result="Notepad opened"
            )
            self.assertEqual(finished["status"], "completed")
            self.assertIsNotNone(finished["finished_at"])
            self.assertEqual(len(finished["steps"]), 1)
            reloaded = TaskStore(path).get_task(created["id"])
            self.assertEqual(reloaded["result"], "Notepad opened")
            self.assertEqual(reloaded["steps"][0]["text"], "Contacting AI model")

    def test_history_is_bounded_and_lists_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            task_ids = [store.create_task(f"command {n}")["id"] for n in range(MAX_TASKS + 7)]
            rows = store.list_tasks(limit=MAX_TASKS)
            self.assertEqual(len(rows), MAX_TASKS)
            self.assertEqual(rows[0]["id"], task_ids[-1])
            self.assertEqual(rows[-1]["id"], task_ids[7])
            self.assertIsNone(store.get_task(task_ids[0]))

    def test_corrupt_history_recovers_for_new_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text("{not json", encoding="utf-8")
            store = TaskStore(path)
            record = store.create_task("recover")
            self.assertEqual(store.get_task(record["id"])["command"], "recover")
            self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), list)

    def test_rejects_unknown_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            task_id = store.create_task("status check")["id"]
            with self.assertRaises(ValueError):
                store.update_task(task_id, status="successful-ish")


if __name__ == "__main__":
    unittest.main()
