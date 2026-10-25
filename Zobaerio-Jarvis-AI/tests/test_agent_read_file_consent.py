from __future__ import annotations

import unittest
from unittest.mock import patch

from jarvis.agent import JarvisAgent, SYSTEM_PROMPT, TOOLS


class ReadFileConsentRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.approval = lambda _title, _message: True
        self.agent = JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test"},
            approval=self.approval,
        )

    def test_file_read_tool_schema_and_prompt_require_consent(self) -> None:
        tool = next(tool for tool in TOOLS if tool["function"]["name"] == "read_text_file")
        self.assertIn("explicit user approval", tool["function"]["description"])
        self.assertIn("explicit, action-specific approval", SYSTEM_PROMPT)
        self.assertIn("configured AI provider", SYSTEM_PROMPT)

    def test_read_file_routes_approval_callback(self) -> None:
        with patch("jarvis.agent.automation.read_text_file", return_value="Contents of file") as read:
            result = self.agent._execute_tool("read_text_file", {"location": "Documents", "filename": "brief.md"})
        self.assertIn("Contents of file", result)
        read.assert_called_once_with("Documents", "brief.md", self.approval)


if __name__ == "__main__":
    unittest.main()
