from __future__ import annotations

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
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

    def test_corrupt_primary_recovers_from_valid_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            store = TaskStore(path)
            first = store.create_task("recover this task")
            store.update_task(first["id"], result="previous result")
            backup = path.with_suffix(path.suffix + ".bak")
            self.assertTrue(backup.is_file())
            path.write_text("{truncated primary", encoding="utf-8")

            recovered = TaskStore(path).list_tasks()
            self.assertEqual(len(recovered), 1)
            self.assertEqual(recovered[0]["command"], "recover this task")
            self.assertEqual(recovered[0]["result"], "previous result")

    def test_multiple_store_instances_do_not_lose_concurrent_updates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            stores = [TaskStore(path) for _ in range(8)]
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(stores[index % len(stores)].create_task, f"parallel command {index}")
                    for index in range(64)
                ]
                [future.result() for future in futures]

            rows = TaskStore(path).list_tasks(limit=MAX_TASKS)
            self.assertEqual(len(rows), 64)
            self.assertEqual(len({row["command"] for row in rows}), 64)

    def test_failed_atomic_write_preserves_last_good_history_and_cleans_temp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            store = TaskStore(path)
            store.create_task("last known good")
            previous = path.read_bytes()

            with patch("jarvis.task_store.os.fsync", side_effect=OSError("simulated disk write failure")):
                with self.assertRaises(OSError):
                    store.create_task("must not replace the good file")

            self.assertEqual(path.read_bytes(), previous)
            self.assertEqual(TaskStore(path).list_tasks()[0]["command"], "last known good")
            self.assertFalse(any(item.name.endswith(".tmp") for item in path.parent.iterdir()))

    def test_corrupt_history_recovers_for_new_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text("{not json", encoding="utf-8")
            store = TaskStore(path)
            record = store.create_task("recover")
            self.assertEqual(store.get_task(record["id"])["command"], "recover")
            self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), list)

    def test_persistent_queue_returns_oldest_queued_task_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            first = store.create_task("Open Notepad", status="queued")
            second = store.create_task("Open Calculator", status="queued")
            self.assertEqual(store.queued_count(), 2)
            self.assertEqual(store.next_queued_task()["id"], first["id"])
            store.update_task(first["id"], status="running", step="Started from queue")
            self.assertEqual(store.next_queued_task()["id"], second["id"])
            store.update_task(second["id"], status="completed", result="Opened")
            self.assertEqual(store.queued_count(), 0)
            self.assertIsNone(store.next_queued_task())

    def test_new_task_status_must_be_queued_or_running(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            with self.assertRaises(ValueError):
                store.create_task("bad status", status="completed")

    def test_rejects_unknown_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            task_id = store.create_task("status check")["id"]
            with self.assertRaises(ValueError):
                store.update_task(task_id, status="successful-ish")


if __name__ == "__main__":
    unittest.main()
