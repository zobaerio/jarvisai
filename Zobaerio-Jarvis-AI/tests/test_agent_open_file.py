from __future__ import annotations

import unittest
from unittest.mock import patch

from jarvis.agent import JarvisAgent, TOOLS


class OpenFileToolRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.approval = lambda _title, _message: True
        self.agent = JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test"},
            approval=self.approval,
        )

    def test_open_file_is_advertised_to_model(self) -> None:
        names = {tool["function"]["name"] for tool in TOOLS}
        self.assertIn("open_file", names)

    def test_open_file_routes_approval_callback(self) -> None:
        with patch("jarvis.agent.automation.open_file", return_value="Asked Windows to open") as open_file:
            result = self.agent._execute_tool("open_file", {"location": "Documents", "filename": "plan.pdf"})
        self.assertIn("Asked Windows to open", result)
        open_file.assert_called_once_with("Documents", "plan.pdf", self.approval)


if __name__ == "__main__":
    unittest.main()
