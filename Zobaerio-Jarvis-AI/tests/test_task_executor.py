from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any

from jarvis.task_executor import execute_task_plan
from jarvis.task_store import TaskStore


class FakeStepAgent:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []
        self.tool_budgets: list[int] = []
        self.last_outcome = "completed"
        self.last_tool_call_count = 0
        self.last_tool_call_names: list[str] = []
        self.last_tool_call_failures = 0
        self.last_verification_succeeded = False

    def respond(
        self,
        user_text: str,
        *,
        cancel_event: threading.Event,
        progress=None,
        tool_event=None,
        tool_budget: int = 12,
    ) -> str:
        self.prompts.append(user_text)
        self.tool_budgets.append(tool_budget)
        if cancel_event.is_set():
            self.last_outcome = "cancelled"
            return "Cancelled."
        profile = self.responses.pop(0)
        self.last_outcome = profile.get("outcome", "completed")
        self.last_tool_call_count = profile.get("tool_count", 0)
        self.last_tool_call_names = list(profile.get("tool_names", []))
        self.last_tool_call_failures = profile.get("tool_failures", 0)
        self.last_verification_succeeded = profile.get("verified", False)
        if tool_event is not None:
            for name in profile.get("audit_tools", []):
                action_id = tool_event(name, "running", None, "")
                tool_event(name, "result_received", action_id, "")
        return profile.get("answer", "Step output")


class StepwiseTaskExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.store = TaskStore(Path(self.temp_dir.name) / "history.json")

    def make_plan(
        self,
        titles: list[str],
        kinds: list[str] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        task = self.store.create_task("Run a multi-step task")
        planned = self.store.set_task_plan(
            task["id"],
            titles,
            step_kinds=kinds or ["unknown"] * len(titles),
        )
        return task["id"], planned["plan"]

    @staticmethod
    def no_cancel() -> threading.Event:
        return threading.Event()

    def test_executes_steps_in_order_with_one_shared_tool_budget(self) -> None:
        task_id, plan = self.make_plan(["Inspect system", "Open and verify Notepad"], ["read_only", "state_change"])
        agent = FakeStepAgent([
            {
                "answer": "System information collected.",
                "tool_count": 2,
                "tool_names": ["get_system_info", "search_files"],
                "audit_tools": ["get_system_info", "search_files"],
            },
            {
                "answer": "Notepad was opened and its window was verified.",
                "tool_count": 3,
                "tool_names": ["open_application", "verify_local_action"],
                "verified": True,
                "audit_tools": ["open_application", "verify_local_action"],
            },
        ])

        def tool_event_factory(step_id: str):
            def on_tool(name: str, status: str, action_id: str | None, note: str) -> str | None:
                if status == "running":
                    return self.store.start_action(task_id, name, plan_step_id=step_id)
                if action_id:
                    self.store.finish_action(task_id, action_id, status=status, note=note)
                return action_id
            return on_tool

        result, status = execute_task_plan(
            agent=agent,
            task_store=self.store,
            task_id=task_id,
            user_text="Inspect my system then open and verify Notepad",
            cancel_event=self.no_cancel(),
            tool_event_factory=tool_event_factory,
        )
        self.assertEqual(status, "completed")
        self.assertIn("System information collected.", result)
        self.assertIn("Notepad was opened", result)
        self.assertEqual(agent.tool_budgets, [12, 10])
        saved = self.store.get_task(task_id)
        self.assertEqual([step["status"] for step in saved["plan"]], ["completed", "completed"])
        self.assertEqual(saved["plan"][0]["evidence"], "tool_result")
        self.assertEqual(saved["plan"][1]["evidence"], "verified_local_action")
        self.assertTrue(all(action.get("plan_step_id") for action in saved["actions"]))
        self.assertEqual(saved["actions"][0]["plan_step_id"], plan[0]["id"])
        self.assertEqual(saved["actions"][-1]["plan_step_id"], plan[1]["id"])

    def test_unverified_state_change_stops_later_steps(self) -> None:
        task_id, plan = self.make_plan(["Create a file", "Verify the new file"], ["state_change", "read_only"])
        agent = FakeStepAgent([{
            "answer": "The tool returned, but no verification was run.",
            "tool_count": 1,
            "tool_names": ["create_text_file"],
        }])
        result, status = execute_task_plan(
            agent=agent,
            task_store=self.store,
            task_id=task_id,
            user_text="Create a file and verify it",
            cancel_event=self.no_cancel(),
        )
        self.assertEqual(status, "partial")
        self.assertIn("Later steps were not started", result)
        saved = self.store.get_task(task_id)
        self.assertEqual(saved["plan"][0]["status"], "unverified")
        self.assertEqual(saved["plan"][0]["evidence"], "tool_result")
        self.assertEqual(saved["plan"][1]["status"], "pending")
        self.assertEqual(len(agent.prompts), 1)
        self.assertIn("ACTIVE STEP 1/2", agent.prompts[0])

    def test_response_step_can_use_read_only_research_tools(self) -> None:
        task_id, _plan = self.make_plan(["Prepare a report"], ["response"])
        agent = FakeStepAgent([{
            "answer": "The report summarizes the inspected information.",
            "tool_count": 1,
            "tool_names": ["search_files"],
        }])
        result, status = execute_task_plan(
            agent=agent,
            task_store=self.store,
            task_id=task_id,
            user_text="Prepare a report from available files",
            cancel_event=self.no_cancel(),
        )
        step = self.store.get_task(task_id)["plan"][0]
        self.assertEqual(status, "completed")
        self.assertEqual(step["status"], "completed")
        self.assertEqual(step["evidence"], "tool_result")
        self.assertIn("read-only tool results", step["verification_note"])
        self.assertIn("The report summarizes", result)

    def test_text_only_step_is_completed_from_its_direct_response(self) -> None:
        task_id, _plan = self.make_plan(["Draft a short summary"], ["response"])
        agent = FakeStepAgent([{"answer": "The requested summary is ready."}])
        result, status = execute_task_plan(
            agent=agent,
            task_store=self.store,
            task_id=task_id,
            user_text="Write a short summary",
            cancel_event=self.no_cancel(),
        )
        step = self.store.get_task(task_id)["plan"][0]
        self.assertEqual(status, "completed")
        self.assertEqual(step["status"], "completed")
        self.assertEqual(step["evidence"], "assistant_response")
        self.assertIn("The requested summary is ready.", result)

    def test_unknown_step_does_not_complete_from_read_only_results_alone(self) -> None:
        task_id, _plan = self.make_plan(["Handle the next part"], ["unknown"])
        agent = FakeStepAgent([{
            "answer": "I inspected system information, but the requested step is still ambiguous.",
            "tool_count": 1,
            "tool_names": ["get_system_info"],
        }])
        result, status = execute_task_plan(
            agent=agent,
            task_store=self.store,
            task_id=task_id,
            user_text="Handle the next part",
            cancel_event=self.no_cancel(),
        )
        step = self.store.get_task(task_id)["plan"][0]
        self.assertEqual(status, "partial")
        self.assertEqual(step["status"], "unverified")
        self.assertEqual(step["outcome"], "partial")
        self.assertIn("no execution evidence", result)
        self.assertEqual(len(agent.prompts), 1)

    def test_state_change_step_is_not_completed_from_claimed_text_alone(self) -> None:
        task_id, _plan = self.make_plan(["Create a website"], ["state_change"])
        agent = FakeStepAgent([{
            "answer": "The website has been created.",
            "outcome": "completed",
        }])
        result, status = execute_task_plan(
            agent=agent,
            task_store=self.store,
            task_id=task_id,
            user_text="Create a website",
            cancel_event=self.no_cancel(),
        )
        step = self.store.get_task(task_id)["plan"][0]
        self.assertEqual(status, "partial")
        self.assertEqual(step["status"], "unverified")
        self.assertEqual(step["evidence"], "none")
        self.assertIn("unsupported claim", result)

    def test_resume_skips_completed_steps_and_starts_at_first_pending_step(self) -> None:
        task_id, plan = self.make_plan(
            ["Draft the text", "Create a file", "Verify the file"],
            ["response", "state_change", "read_only"],
        )
        self.store.update_plan_step(
            task_id,
            plan[0]["id"],
            status="running",
        )
        self.store.update_plan_step(
            task_id,
            plan[0]["id"],
            status="completed",
            evidence="assistant_response",
            verification_note="Draft text is ready.",
            outcome="completed",
        )
        agent = FakeStepAgent([
            {
                "answer": "The file has been created and verified.",
                "tool_count": 2,
                "tool_names": ["create_text_file", "verify_local_action"],
                "verified": True,
            },
            {
                "answer": "The file was inspected.",
                "tool_count": 1,
                "tool_names": ["get_system_info"],
            },
        ])
        # Preserve a completed prefix in the plan and leave only the remaining steps pending.
        saved_plan = self.store.get_task(task_id)["plan"]
        for step in saved_plan[1:]:
            self.assertEqual(step["status"], "pending")
        result, status = execute_task_plan(
            agent=agent,
            task_store=self.store,
            task_id=task_id,
            user_text="Draft the text, create a file, and verify it",
            cancel_event=self.no_cancel(),
        )
        self.assertEqual(status, "completed")
        self.assertEqual(len(agent.prompts), 2)
        self.assertIn("ACTIVE STEP 2/3", agent.prompts[0])
        self.assertIn("ACTIVE STEP 3/3", agent.prompts[1])
        final_plan = self.store.get_task(task_id)["plan"]
        self.assertEqual([step["status"] for step in final_plan], ["completed", "completed", "completed"])
        self.assertEqual(final_plan[0]["verification_note"], "Draft text is ready.")
        self.assertIn("Step 2", result)

    def test_failed_step_stops_without_marking_it_complete(self) -> None:
        task_id, _plan = self.make_plan(["Inspect settings", "Prepare result"], ["read_only", "response"])
        agent = FakeStepAgent([{
            "answer": "The AI endpoint failed.",
            "outcome": "failed",
        }])
        _result, status = execute_task_plan(
            agent=agent,
            task_store=self.store,
            task_id=task_id,
            user_text="Inspect settings and prepare result",
            cancel_event=self.no_cancel(),
        )
        saved = self.store.get_task(task_id)
        self.assertEqual(status, "failed")
        self.assertEqual(saved["plan"][0]["status"], "failed")
        self.assertEqual(saved["plan"][1]["status"], "pending")
        self.assertEqual(len(agent.prompts), 1)

    def test_executor_never_replays_uncertain_steps_without_explicit_resume(self) -> None:
        task_id, plan = self.make_plan(["Create a file", "Inspect result"], ["state_change", "read_only"])
        self.store.update_plan_step(task_id, plan[0]["id"], status="running")
        self.store.update_plan_step(
            task_id,
            plan[0]["id"],
            status="unverified",
            evidence="tool_result",
            verification_note="The action may have occurred.",
            outcome="partial",
        )
        agent = FakeStepAgent([])
        result, status = execute_task_plan(
            agent=agent,
            task_store=self.store,
            task_id=task_id,
            user_text="Create a file and inspect it",
            cancel_event=self.no_cancel(),
        )
        self.assertEqual(status, "partial")
        self.assertIn("No action was replayed", result)
        self.assertEqual(agent.prompts, [])
        saved = self.store.get_task(task_id)
        self.assertEqual(saved["plan"][0]["status"], "unverified")
        self.assertEqual(saved["plan"][1]["status"], "pending")

    def test_failure_after_tool_activity_leaves_step_unverified(self) -> None:
        task_id, _plan = self.make_plan(["Create a file", "Verify the file"], ["state_change", "read_only"])
        agent = FakeStepAgent([{
            "answer": "An error happened after the file action was attempted.",
            "outcome": "failed",
            "tool_count": 1,
            "tool_names": ["create_text_file"],
        }])
        _result, status = execute_task_plan(
            agent=agent,
            task_store=self.store,
            task_id=task_id,
            user_text="Create a file then verify it",
            cancel_event=self.no_cancel(),
        )
        saved = self.store.get_task(task_id)
        self.assertEqual(status, "partial")
        self.assertEqual(saved["plan"][0]["status"], "unverified")
        self.assertEqual(saved["plan"][0]["evidence"], "tool_result")
        self.assertEqual(saved["plan"][0]["outcome"], "partial")
        self.assertEqual(saved["plan"][1]["status"], "pending")
        self.assertEqual(len(agent.prompts), 1)

    def test_cancellation_prevents_starting_the_next_step(self) -> None:
        task_id, _plan = self.make_plan(["First output", "Second output"])
        event = threading.Event()
        event.set()
        agent = FakeStepAgent([])
        _result, status = execute_task_plan(
            agent=agent,
            task_store=self.store,
            task_id=task_id,
            user_text="Do two things step by step",
            cancel_event=event,
        )
        self.assertEqual(status, "cancelled")
        self.assertEqual(agent.prompts, [])
        saved = self.store.get_task(task_id)
        self.assertEqual([step["status"] for step in saved["plan"]], ["pending", "pending"])


if __name__ == "__main__":
    unittest.main()
