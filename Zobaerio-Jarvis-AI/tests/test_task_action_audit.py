from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.task_store import MAX_ACTIONS_PER_TASK, TaskStore


class TaskActionAuditTests(unittest.TestCase):
    def test_action_lifecycle_is_saved_without_arguments_or_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            task = store.create_task("Open an app")
            action_id = store.start_action(task["id"], "open_application")
            self.assertTrue(action_id)
            running = store.get_task(task["id"])["actions"][0]
            self.assertEqual(running["name"], "open_application")
            self.assertEqual(running["status"], "running")
            self.assertNotIn("arguments", running)
            self.assertNotIn("output", running)

            finished = store.finish_action(
                task["id"], action_id, status="result_received"
            )
            self.assertEqual(finished["status"], "result_received")
            self.assertIsNotNone(finished["finished_at"])
            self.assertIsNone(
                store.finish_action(task["id"], action_id, status="failed", note="late update")
            )

    def test_action_can_be_linked_to_plan_step_without_storing_step_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            task = store.create_task("Create a report")
            plan = store.set_task_plan(task["id"], ["Create report file"])
            step_id = plan["plan"][0]["id"]
            action_id = store.start_action(
                task["id"], "create_text_file", plan_step_id=step_id
            )
            action = store.get_task(task["id"])["actions"][0]
            self.assertTrue(action_id)
            self.assertEqual(action["plan_step_id"], step_id)
            self.assertNotIn("title", action)
            self.assertNotIn("arguments", action)
            self.assertNotIn("output", action)

    def test_recovery_marks_active_steps_unverified_and_unstarted_steps_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            task = store.create_task("Multi-step task")
            plan = store.set_task_plan(task["id"], ["Current step", "Future step"])
            store.update_plan_step(task["id"], plan["plan"][0]["id"], status="running")

            with patch("jarvis.task_store._process_is_running", return_value=False):
                self.assertEqual(store.recover_interrupted_tasks(), 1)

            recovered = store.get_task(task["id"])
            self.assertEqual(recovered["status"], "failed")
            active, pending = recovered["plan"]
            self.assertEqual(active["status"], "unverified")
            self.assertEqual(active["outcome"], "failed")
            self.assertIsNotNone(active["finished_at"])
            self.assertIn("state is unknown", active["verification_note"])
            self.assertEqual(pending["status"], "skipped")
            self.assertEqual(pending["outcome"], "failed")
            self.assertIsNotNone(pending["finished_at"])
            self.assertIn("before this step began", pending["verification_note"])

    def test_tool_failure_note_is_bounded_and_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            task = store.create_task("Check a tool")
            action_id = store.start_action(task["id"], "read_text_file")
            finished = store.finish_action(
                task["id"],
                action_id,
                status="failed",
                note="  RuntimeError\n" + ("x" * 300),
            )
            self.assertEqual(finished["status"], "failed")
            self.assertNotIn("\n", finished["note"])
            self.assertEqual(len(finished["note"]), 120)

    def test_rejects_unknown_action_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            task = store.create_task("Invalid status")
            action_id = store.start_action(task["id"], "test_tool")
            with self.assertRaises(ValueError):
                store.finish_action(task["id"], action_id, status="completed")

    def test_action_log_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            task = store.create_task("Many tools")
            for index in range(MAX_ACTIONS_PER_TASK + 4):
                store.start_action(task["id"], f"tool_{index}")
            actions = store.get_task(task["id"])["actions"]
            self.assertEqual(len(actions), MAX_ACTIONS_PER_TASK)
            self.assertEqual(actions[0]["name"], "tool_4")

    def test_interrupted_running_action_is_marked_unknown_and_not_replayed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            task = store.create_task("Task stopped mid-action")
            store.start_action(task["id"], "create_text_file")
            with patch("jarvis.task_store._process_is_running", return_value=False):
                self.assertEqual(store.recover_interrupted_tasks(), 1)

            recovered = store.get_task(task["id"])
            action = recovered["actions"][0]
            self.assertEqual(recovered["status"], "failed")
            self.assertEqual(action["status"], "interrupted")
            self.assertIsNotNone(action["finished_at"])
            self.assertIn("outcome is unknown", action["note"])
            self.assertIn("not replayed", action["note"])
            self.assertIsNone(store.finish_action(task["id"], action["id"], status="result_received"))


if __name__ == "__main__":
    unittest.main()
