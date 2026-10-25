from __future__ import annotations

import unittest
from unittest.mock import patch

from jarvis.agent import JarvisAgent, TOOLS


class FileOperationToolRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.approval = lambda _title, _message: True
        self.agent = JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test"},
            approval=self.approval,
        )

    def test_all_file_operations_are_advertised(self) -> None:
        names = {tool["function"]["name"] for tool in TOOLS}
        self.assertTrue({"copy_file", "move_file", "rename_file"}.issubset(names))

    def test_copy_routes_to_automation_with_approval_callback(self) -> None:
        args = {
            "source_location": "Documents",
            "filename": "a.txt",
            "destination_location": "Downloads",
            "destination_filename": "a-copy.txt",
        }
        with patch("jarvis.agent.automation.copy_file", return_value="Copied file") as copy:
            self.assertEqual(self.agent._execute_tool("copy_file", args), "Copied file")
        copy.assert_called_once_with("Documents", "a.txt", "Downloads", "a-copy.txt", self.approval)

    def test_move_routes_to_automation_with_approval_callback(self) -> None:
        args = {
            "source_location": "Desktop",
            "filename": "a.txt",
            "destination_location": "Documents",
            "destination_filename": "a.txt",
        }
        with patch("jarvis.agent.automation.move_file", return_value="Moved file") as move:
            self.assertEqual(self.agent._execute_tool("move_file", args), "Moved file")
        move.assert_called_once_with("Desktop", "a.txt", "Documents", "a.txt", self.approval)

    def test_rename_routes_to_automation_with_approval_callback(self) -> None:
        args = {"location": "Downloads", "filename": "a.txt", "new_filename": "b.txt"}
        with patch("jarvis.agent.automation.rename_file", return_value="Renamed file") as rename:
            self.assertEqual(self.agent._execute_tool("rename_file", args), "Renamed file")
        rename.assert_called_once_with("Downloads", "a.txt", "b.txt", self.approval)


if __name__ == "__main__":
    unittest.main()
