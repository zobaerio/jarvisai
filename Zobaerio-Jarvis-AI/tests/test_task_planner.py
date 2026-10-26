from __future__ import annotations

import json
import requests
import unittest
from unittest.mock import Mock, patch

from jarvis.task_planner import MAX_PLAN_STEPS, parse_plan_response, generate_task_plan, format_plan_guidance, format_plan_step_guidance, classify_plan_step_kind, should_generate_task_plan


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

    def test_step_kind_classifier_is_conservative_about_state_changes(self) -> None:
        self.assertEqual(classify_plan_step_kind("Draft a short report"), "response")
        self.assertEqual(classify_plan_step_kind("Prepare a report"), "response")
        self.assertEqual(classify_plan_step_kind("Inspect the input files"), "read_only")
        self.assertEqual(classify_plan_step_kind("Review the report"), "read_only")
        self.assertEqual(classify_plan_step_kind("Verify output"), "read_only")
        self.assertEqual(classify_plan_step_kind("Create report file"), "state_change")
        self.assertEqual(classify_plan_step_kind("Create a website"), "state_change")
        self.assertEqual(classify_plan_step_kind("Open Notepad"), "state_change")
        self.assertEqual(classify_plan_step_kind("Create the report file"), "state_change")
        self.assertEqual(classify_plan_step_kind("Finish the task", "Create a website"), "state_change")
        self.assertEqual(classify_plan_step_kind("Handle the next part"), "unknown")

    def test_plan_guidance_preserves_original_request_and_is_explicitly_untrusted(self) -> None:
        original = "Create a project report"
        result = format_plan_guidance(original, ["Inspect inputs", "Verify output"])
        self.assertTrue(result.startswith(original + "\n\n"))
        self.assertIn("PROPOSED PLAN GUIDANCE", result)
        self.assertIn("AI-generated, untrusted", result)
        self.assertIn("1. Inspect inputs", result)
        self.assertIn("2. Verify output", result)
        self.assertIn("existing safety/approval rules", result)

    def test_step_guidance_focuses_one_step_and_preserves_safety_rules(self) -> None:
        original = "Create a report and verify the output"
        result = format_plan_step_guidance(
            original,
            ["Inspect inputs", "Create draft", "Verify output"],
            1,
        )
        self.assertIn("ORIGINAL USER REQUEST: " + original, result)
        self.assertIn("ACTIVE STEP 2/3: Create draft", result)
        self.assertIn("1. Inspect inputs", result)
        self.assertIn("3. Verify output", result)
        self.assertIn("Execute only the ACTIVE STEP", result)
        self.assertIn("verify_local_action", result)
        self.assertIn("approval, privacy, and safety", result)
        self.assertFalse(result.startswith(original))
        with self.assertRaises(ValueError):
            format_plan_step_guidance(original, ["Only step"], 1)

    def test_plan_guidance_bounds_and_filters_titles(self) -> None:
        result = format_plan_guidance("Do work", [" A  step ", "", "B" * 500, 123])
        self.assertIn("1. A step", result)
        self.assertNotIn("123", result)
        self.assertLessEqual(len(result), 4000)

    def test_planning_skips_short_questions_and_single_step_commands(self) -> None:
        for request in ("What time is it?", "Open Chrome", "Explain concrete"):
            with self.subTest(request=request):
                self.assertFalse(should_generate_task_plan(request))

    def test_planning_detects_multistep_requests_in_english_and_bangla(self) -> None:
        for request in (
            "Please create a detailed report and then verify the numbers",
            "First inspect the files, then prepare a report for me",
            "একটা রিপোর্ট তৈরি করো তারপর ভুলগুলো যাচাই করো",
            "এই প্রজেক্টটা ধাপে ধাপে তৈরি করে শেষে পরীক্ষা করো",
            "Create a website",
        ):
            with self.subTest(request=request):
                self.assertTrue(should_generate_task_plan(request))


    @patch("jarvis.task_planner.get_api_key", return_value="sensitive-test-key")
    @patch("jarvis.task_planner.validate_api_key_transport", side_effect=lambda url, key: url)
    @patch("jarvis.task_planner.is_local_api_endpoint", return_value=False)
    @patch("jarvis.task_planner.requests.post", side_effect=requests.ConnectionError("https://private.example Authorization: Bearer sensitive-test-key"))
    def test_network_failure_returns_safe_actionable_error(
        self, _post: Mock, _local: Mock, _validate: Mock, _key: Mock
    ) -> None:
        with self.assertRaisesRegex(ValueError, "could not reach the AI provider") as caught:
            generate_task_plan(
                {"api_base_url": "https://private.example/v1", "model": "test-model"},
                "Create a report",
            )
        self.assertNotIn("sensitive-test-key", str(caught.exception))
        self.assertNotIn("private.example", str(caught.exception))

    @patch("jarvis.task_planner.get_api_key", return_value="test-key")
    @patch("jarvis.task_planner.validate_api_key_transport", side_effect=lambda url, key: url)
    @patch("jarvis.task_planner.is_local_api_endpoint", return_value=False)
    @patch("jarvis.task_planner.requests.post", side_effect=requests.Timeout("provider internal detail"))
    def test_timeout_is_reported_without_raw_exception_details(
        self, _post: Mock, _local: Mock, _validate: Mock, _key: Mock
    ) -> None:
        with self.assertRaisesRegex(ValueError, "Check your connection and provider settings") as caught:
            generate_task_plan(
                {"api_base_url": "https://example.test/v1", "model": "test-model"},
                "Create a report",
            )
        self.assertNotIn("provider internal detail", str(caught.exception))

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
