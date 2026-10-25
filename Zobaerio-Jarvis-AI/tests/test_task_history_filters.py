from __future__ import annotations

import copy
import unittest

from jarvis.task_store import filter_task_records


class TaskHistoryFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            {
                "id": "task-101",
                "status": "completed",
                "command": "Create a BOQ",
                "result": "Quantity table generated",
                "steps": [{"text": "Verified the saved file"}],
                "actions": [{"name": "create_text_file", "status": "result_received", "note": ""}],
            },
            {
                "id": "task-102",
                "status": "queued",
                "command": "Export the plan",
                "result": "",
                "steps": [{"text": "Queued by user"}],
                "actions": [],
            },
            {
                "id": "task-103",
                "status": "failed",
                "command": "Check provider",
                "result": "AI provider returned HTTP 401",
                "steps": [],
                "actions": [],
            },
        ]

    def test_status_filter_is_case_insensitive_and_preserves_order(self) -> None:
        result = filter_task_records(self.records, status="COMPLETED")
        self.assertEqual([row["id"] for row in result], ["task-101"])

    def test_search_matches_command_result_progress_and_tool_metadata(self) -> None:
        self.assertEqual(
            [row["id"] for row in filter_task_records(self.records, query="boq")],
            ["task-101"],
        )
        self.assertEqual(
            [row["id"] for row in filter_task_records(self.records, query="http 401")],
            ["task-103"],
        )
        self.assertEqual(
            [row["id"] for row in filter_task_records(self.records, query="create_text_file")],
            ["task-101"],
        )
        self.assertEqual(
            [row["id"] for row in filter_task_records(self.records, query="queued by user")],
            ["task-102"],
        )

    def test_query_normalizes_whitespace_and_caps_input_length(self) -> None:
        result = filter_task_records(self.records, query="   quantity   table   ")
        self.assertEqual([row["id"] for row in result], ["task-101"])
        long_query = "x" * 500
        self.assertEqual(filter_task_records(self.records, query=long_query), [])

    def test_combines_status_and_search_filters(self) -> None:
        self.assertEqual(
            [row["id"] for row in filter_task_records(self.records, query="plan", status="queued")],
            ["task-102"],
        )
        self.assertEqual(
            filter_task_records(self.records, query="plan", status="failed"),
            [],
        )

    def test_invalid_status_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            filter_task_records(self.records, status="anything-else")

    def test_filter_does_not_mutate_source_records_or_return_non_dict_rows(self) -> None:
        snapshot = copy.deepcopy(self.records)
        result = filter_task_records([*self.records, "not-a-record"], query="boq")
        self.assertEqual(self.records, snapshot)
        self.assertEqual([row["id"] for row in result], ["task-101"])


if __name__ == "__main__":
    unittest.main()
