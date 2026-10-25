from __future__ import annotations

import unittest
from unittest.mock import patch

from jarvis.agent import JarvisAgent, TOOLS


class SafeZipArchiveToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.approval = lambda _title, _detail: True
        self.agent = JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test"},
            approval=self.approval,
        )

    def test_zip_tool_is_advertised_with_bounded_inputs(self) -> None:
        tool = next(t for t in TOOLS if t["function"]["name"] == "create_zip_archive")
        properties = tool["function"]["parameters"]["properties"]
        self.assertEqual(properties["filenames"]["maxItems"], 100)
        self.assertEqual(properties["filenames"]["minItems"], 1)
        self.assertIn("100 MiB", tool["function"]["description"])

    def test_zip_tool_routes_selected_names_and_approval(self) -> None:
        with patch("jarvis.agent.automation.create_zip_archive", return_value="Created ZIP archive") as create:
            result = self.agent._execute_tool(
                "create_zip_archive",
                {"location": "Documents", "filenames": ["a.txt", "b.csv"], "archive_filename": "bundle.zip"},
            )
        self.assertIn("Created ZIP archive", result)
        create.assert_called_once_with("Documents", ["a.txt", "b.csv"], "bundle.zip", self.approval)

    def test_rejects_non_list_filenames_before_routing(self) -> None:
        with patch("jarvis.agent.automation.create_zip_archive") as create:
            result = self.agent._execute_tool(
                "create_zip_archive",
                {"location": "Documents", "filenames": "a.txt", "archive_filename": "bundle.zip"},
            )
        self.assertIn("must be a list", result)
        create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
