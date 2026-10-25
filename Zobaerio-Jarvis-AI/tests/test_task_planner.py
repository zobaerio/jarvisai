from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, patch

from jarvis.task_planner import MAX_PLAN_STEPS, parse_plan_response, generate_task_plan


def response_with(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


class TaskPlannerTests(unittest.TestCase):
    def test_parses_ordered_step_titles_and_deduplicates_case_insensitively(self) -> None:
        result = parse_plan_response(response_with(json.dumps({
            "steps": [" Inspect request ", "Create draft", "inspect request", "Verify output"]
        })))
        self.assertEqual(result, ["Inspect request", "Create draft", "Verify output"])

    def test_accepts_json_code_fence(self) -> None:
        result = parse_plan_response(response_with(' ```json\n{"steps":["First","Second"]}\n``` '))
        self.assertEqual(result, ["First", "Second"])

    def test_rejects_malformed_or_unbounded_responses(self) -> None:
        for payload in (
            None,
            {},
            {"choices": []},
            response_with("not json"),
            response_with('{"steps":[]}'),
            response_with(json.dumps({"steps": ["x"] * (MAX_PLAN_STEPS + 1)})),
            response_with(json.dumps({"steps": ["x" * 181]})),
            response_with(json.dumps({"steps": ["ok", 42]})),
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                parse_plan_response(payload)

    @patch("jarvis.task_planner.requests.post")
    @patch("jarvis.task_planner.get_api_key", return_value="test-key")
    @patch("jarvis.task_planner.validate_api_key_transport", side_effect=lambda url, key: url)
    @patch("jarvis.task_planner.is_local_api_endpoint", return_value=False)
    def test_generation_sends_no_tools_and_bounds_timeout(
        self, _local: Mock, _validate: Mock, _key: Mock, post: Mock
    ) -> None:
        post.return_value.status_code = 200
        post.return_value.json.return_value = response_with('{"steps":["Inspect","Verify"]}')
        result = generate_task_plan(
            {"api_base_url": "https://example.test/v1", "model": "test-model"},
            "  Make   a report  ",
        )
        self.assertEqual(result, ["Inspect", "Verify"])
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["timeout"], (8, 25))
        self.assertNotIn("tools", kwargs["json"])
        self.assertEqual(kwargs["json"]["messages"][1]["content"], "Make a report")

    def test_cancellation_avoids_network_request(self) -> None:
        import threading
        event = threading.Event()
        event.set()
        with self.assertRaises(InterruptedError), patch("jarvis.task_planner.requests.post") as post:
            generate_task_plan(
                {"api_base_url": "http://localhost:11434/v1", "model": "test"},
                "Do work",
                cancel_event=event,
            )
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
