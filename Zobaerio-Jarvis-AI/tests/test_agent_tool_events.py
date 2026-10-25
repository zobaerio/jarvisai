from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, patch

from jarvis.agent import JarvisAgent


class AgentToolEventTests(unittest.TestCase):
    @staticmethod
    def provider_response(message: dict) -> Mock:
        response = Mock()
        response.status_code = 200
        response.headers = {}
        response.json.return_value = {"choices": [{"message": message}]}
        return response

    def test_emits_running_then_result_received_without_copying_payloads(self) -> None:
        call_message = {
            "role": "assistant",
            "tool_calls": [{
                "id": "call-1",
                "type": "function",
                "function": {"name": "get_system_info", "arguments": "{}"},
            }],
        }
        final_message = {"role": "assistant", "content": "Finished"}
        first = self.provider_response(call_message)
        second = self.provider_response(final_message)
        agent = JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test"},
            approval=lambda *_args: True,
        )
        events: list[tuple[str, str, str | None, str]] = []

        def on_tool_event(name: str, status: str, action_id: str | None, note: str) -> str | None:
            events.append((name, status, action_id, note))
            return "audit-01" if status == "running" else action_id

        with patch("jarvis.agent.automation.direct_command", return_value=None), patch(
            "jarvis.agent.get_api_key", return_value=""
        ), patch("jarvis.agent.requests.post", side_effect=[first, second]), patch.object(
            agent, "_execute_tool", return_value="private result content"
        ) as execute:
            result = agent.respond(
                "Please use the system information tool",
                tool_event=on_tool_event,
            )

        self.assertEqual(result, "Finished")
        execute.assert_called_once_with("get_system_info", {})
        self.assertEqual(
            events,
            [
                ("get_system_info", "running", None, ""),
                ("get_system_info", "result_received", "audit-01", ""),
            ],
        )
        self.assertNotIn("private result content", repr(events))

    def test_tool_exception_emits_only_exception_type_in_audit_note(self) -> None:
        first = self.provider_response({
            "role": "assistant",
            "tool_calls": [{
                "id": "call-2",
                "type": "function",
                "function": {"name": "get_system_info", "arguments": "{}"},
            }],
        })
        second = self.provider_response({"role": "assistant", "content": "Stopped"})
        agent = JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test"},
            approval=lambda *_args: True,
        )
        events: list[tuple[str, str, str | None, str]] = []

        def on_tool_event(name: str, status: str, action_id: str | None, note: str) -> str | None:
            events.append((name, status, action_id, note))
            return "audit-02" if status == "running" else action_id

        progress: list[str] = []
        with patch("jarvis.agent.automation.direct_command", return_value=None), patch(
            "jarvis.agent.get_api_key", return_value=""
        ), patch("jarvis.agent.requests.post", side_effect=[first, second]) as post, patch.object(
            agent, "_execute_tool", side_effect=RuntimeError("sensitive details should not enter audit metadata")
        ):
            result = agent.respond("Run a tool", tool_event=on_tool_event, progress=progress.append)

        self.assertEqual(result, "Stopped")
        self.assertEqual(agent.last_outcome, "partial")
        self.assertEqual(events[-1][1:], ("failed", "audit-02", "RuntimeError"))
        self.assertNotIn("sensitive details", repr(events))
        self.assertNotIn("sensitive details", repr(progress))
        self.assertIn("Tool returned: get_system_info", progress)
        provider_payload = json.dumps(post.call_args_list[1].kwargs["json"]["messages"])
        self.assertIn("Sensitive exception details were withheld", provider_payload)
        self.assertNotIn("sensitive details should not enter audit metadata", provider_payload)


if __name__ == "__main__":
    unittest.main()
