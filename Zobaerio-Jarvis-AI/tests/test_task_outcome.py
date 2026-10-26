from __future__ import annotations

import threading
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jarvis.agent import JarvisAgent
from jarvis.task_store import TaskStore


class AgentOutcomeTests(unittest.TestCase):
    @staticmethod
    def provider_response(message: dict, status_code: int = 200) -> Mock:
        response = Mock()
        response.status_code = status_code
        response.headers = {}
        response.json.return_value = {"choices": [{"message": message}]}
        return response

    def make_agent(self) -> JarvisAgent:
        return JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test"},
            approval=lambda *_args: True,
        )

    def respond(self, agent: JarvisAgent, text: str, **kwargs) -> str:
        with patch("jarvis.agent.automation.direct_command", return_value=None), patch(
            "jarvis.agent.get_api_key", return_value=""
        ):
            return agent.respond(text, **kwargs)

    def test_missing_model_is_failed_not_completed(self) -> None:
        agent = JarvisAgent({}, approval=lambda *_args: True)
        with patch("jarvis.agent.automation.direct_command", return_value=None):
            result = agent.respond("Summarize my plan")
        self.assertIn("AI model সেট করা নেই", result)
        self.assertEqual(agent.last_outcome, "failed")

    def test_cancellation_before_start_has_cancelled_outcome(self) -> None:
        agent = self.make_agent()
        event = threading.Event()
        event.set()
        with patch("jarvis.agent.automation.direct_command") as direct:
            result = agent.respond("Open Notepad", cancel_event=event)
        self.assertIn("বাতিল", result)
        self.assertEqual(agent.last_outcome, "cancelled")
        direct.assert_not_called()

    def test_provider_http_error_is_failed(self) -> None:
        agent = self.make_agent()
        response = self.provider_response({}, status_code=401)
        with patch("jarvis.agent.automation.direct_command", return_value=None), patch(
            "jarvis.agent.get_api_key", return_value=""
        ), patch("jarvis.agent.requests.post", return_value=response):
            result = agent.respond("Analyze my task")
        self.assertIn("HTTP 401", result)
        self.assertEqual(agent.last_outcome, "failed")

    def test_normal_text_response_is_completed(self) -> None:
        agent = self.make_agent()
        response = self.provider_response({"role": "assistant", "content": "Analysis complete."})
        with patch("jarvis.agent.automation.direct_command", return_value=None), patch(
            "jarvis.agent.get_api_key", return_value=""
        ), patch("jarvis.agent.requests.post", return_value=response):
            result = agent.respond("Explain my plan")
        self.assertEqual(result, "Analysis complete.")
        self.assertEqual(agent.last_outcome, "completed")

    def test_tool_exception_followed_by_answer_is_partial(self) -> None:
        agent = self.make_agent()
        tool_response = self.provider_response({
            "role": "assistant",
            "tool_calls": [{
                "id": "call-1",
                "type": "function",
                "function": {"name": "get_system_info", "arguments": "{}"},
            }],
        })
        final_response = self.provider_response({"role": "assistant", "content": "I could not finish every step."})
        with patch("jarvis.agent.automation.direct_command", return_value=None), patch(
            "jarvis.agent.get_api_key", return_value=""
        ), patch("jarvis.agent.requests.post", side_effect=[tool_response, final_response]), patch.object(
            agent, "_execute_tool", side_effect=RuntimeError("private diagnostic")
        ):
            result = agent.respond("Check system information")
        self.assertEqual(result, "I could not finish every step.")
        self.assertEqual(agent.last_outcome, "partial")

    def test_tool_budget_exhaustion_is_partial(self) -> None:
        agent = self.make_agent()
        calls = [{
            "id": f"call-{index}",
            "type": "function",
            "function": {"name": "get_system_info", "arguments": "{}"},
        } for index in range(13)]
        response = self.provider_response({"role": "assistant", "tool_calls": calls})
        progress: list[str] = []
        with patch("jarvis.agent.automation.direct_command", return_value=None), patch(
            "jarvis.agent.get_api_key", return_value=""
        ), patch("jarvis.agent.requests.post", return_value=response) as post, patch.object(
            agent, "_execute_tool", return_value="ok"
        ) as execute:
            result = agent.respond("Check several system details", progress=progress.append)
        self.assertIn("Partially completed", result)
        self.assertEqual(agent.last_outcome, "partial")
        self.assertEqual(execute.call_count, 12)
        post.assert_called_once()
        self.assertTrue(any("Task action budget reached" in item for item in progress))

    def test_custom_tool_budget_caps_actions_for_a_plan_step(self) -> None:
        agent = self.make_agent()
        calls = [{
            "id": f"call-{index}",
            "type": "function",
            "function": {"name": "get_system_info", "arguments": "{}"},
        } for index in range(3)]
        response = self.provider_response({"role": "assistant", "tool_calls": calls})
        with patch("jarvis.agent.automation.direct_command", return_value=None), patch(
            "jarvis.agent.get_api_key", return_value=""
        ), patch("jarvis.agent.requests.post", return_value=response), patch.object(
            agent, "_execute_tool", return_value="ok"
        ) as execute:
            result = agent.respond("Inspect this step", tool_budget=2)
        self.assertIn("Partially completed", result)
        self.assertEqual(agent.last_outcome, "partial")
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(agent.last_tool_call_count, 2)
        self.assertEqual(agent.last_tool_call_names, ["get_system_info", "get_system_info"])

    def test_positive_local_verification_is_reported_as_bounded_metadata(self) -> None:
        agent = self.make_agent()
        create_call = self.provider_response({
            "role": "assistant",
            "tool_calls": [{
                "id": "create-1",
                "type": "function",
                "function": {
                    "name": "create_text_file",
                    "arguments": '{"location":"Documents","filename":"report.txt","content":"hello"}',
                },
            }],
        })
        verify_call = self.provider_response({
            "role": "assistant",
            "tool_calls": [{
                "id": "verify-1",
                "type": "function",
                "function": {
                    "name": "verify_local_action",
                    "arguments": '{"kind":"file","target":"report.txt","location":"Documents"}',
                },
            }],
        })
        final = self.provider_response({"role": "assistant", "content": "The file was created and verified."})

        def execute_tool(name, _args):
            return "Verified file exists: report.txt (12 bytes)." if name == "verify_local_action" else "Created file."

        with patch("jarvis.agent.automation.direct_command", return_value=None), patch(
            "jarvis.agent.get_api_key", return_value=""
        ), patch("jarvis.agent.requests.post", side_effect=[create_call, verify_call, final]), patch.object(
            agent, "_execute_tool", side_effect=execute_tool
        ):
            result = agent.respond("Create and verify a file")
        self.assertEqual(agent.last_outcome, "completed")
        self.assertIn("verified", result.lower())
        self.assertEqual(agent.last_tool_call_count, 2)
        self.assertTrue(agent.last_verification_succeeded)

    def test_verification_of_an_unrelated_target_is_not_accepted(self) -> None:
        agent = self.make_agent()
        create_call = self.provider_response({
            "role": "assistant",
            "tool_calls": [{
                "id": "create-1",
                "type": "function",
                "function": {
                    "name": "create_text_file",
                    "arguments": '{"location":"Documents","filename":"report.txt","content":"hello"}',
                },
            }],
        })
        verify_call = self.provider_response({
            "role": "assistant",
            "tool_calls": [{
                "id": "verify-1",
                "type": "function",
                "function": {
                    "name": "verify_local_action",
                    "arguments": '{"kind":"file","target":"another.txt","location":"Documents"}',
                },
            }],
        })
        final = self.provider_response({"role": "assistant", "content": "The action was attempted."})

        with patch("jarvis.agent.automation.direct_command", return_value=None), patch(
            "jarvis.agent.get_api_key", return_value=""
        ), patch("jarvis.agent.requests.post", side_effect=[create_call, verify_call, final]), patch.object(
            agent, "_execute_tool", side_effect=lambda name, _args: (
                "Verified file exists: another.txt (12 bytes)." if name == "verify_local_action"
                else "Created file: report.txt"
            )
        ):
            agent.respond("Create report.txt and verify it")
        self.assertFalse(agent.last_verification_succeeded)

    def test_bare_website_hostname_maps_to_its_own_verification_target(self) -> None:
        from jarvis.agent import _expected_verification_targets

        self.assertEqual(
            _expected_verification_targets("open_website", {"url_or_query": "example.com"}),
            {("window", "example.com", "")},
        )
        self.assertEqual(
            _expected_verification_targets(
                "open_website",
                {"url_or_query": "https://www.example.com/path"},
            ),
            {("window", "example.com", "")},
        )
        self.assertEqual(
            _expected_verification_targets("open_website", {"url_or_query": "weather tomorrow"}),
            {("window", "google", "")},
        )

    def test_later_state_change_invalidates_an_earlier_verification(self) -> None:
        agent = self.make_agent()
        verify_call = self.provider_response({
            "role": "assistant",
            "tool_calls": [{
                "id": "verify-1",
                "type": "function",
                "function": {"name": "verify_local_action", "arguments": "{}"},
            }],
        })
        create_call = self.provider_response({
            "role": "assistant",
            "tool_calls": [{
                "id": "create-1",
                "type": "function",
                "function": {"name": "create_text_file", "arguments": "{}"},
            }],
        })
        final = self.provider_response({"role": "assistant", "content": "Done."})

        def execute_tool(name, _args):
            return "Verified file exists: old.txt (10 bytes)." if name == "verify_local_action" else "Created file."

        with patch("jarvis.agent.automation.direct_command", return_value=None), patch(
            "jarvis.agent.get_api_key", return_value=""
        ), patch("jarvis.agent.requests.post", side_effect=[verify_call, create_call, final]), patch.object(
            agent, "_execute_tool", side_effect=execute_tool
        ):
            agent.respond("Perform a verified state change")
        self.assertFalse(agent.last_verification_succeeded)

    def test_partial_task_status_is_persisted_as_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = TaskStore(Path(directory) / "history.json")
            task = store.create_task("Run a multi-step task")
            updated = store.update_task(task["id"], status="partial", result="Stopped at action budget")
            self.assertEqual(updated["status"], "partial")
            self.assertIsNotNone(updated["finished_at"])
            self.assertEqual(store.get_task(task["id"])["status"], "partial")


if __name__ == "__main__":
    unittest.main()
