"""Regression tests for bounded AI-provider retry behavior."""

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import requests

from jarvis.agent import (
    _post_with_bounded_retry,
    _provider_retry_delay,
)


def response(status_code: int, headers: dict[str, str] | None = None):
    return SimpleNamespace(status_code=status_code, headers=headers or {})


class ProviderRetryTests(unittest.TestCase):
    def test_retries_transient_http_status_then_returns_success(self) -> None:
        transient = response(503)
        success = response(200)
        with (
            patch("jarvis.agent.requests.post", side_effect=[transient, success]) as post,
            patch("jarvis.agent._wait_before_provider_retry", return_value=True) as wait,
        ):
            result = _post_with_bounded_retry("https://provider.example/v1", headers={}, payload={})

        self.assertIs(result, success)
        self.assertEqual(post.call_count, 2)
        wait.assert_called_once()

    def test_does_not_retry_non_retryable_http_status(self) -> None:
        unauthorized = response(401)
        with (
            patch("jarvis.agent.requests.post", return_value=unauthorized) as post,
            patch("jarvis.agent._wait_before_provider_retry") as wait,
        ):
            result = _post_with_bounded_retry("https://provider.example/v1", headers={}, payload={})

        self.assertIs(result, unauthorized)
        post.assert_called_once()
        wait.assert_not_called()

    def test_does_not_retry_before_long_retry_after(self) -> None:
        rate_limited = response(429, {"Retry-After": "30"})
        self.assertIsNone(_provider_retry_delay(rate_limited, 1))
        with (
            patch("jarvis.agent.requests.post", return_value=rate_limited) as post,
            patch("jarvis.agent._wait_before_provider_retry") as wait,
        ):
            result = _post_with_bounded_retry("https://provider.example/v1", headers={}, payload={})

        self.assertIs(result, rate_limited)
        post.assert_called_once()
        wait.assert_not_called()

    def test_cancelled_request_does_not_send_http_request(self) -> None:
        cancel_event = threading.Event()
        cancel_event.set()
        with patch("jarvis.agent.requests.post") as post:
            result = _post_with_bounded_retry(
                "https://provider.example/v1",
                headers={},
                payload={},
                cancel_event=cancel_event,
            )

        self.assertIsNone(result)
        post.assert_not_called()

    def test_cancellation_during_backoff_prevents_next_attempt(self) -> None:
        cancel_event = threading.Event()
        transient = response(503)
        with (
            patch("jarvis.agent.requests.post", return_value=transient) as post,
            patch("jarvis.agent._wait_before_provider_retry", return_value=False),
        ):
            result = _post_with_bounded_retry(
                "https://provider.example/v1",
                headers={},
                payload={},
                cancel_event=cancel_event,
            )

        self.assertIsNone(result)
        post.assert_called_once()

    def test_connection_error_retries_only_within_attempt_budget(self) -> None:
        with (
            patch(
                "jarvis.agent.requests.post",
                side_effect=requests.exceptions.ConnectionError("private endpoint"),
            ) as post,
            patch("jarvis.agent._wait_before_provider_retry", return_value=True),
        ):
            with self.assertRaises(requests.exceptions.ConnectionError):
                _post_with_bounded_retry(
                    "https://provider.example/v1",
                    headers={},
                    payload={},
                    max_attempts=3,
                )

        self.assertEqual(post.call_count, 3)

    def test_rejects_empty_retry_budget(self) -> None:
        with self.assertRaises(ValueError):
            _post_with_bounded_retry(
                "https://provider.example/v1",
                headers={},
                payload={},
                max_attempts=0,
            )


if __name__ == "__main__":
    unittest.main()
