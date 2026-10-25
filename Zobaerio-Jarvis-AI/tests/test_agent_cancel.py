from __future__ import annotations

import threading
import unittest
from unittest.mock import Mock, patch

from jarvis.agent import JarvisAgent


class AgentCancellationTests(unittest.TestCase):
    def test_cancelled_before_start_runs_no_tools(self) -> None:
        event = threading.Event()
        event.set()
        agent = JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test"},
            approval=lambda _title, _message: True,
        )
        with patch.object(agent, "_execute_tool") as execute:
            result = agent.respond("Open Notepad", cancel_event=event)
        execute.assert_not_called()
        self.assertIn("বাতিল", result)

    def test_cancel_after_model_request_runs_no_requested_tool(self) -> None:
        event = threading.Event()
        agent = JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test"},
            approval=lambda _title, _message: True,
        )
        response = Mock()
        response.status_code = 200

        def post(*_args, **_kwargs):
            event.set()
            return response

        with patch("jarvis.agent.get_api_key", return_value=""), patch(
            "jarvis.agent.requests.post", side_effect=post
        ), patch.object(agent, "_execute_tool") as execute:
            result = agent.respond("Please open Notepad", cancel_event=event)
        execute.assert_not_called()
        self.assertIn("বাতিল", result)


if __name__ == "__main__":
    unittest.main()
