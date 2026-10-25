from __future__ import annotations

import unittest
from unittest.mock import patch

from jarvis.agent import JarvisAgent, TOOLS


class ContentSearchRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.approval = lambda _title, _message: True
        self.agent = JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test"},
            approval=self.approval,
        )

    def test_content_search_is_advertised_to_model(self) -> None:
        names = {tool["function"]["name"] for tool in TOOLS}
        self.assertIn("search_file_contents", names)

    def test_content_search_routes_approval_callback(self) -> None:
        with patch("jarvis.agent.automation.search_file_contents", return_value="Found 1 matching line") as search:
            result = self.agent._execute_tool("search_file_contents", {"query": "concrete", "location": "Documents"})
        self.assertIn("Found 1 matching line", result)
        search.assert_called_once_with("concrete", "Documents", self.approval)


if __name__ == "__main__":
    unittest.main()
