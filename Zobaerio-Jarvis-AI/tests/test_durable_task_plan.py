from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.task_store import MAX_STEPS, TaskStore


class DurableTaskPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "history.json"
        self.store = TaskStore(self.path)

    def test_plan_and_step_transitions_persist_across_store_instances(self) -> None:
        task = self.store.create_task("Prepare a report")
        planned = self.store.set_task_plan(task["id"], ["Inspect inputs", "Create draft", "Verify output"])
        self.assertEqual([step["status"] for step in planned["plan"]], ["pending"] * 3)

        first = planned["plan"][0]
        started = self.store.update_plan_step(task["id"], first["id"], status="running")
        self.assertEqual(started["plan"][0]["attempts"], 1)
        completed = self.store.update_plan_step(task["id"], first["id"], status="completed")
        self.assertEqual(completed["plan"][0]["status"], "completed")

        reloaded = TaskStore(self.path).get_task(task["id"])
        self.assertEqual(reloaded["plan"][0]["status"], "completed")
        self.assertEqual(reloaded["plan"][0]["attempts"], 1)
        self.assertEqual(reloaded["plan"][1]["status"], "pending")

    def test_failed_step_requires_explicit_retry_transition(self) -> None:
        task = self.store.create_task("A bounded task")
        plan = self.store.set_task_plan(task["id"], ["Do work"])
        step_id = plan["plan"][0]["id"]
        self.store.update_plan_step(task["id"], step_id, status="running")
        failed = self.store.update_plan_step(task["id"], step_id, status="failed")
        self.assertEqual(failed["plan"][0]["status"], "failed")
        with self.assertRaises(ValueError):
            self.store.update_plan_step(task["id"], step_id, status="running")

        pending = self.store.update_plan_step(task["id"], step_id, status="pending")
        self.assertEqual(pending["plan"][0]["status"], "pending")
        retried = self.store.update_plan_step(task["id"], step_id, status="running")
        self.assertEqual(retried["plan"][0]["attempts"], 2)

    def test_completed_step_cannot_be_replayed_or_rewritten(self) -> None:
        task = self.store.create_task("Do one thing")
        plan = self.store.set_task_plan(task["id"], ["One step"])
        step_id = plan["plan"][0]["id"]
        self.store.update_plan_step(task["id"], step_id, status="running")
        self.store.update_plan_step(task["id"], step_id, status="completed")
        with self.assertRaises(ValueError):
            self.store.update_plan_step(task["id"], step_id, status="running")

    def test_finalizing_task_marks_only_unfinished_plan_steps_unverified(self) -> None:
        task = self.store.create_task("Prepare a report")
        plan = self.store.set_task_plan(task["id"], ["Inspect inputs", "Create draft"])
        first_id = plan["plan"][0]["id"]
        self.store.update_plan_step(task["id"], first_id, status="running")
        self.store.update_plan_step(task["id"], first_id, status="completed")

        finalized = self.store.finalize_task_plan(task["id"], "partial")
        self.assertEqual(finalized["plan"][0]["status"], "completed")
        self.assertEqual(finalized["plan"][1]["status"], "unverified")
        self.assertEqual(finalized["plan"][1]["outcome"], "partial")
        self.assertIn("without a dedicated", finalized["plan"][1]["verification_note"])

    def test_finalizing_missing_plan_is_safe_and_invalid_outcome_rejected(self) -> None:
        task = self.store.create_task("No plan")
        self.assertIsNotNone(self.store.finalize_task_plan(task["id"], "completed"))
        self.assertIsNone(self.store.finalize_task_plan("missing", "completed"))
        with self.assertRaises(ValueError):
            self.store.finalize_task_plan(task["id"], "unknown")

    def test_plan_input_is_bounded_and_validated(self) -> None:
        task = self.store.create_task("Bounded")
        with self.assertRaises(ValueError):
            self.store.set_task_plan(task["id"], [])
        with self.assertRaises(ValueError):
            self.store.set_task_plan(task["id"], ["valid", " "])
        with self.assertRaises(ValueError):
            self.store.set_task_plan(task["id"], ["x" * 241])
        with self.assertRaises(ValueError):
            self.store.set_task_plan(task["id"], ["step"] * (MAX_STEPS + 1))

    def test_terminal_or_missing_tasks_cannot_be_planned_or_changed(self) -> None:
        task = self.store.create_task("Already finished")
        self.store.update_task(task["id"], status="completed")
        self.assertIsNone(self.store.set_task_plan(task["id"], ["Not allowed"]))
        self.assertIsNone(self.store.update_plan_step(task["id"], "missing", status="running"))
        self.assertIsNone(self.store.set_task_plan("unknown-task", ["Not found"]))

    def test_unknown_step_and_invalid_transitions_fail_closed(self) -> None:
        task = self.store.create_task("Validate transitions")
        self.store.set_task_plan(task["id"], ["First"])
        self.assertIsNone(self.store.update_plan_step(task["id"], "unknown", status="running"))
        with self.assertRaises(ValueError):
            self.store.update_plan_step(task["id"], "unknown", status="unexpected")


if __name__ == "__main__":
    unittest.main()
