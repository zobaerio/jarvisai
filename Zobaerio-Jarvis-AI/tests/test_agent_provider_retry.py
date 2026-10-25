from __future__ import annotations

import threading
import unittest
from unittest.mock import Mock, patch

import requests

from jarvis.agent import _post_with_bounded_retry


class ProviderRetryTests(unittest.TestCase):
    @staticmethod
    def response(status_code: int, headers: dict[str, str] | None = None) -> Mock:
        result = Mock()
        result.status_code = status_code
        result.headers = headers or {}
        return result

    def post(self, *, cancel_event=None, progress=None, max_attempts=3):
        return _post_with_bounded_retry(
            "https://provider.example/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            payload={"model": "test-model", "messages": []},
            timeout=(1, 2),
            cancel_event=cancel_event,
            progress=progress,
            max_attempts=max_attempts,
        )

    def test_retries_transient_http_status_then_returns_success(self) -> None:
        unavailable = self.response(503)
        success = self.response(200)
        progress: list[str] = []
        with patch("jarvis.agent.requests.post", side_effect=[unavailable, success]) as post, patch(
            "jarvis.agent.time.sleep"
        ) as sleep:
            result = self.post(progress=progress.append)
        self.assertIs(result, success)
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(0.5)
        self.assertIn("HTTP 503", progress[0])
        self.assertNotIn("provider.example", progress[0])

    def test_honors_numeric_retry_after_when_within_small_wait_budget(self) -> None:
        limited = self.response(429, {"Retry-After": "1.25"})
        success = self.response(200)
        with patch("jarvis.agent.requests.post", side_effect=[limited, success]) as post, patch(
            "jarvis.agent.time.sleep"
        ) as sleep:
            result = self.post()
        self.assertIs(result, success)
        post.assert_has_calls([unittest.mock.call(
            "https://provider.example/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={"model": "test-model", "messages": []},
            timeout=(1, 2),
        )] * 2)
        sleep.assert_called_once_with(1.25)

    def test_does_not_retry_when_retry_after_exceeds_wait_budget(self) -> None:
        limited = self.response(429, {"Retry-After": "60"})
        with patch("jarvis.agent.requests.post", return_value=limited) as post, patch(
            "jarvis.agent.time.sleep"
        ) as sleep:
            result = self.post()
        self.assertIs(result, limited)
        post.assert_called_once()
        sleep.assert_not_called()

    def test_non_retryable_status_returns_immediately(self) -> None:
        unauthorized = self.response(401)
        with patch("jarvis.agent.requests.post", return_value=unauthorized) as post, patch(
            "jarvis.agent.time.sleep"
        ) as sleep:
            result = self.post()
        self.assertIs(result, unauthorized)
        post.assert_called_once()
        sleep.assert_not_called()

    def test_exhausts_exactly_three_attempts_without_hiding_final_response(self) -> None:
        unavailable = self.response(503)
        with patch("jarvis.agent.requests.post", return_value=unavailable) as post, patch(
            "jarvis.agent.time.sleep"
        ) as sleep:
            result = self.post()
        self.assertIs(result, unavailable)
        self.assertEqual(post.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.5, 1.0])

    def test_retries_a_connection_failure_before_any_tool_execution(self) -> None:
        success = self.response(200)
        with patch(
            "jarvis.agent.requests.post",
            side_effect=[requests.exceptions.ConnectionError("details must not be logged"), success],
        ) as post, patch("jarvis.agent.time.sleep") as sleep:
            result = self.post()
        self.assertIs(result, success)
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(0.5)

    def test_cancellation_during_backoff_prevents_another_request(self) -> None:
        cancellation = threading.Event()
        transient = self.response(503)
        progress: list[str] = []
        with patch("jarvis.agent.requests.post", side_effect=lambda *_args, **_kwargs: (cancellation.set(), transient)[1]) as post:
            result = self.post(cancel_event=cancellation, progress=progress.append)
        self.assertIsNone(result)
        post.assert_called_once()
        self.assertEqual(len(progress), 1)

    def test_invalid_attempt_budget_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.post(max_attempts=0)


if __name__ == "__main__":
    unittest.main()
