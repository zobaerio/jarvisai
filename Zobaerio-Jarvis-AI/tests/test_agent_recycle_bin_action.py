from __future__ import annotations

import unittest
from unittest.mock import patch

from jarvis.agent import JarvisAgent, SYSTEM_PROMPT, TOOLS


class RecycleBinToolRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.approval = lambda _title, _message: True
        self.agent = JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test"},
            approval=self.approval,
        )

    def test_tool_and_prompt_describe_recoverable_approved_action(self) -> None:
        names = {tool["function"]["name"] for tool in TOOLS}
        self.assertIn("move_file_to_recycle_bin", names)
        tool = next(t for t in TOOLS if t["function"]["name"] == "move_file_to_recycle_bin")
        self.assertIn("not permanent deletion", tool["function"]["description"])
        self.assertIn("must never be described as permanent deletion", SYSTEM_PROMPT)

    def test_tool_routes_approval_callback(self) -> None:
        with patch("jarvis.agent.automation.move_file_to_recycle_bin", return_value="Moved to the Windows Recycle Bin") as trash:
            result = self.agent._execute_tool("move_file_to_recycle_bin", {"location": "Documents", "filename": "draft.txt"})
        self.assertIn("Moved to the Windows Recycle Bin", result)
        trash.assert_called_once_with("Documents", "draft.txt", self.approval)


if __name__ == "__main__":
    unittest.main()
