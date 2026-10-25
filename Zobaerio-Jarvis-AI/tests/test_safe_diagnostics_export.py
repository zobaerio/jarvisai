from __future__ import annotations

import json
import unittest

from jarvis.task_store import build_safe_diagnostics
from jarvis.version import APP_VERSION


class SafeDiagnosticsExportTests(unittest.TestCase):
    def test_diagnostics_uses_central_app_version_by_default(self) -> None:
        report = build_safe_diagnostics([])
        self.assertEqual(report["app_version"], APP_VERSION)
        self.assertEqual(APP_VERSION, "1.7.1")

    def test_report_contains_aggregates_without_user_content_or_identifiers(self) -> None:
        records = [
            {
                "id": "private-task-id-77",
                "status": "failed",
                "created_at": "2026-10-25T10:00:00+00:00",
                "finished_at": "2026-10-25T10:03:00+00:00",
                "command": "PRIVATE_COMMAND_SENTINEL create a confidential bill of quantities",
                "result": "PRIVATE_RESULT_SENTINEL customer data should not leave this PC",
                "steps": [{"time": "2026-10-25T10:01:00+00:00", "text": "PRIVATE_PROGRESS_SENTINEL /users/demo/secret.dwg"}],
                "actions": [{
                    "name": "PRIVATE_TOOL_NAME_SENTINEL",
                    "status": "failed",
                    "note": "PRIVATE_EXCEPTION_SENTINEL",
                    "arguments": {"path": "C:/Users/demo/private.dwg"},
                    "output": "PRIVATE_OUTPUT_SENTINEL",
                }],
            },
            {
                "id": "private-task-id-88",
                "status": "completed",
                "created_at": "2026-10-25T11:00:00Z",
                "finished_at": "2026-10-25T11:00:05Z",
                "command": "another private command",
                "result": "another private result",
                "steps": [],
                "actions": [{"name": "open_application", "status": "result_received"}],
            },
        ]
        report = build_safe_diagnostics(
            records,
            app_version="1.6.7",
            os_name="Windows",
            python_version="3.12.4",
            generated_at="2026-10-25T12:00:00Z",
        )
        serialized = json.dumps(report, ensure_ascii=False)

        self.assertEqual(report["summary"]["task_count"], 2)
        self.assertEqual(report["summary"]["status_counts"]["failed"], 1)
        self.assertEqual(report["summary"]["status_counts"]["completed"], 1)
        self.assertEqual(report["summary"]["tool_action_status_counts"]["failed"], 1)
        self.assertEqual(report["summary"]["tool_action_status_counts"]["result_received"], 1)
        self.assertEqual(report["tasks"][0]["duration_seconds"], 180.0)
        self.assertEqual(report["runtime"]["operating_system_family"], "Windows")
        self.assertEqual(report["app_version"], "1.6.7")

        for secret in (
            "private-task-id-77",
            "PRIVATE_COMMAND_SENTINEL",
            "PRIVATE_RESULT_SENTINEL",
            "PRIVATE_PROGRESS_SENTINEL",
            "PRIVATE_TOOL_NAME_SENTINEL",
            "PRIVATE_EXCEPTION_SENTINEL",
            "PRIVATE_OUTPUT_SENTINEL",
            "/users/demo/secret.dwg",
            "C:/Users/demo/private.dwg",
            "confidential bill of quantities",
        ):
            self.assertNotIn(secret, serialized)

    def test_malformed_timestamps_and_unknown_statuses_are_safe(self) -> None:
        report = build_safe_diagnostics([{
            "status": "unexpected-status",
            "created_at": "not a timestamp",
            "finished_at": "also not a timestamp",
            "steps": ["not a step record"],
            "actions": [{"status": "future-action-state"}],
        }])
        self.assertEqual(report["summary"]["status_counts"]["unknown"], 1)
        self.assertEqual(report["summary"]["tool_action_status_counts"]["unknown"], 1)
        self.assertIsNone(report["tasks"][0]["created_date_utc"])
        self.assertIsNone(report["tasks"][0]["duration_seconds"])

    def test_export_is_bounded_and_does_not_mutate_input(self) -> None:
        records = [{"id": str(index), "status": "queued", "command": f"command-{index}"} for index in range(150)]
        snapshot = json.dumps(records, sort_keys=True)
        report = build_safe_diagnostics(records)
        self.assertEqual(report["summary"]["task_count"], 100)
        self.assertEqual(len(report["tasks"]), 100)
        self.assertEqual(json.dumps(records, sort_keys=True), snapshot)
        self.assertEqual(report["tasks"][0]["task_number"], 1)


if __name__ == "__main__":
    unittest.main()
