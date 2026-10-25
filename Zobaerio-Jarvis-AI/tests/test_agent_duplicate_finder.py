from __future__ import annotations

import unittest
from unittest.mock import patch

from jarvis.agent import JarvisAgent, TOOLS


class DuplicateFinderToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.approval = lambda _title, _detail: True
        self.agent = JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test"},
            approval=self.approval,
        )

    def test_duplicate_finder_tool_is_advertised_as_read_only(self) -> None:
        tool = next(t for t in TOOLS if t["function"]["name"] == "find_duplicate_files")
        self.assertIn("never edits or deletes files", tool["function"]["description"].lower())
        self.assertEqual(
            tool["function"]["parameters"]["properties"]["location"]["enum"],
            ["Desktop", "Documents", "Downloads", "All"],
        )

    def test_duplicate_finder_routes_approval_callback(self) -> None:
        with patch("jarvis.agent.automation.find_duplicate_files", return_value="Found 1 duplicate group") as finder:
            result = self.agent._execute_tool("find_duplicate_files", {"location": "All"})
        self.assertIn("duplicate group", result)
        finder.assert_called_once_with("All", self.approval)


if __name__ == "__main__":
    unittest.main()
