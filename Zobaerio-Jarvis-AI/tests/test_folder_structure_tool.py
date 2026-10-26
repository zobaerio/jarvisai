from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import automation
from jarvis.agent import JarvisAgent, TOOLS


class FolderStructureAutomationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "Desktop"
        self.root.mkdir()
        self.roots = {
            "desktop": self.root,
            "documents": Path(self.temp.name) / "Documents",
            "downloads": Path(self.temp.name) / "Downloads",
        }
        self.root_patch = patch.dict(automation.ROOTS, self.roots)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def test_creates_nested_project_folders_after_one_approval(self) -> None:
        approvals = []

        def approve(title: str, detail: str) -> bool:
            approvals.append((title, detail))
            return True

        result = automation.create_folder_structure(
            "Desktop", ["CivilOS/Drawings", "CivilOS/Reports"], approve
        )
        self.assertIn("Created 3 folders", result)
        self.assertTrue((self.root / "CivilOS" / "Drawings").is_dir())
        self.assertTrue((self.root / "CivilOS" / "Reports").is_dir())
        self.assertEqual(len(approvals), 1)
        self.assertIn(str(self.root / "CivilOS" / "Drawings"), approvals[0][1])

    def test_cancelled_request_creates_nothing(self) -> None:
        result = automation.create_folder_structure(
            "Desktop", ["CivilOS/Drawings"], lambda *_: False
        )
        self.assertIn("Cancelled", result)
        self.assertFalse((self.root / "CivilOS").exists())

    def test_existing_destination_blocks_whole_structure_before_approval(self) -> None:
        (self.root / "CivilOS").mkdir()
        called = []
        result = automation.create_folder_structure(
            "Desktop", ["CivilOS/Drawings"], lambda *_: called.append(True) or True
        )
        self.assertIn("already exist", result)
        self.assertEqual(called, [])
        self.assertFalse((self.root / "CivilOS" / "Drawings").exists())

    def test_rejects_traversal_reserved_names_and_excessive_depth(self) -> None:
        invalid_paths = [
            ["../outside"],
            ["CivilOS/../../outside"],
            ["CivilOS//Drawings"],
            ["C:/outside"],
            ["/absolute/path"],
            ["/".join(["level"] * 9)],
        ]
        for paths in invalid_paths:
            with self.subTest(paths=paths):
                result = automation.create_folder_structure(
                    "Desktop", paths, lambda *_: True
                )
                self.assertIn("blocked", result.casefold())
        self.assertFalse((Path(self.temp.name) / "outside").exists())

    def test_rejects_empty_and_over_limit_path_lists(self) -> None:
        for paths in ([], ["x"] * 31):
            with self.subTest(count=len(paths)):
                result = automation.create_folder_structure(
                    "Desktop", paths, lambda *_: True
                )
                self.assertIn("blocked", result.casefold())


class FolderStructureToolRoutingTests(unittest.TestCase):
    def test_tool_is_advertised_to_model(self) -> None:
        names = {tool["function"]["name"] for tool in TOOLS}
        self.assertIn("create_folder_structure", names)

    def test_routes_folder_list_and_approval_callback(self) -> None:
        approval = lambda *_: True
        agent = JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test"},
            approval=approval,
        )
        args = {"location": "Documents", "folder_paths": ["Project/Drawings"]}
        with patch(
            "jarvis.agent.automation.create_folder_structure",
            return_value="Created 2 folders",
        ) as create:
            result = agent._execute_tool("create_folder_structure", args)
        self.assertEqual(result, "Created 2 folders")
        create.assert_called_once_with("Documents", ["Project/Drawings"], approval)

    def test_rejects_non_list_folder_paths_before_routing(self) -> None:
        agent = JarvisAgent({}, approval=lambda *_: True)
        with patch("jarvis.agent.automation.create_folder_structure") as create:
            result = agent._execute_tool(
                "create_folder_structure",
                {"location": "Desktop", "folder_paths": "Project/Drawings"},
            )
        self.assertIn("must be a list", result)
        create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
