from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.task_store import TaskStore


class InterruptedTaskRecoveryTests(unittest.TestCase):
    def test_recovery_marks_abandoned_tasks_failed_but_keeps_queue_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            running = store.create_task("Copy a report")
            cancelling = store.create_task("Open a plan")
            store.update_task(cancelling["id"], status="cancelling", step="Cancellation requested")
            queued = store.create_task("Open Calculator", status="queued")
            completed = store.create_task("Open Notepad")
            store.update_task(completed["id"], status="completed", result="Window was visible")
            cancelled = store.create_task("Open Paint")
            store.update_task(cancelled["id"], status="cancelled", result="Cancelled by user")

            with patch("jarvis.task_store._process_is_running", return_value=False):
                recovered = store.recover_interrupted_tasks()

            self.assertEqual(recovered, 2)
            running_record = store.get_task(running["id"])
            cancelling_record = store.get_task(cancelling["id"])
            queued_record = store.get_task(queued["id"])
            completed_record = store.get_task(completed["id"])
            cancelled_record = store.get_task(cancelled["id"])

            for record in (running_record, cancelling_record):
                self.assertEqual(record["status"], "failed")
                self.assertIsNotNone(record["finished_at"])
                self.assertIn("not automatically rerun", record["result"])
                self.assertIn("Startup recovery", record["steps"][-1]["text"])
            self.assertEqual(queued_record["status"], "queued")
            self.assertEqual(completed_record["status"], "completed")
            self.assertEqual(cancelled_record["status"], "cancelled")
            self.assertEqual(store.queued_count(), 1)

    def test_recovery_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            task = store.create_task("Prepare an estimate")
            with patch("jarvis.task_store._process_is_running", return_value=False):
                self.assertEqual(store.recover_interrupted_tasks(), 1)
                self.assertEqual(store.recover_interrupted_tasks(), 0)
            recovered = store.get_task(task["id"])
            self.assertEqual(recovered["status"], "failed")
            self.assertEqual(sum("Startup recovery" in s["text"] for s in recovered["steps"]), 1)

    def test_does_not_mark_tasks_owned_by_a_live_process_as_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            task = store.create_task("Run an active task")
            with patch("jarvis.task_store._process_is_running", return_value=True) as alive:
                self.assertEqual(store.recover_interrupted_tasks(), 0)
            alive.assert_called_once_with(task["process_id"])
            self.assertEqual(store.get_task(task["id"])["status"], "running")

    def test_legacy_running_records_without_process_id_are_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            store = TaskStore(path)
            task = store.create_task("Legacy in-progress task")
            data = json.loads(path.read_text(encoding="utf-8"))
            data[0].pop("process_id", None)
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch("jarvis.task_store._process_is_running") as alive:
                self.assertEqual(store.recover_interrupted_tasks(), 1)
            alive.assert_not_called()
            self.assertEqual(store.get_task(task["id"])["status"], "failed")

    def test_queued_tasks_are_not_auto_replayed_by_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            queued = store.create_task("Queued command", status="queued")
            self.assertEqual(store.recover_interrupted_tasks(), 0)
            self.assertEqual(store.get_task(queued["id"])["status"], "queued")
            self.assertEqual(store.queued_count(), 1)


if __name__ == "__main__":
    unittest.main()
