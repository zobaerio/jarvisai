from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.task_store import TaskStore


class QueuedTaskControlTests(unittest.TestCase):
    def test_cancel_queued_task_marks_it_cancelled_without_running_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            queued = store.create_task("Create the report", status="queued")
            cancelled = store.cancel_queued_task(queued["id"])

            self.assertEqual(cancelled["status"], "cancelled")
            self.assertIsNotNone(cancelled["finished_at"])
            self.assertIn("before execution", cancelled["result"])
            self.assertIn("was not run", cancelled["result"])
            self.assertIn("cancelled by user", cancelled["steps"][-1]["text"])
            self.assertEqual(store.queued_count(), 0)
            self.assertIsNone(store.next_queued_task())
            self.assertEqual(TaskStore(Path(directory) / "history.json").get_task(queued["id"])["status"], "cancelled")

    def test_cancelled_item_is_skipped_and_next_queued_item_keeps_fifo_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            first = store.create_task("First command", status="queued")
            second = store.create_task("Second command", status="queued")
            self.assertEqual(store.next_queued_task()["id"], first["id"])

            store.cancel_queued_task(first["id"])
            self.assertEqual(store.next_queued_task()["id"], second["id"])
            self.assertEqual(store.queued_count(), 1)

    def test_running_and_terminal_tasks_cannot_be_cancelled_as_queued(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            running = store.create_task("Already started")
            completed = store.create_task("Already completed")
            store.update_task(completed["id"], status="completed", result="Finished")

            self.assertIsNone(store.cancel_queued_task(running["id"]))
            self.assertIsNone(store.cancel_queued_task(completed["id"]))
            self.assertEqual(store.get_task(running["id"])["status"], "running")
            self.assertEqual(store.get_task(completed["id"])["status"], "completed")

    def test_unknown_task_id_is_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            self.assertIsNone(store.cancel_queued_task("missing-id"))
            self.assertEqual(store.queued_count(), 0)


if __name__ == "__main__":
    unittest.main()
