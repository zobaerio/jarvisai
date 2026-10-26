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
        self.assertIsNotNone(started["plan"][0]["started_at"])
        self.assertNotIn("finished_at", started["plan"][0])
        completed = self.store.update_plan_step(
            task["id"],
            first["id"],
            status="completed",
            evidence="assistant_response",
            verification_note="Generated a text deliverable.",
            outcome="completed",
        )
        self.assertEqual(completed["plan"][0]["status"], "completed")
        self.assertEqual(completed["plan"][0]["evidence"], "assistant_response")
        self.assertEqual(completed["plan"][0]["verification_note"], "Generated a text deliverable.")
        self.assertEqual(completed["plan"][0]["outcome"], "completed")
        self.assertIsNotNone(completed["plan"][0]["finished_at"])
        self.assertGreaterEqual(
            completed["plan"][0]["finished_at"],
            completed["plan"][0]["started_at"],
        )

        reloaded = TaskStore(self.path).get_task(task["id"])
        self.assertEqual(reloaded["plan"][0]["status"], "completed")
        self.assertEqual(reloaded["plan"][0]["attempts"], 1)
        self.assertEqual(reloaded["plan"][0]["started_at"], started["plan"][0]["started_at"])
        self.assertEqual(reloaded["plan"][0]["finished_at"], completed["plan"][0]["finished_at"])
        self.assertEqual(reloaded["plan"][1]["status"], "pending")

    def test_failed_step_requires_explicit_retry_transition(self) -> None:
        task = self.store.create_task("A bounded task")
        plan = self.store.set_task_plan(task["id"], ["Do work"])
        step_id = plan["plan"][0]["id"]
        self.store.update_plan_step(task["id"], step_id, status="running")
        failed = self.store.update_plan_step(
            task["id"],
            step_id,
            status="failed",
            evidence="tool_result",
            verification_note="The tool returned an error.",
            outcome="failed",
        )
        self.assertEqual(failed["plan"][0]["status"], "failed")
        with self.assertRaises(ValueError):
            self.store.update_plan_step(task["id"], step_id, status="running")

        pending = self.store.update_plan_step(task["id"], step_id, status="pending")
        self.assertEqual(pending["plan"][0]["status"], "pending")
        self.assertNotIn("started_at", pending["plan"][0])
        self.assertNotIn("finished_at", pending["plan"][0])
        self.assertNotIn("evidence", pending["plan"][0])
        self.assertNotIn("verification_note", pending["plan"][0])
        self.assertNotIn("outcome", pending["plan"][0])
        retried = self.store.update_plan_step(task["id"], step_id, status="running")
        self.assertEqual(retried["plan"][0]["attempts"], 2)
        self.assertIsNotNone(retried["plan"][0]["started_at"])
        self.assertNotIn("finished_at", retried["plan"][0])

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
        self.assertIsNotNone(finalized["plan"][0]["started_at"])
        self.assertIsNotNone(finalized["plan"][0]["finished_at"])
        self.assertNotIn("started_at", finalized["plan"][1])
        self.assertIsNotNone(finalized["plan"][1]["finished_at"])
        self.assertIn("without a dedicated", finalized["plan"][1]["verification_note"])

    def test_running_step_can_be_marked_unverified_with_bounded_evidence(self) -> None:
        task = self.store.create_task("Run and verify")
        plan = self.store.set_task_plan(task["id"], ["Change state"])
        step_id = plan["plan"][0]["id"]
        self.store.update_plan_step(task["id"], step_id, status="running")
        note = "  Change returned, but verification was missing.  "
        updated = self.store.update_plan_step(
            task["id"],
            step_id,
            status="unverified",
            evidence="tool_result",
            verification_note=note,
            outcome="partial",
        )
        step = updated["plan"][0]
        self.assertEqual(step["status"], "unverified")
        self.assertIsNotNone(step["finished_at"])
        self.assertEqual(step["evidence"], "tool_result")
        self.assertEqual(step["verification_note"], "Change returned, but verification was missing.")
        self.assertEqual(step["outcome"], "partial")
        with self.assertRaises(ValueError):
            self.store.update_plan_step(
                task["id"], step_id, status="unverified", evidence="raw_tool_output"
            )

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

    def test_plan_step_kinds_are_persisted_and_unknown_is_the_default(self) -> None:
        task = self.store.create_task("Classified plan")
        planned = self.store.set_task_plan(
            task["id"],
            ["Draft a summary", "Inspect a file", "Create a file"],
            step_kinds=["response", "read_only", "state_change"],
        )
        self.assertEqual(
            [step["kind"] for step in planned["plan"]],
            ["response", "read_only", "state_change"],
        )

        unclassified = self.store.create_task("Legacy plan")
        legacy = self.store.set_task_plan(unclassified["id"], ["Unclassified step"])
        self.assertEqual(legacy["plan"][0]["kind"], "unknown")

    def test_plan_step_kinds_reject_mismatched_or_untrusted_values(self) -> None:
        task = self.store.create_task("Invalid plan kinds")
        with self.assertRaises(ValueError):
            self.store.set_task_plan(task["id"], ["One", "Two"], step_kinds=["response"])
        with self.assertRaises(ValueError):
            self.store.set_task_plan(task["id"], ["One"], step_kinds=["execute_shell"])
        with self.assertRaises(ValueError):
            self.store.set_task_plan(task["id"], ["One"], step_kinds=[None])

    def test_explicit_resume_clones_plan_without_replaying_completed_steps(self) -> None:
        source = self.store.create_task("Create and verify a report")
        plan = self.store.set_task_plan(
            source["id"],
            ["Draft report content", "Create report file", "Verify report file"],
            step_kinds=["response", "state_change", "read_only"],
        )
        first, uncertain, future = plan["plan"]
        completed = self.store.update_plan_step(
            source["id"],
            first["id"],
            status="running",
        )
        completed = self.store.update_plan_step(
            source["id"],
            first["id"],
            status="completed",
            evidence="assistant_response",
            verification_note="Draft text was created.",
            outcome="completed",
        )
        self.store.update_plan_step(source["id"], uncertain["id"], status="running")
        self.store.update_plan_step(
            source["id"],
            uncertain["id"],
            status="unverified",
            evidence="tool_result",
            verification_note="The file state was not verified.",
            outcome="partial",
        )
        self.store.update_plan_step(
            source["id"],
            future["id"],
            status="unverified",
            evidence="none",
            verification_note="Task stopped before this step.",
            outcome="partial",
        )
        self.store.update_task(source["id"], status="partial", result="Stopped before verification.")

        resumed = self.store.create_resumed_plan_task(source["id"])
        self.assertIsNotNone(resumed)
        self.assertNotEqual(resumed["id"], source["id"])
        self.assertEqual(resumed["status"], "queued")
        self.assertEqual(resumed["resumed_from_task_id"], source["id"])
        self.assertEqual(
            [step["status"] for step in resumed["plan"]],
            ["completed", "pending", "pending"],
        )
        self.assertEqual(resumed["plan"][0]["evidence"], "assistant_response")
        self.assertEqual(resumed["plan"][0]["verification_note"], "Draft text was created.")
        self.assertNotEqual(resumed["plan"][0]["id"], first["id"])
        self.assertNotEqual(resumed["plan"][1]["id"], uncertain["id"])
        self.assertNotIn("finished_at", resumed["plan"][1])
        self.assertNotIn("verification_note", resumed["plan"][1])
        self.assertIn("will not be replayed", resumed["steps"][0]["text"])
        # The original record stays terminal and unchanged.
        original = self.store.get_task(source["id"])
        self.assertEqual(original["status"], "partial")
        self.assertEqual([step["status"] for step in original["plan"]], ["completed", "unverified", "unverified"])

    def test_explicit_resume_rejects_active_or_fully_completed_tasks(self) -> None:
        active = self.store.create_task("Still running")
        self.store.set_task_plan(active["id"], ["Step"])
        self.assertIsNone(self.store.create_resumed_plan_task(active["id"]))

        done = self.store.create_task("Already done")
        plan = self.store.set_task_plan(done["id"], ["Step"])
        self.store.update_plan_step(done["id"], plan["plan"][0]["id"], status="running")
        self.store.update_plan_step(done["id"], plan["plan"][0]["id"], status="completed")
        self.store.update_task(done["id"], status="completed")
        self.assertIsNone(self.store.create_resumed_plan_task(done["id"]))

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
