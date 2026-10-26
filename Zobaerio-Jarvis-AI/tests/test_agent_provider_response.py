from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import requests

from jarvis.agent import JarvisAgent, _safe_provider_http_error


class SafeProviderResponseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test-model"},
            approval=lambda *_: True,
        )

    def _respond_with(self, response):
        with patch("jarvis.agent.get_api_key", return_value=""), patch(
            "jarvis.agent.requests.post", return_value=response
        ):
            return self.agent.respond("Analyze my private construction plan.")

    def test_provider_error_body_does_not_echo_private_prompt_or_credentials(self) -> None:
        response = Mock(status_code=500)
        response.text = "debug: API key=very-secret-token private prompt=construction plan"
        result = self._respond_with(response)
        self.assertIn("HTTP 500", result)
        self.assertIn("raw response body is hidden", result)
        self.assertNotIn("very-secret-token", result)
        self.assertNotIn("construction plan", result)
        self.assertNotIn(response.text, result)

    def test_auth_error_is_actionable_but_does_not_echo_response_body(self) -> None:
        response = Mock(status_code=401)
        response.text = "Invalid credential: very-secret-token"
        result = self._respond_with(response)
        self.assertIn("HTTP 401", result)
        self.assertNotIn("very-secret-token", result)
        self.assertNotIn(response.text, result)

    def test_non_object_json_does_not_crash_agent(self) -> None:
        response = Mock(status_code=200)
        response.json.return_value = ["unexpected", "payload"]
        result = self._respond_with(response)
        self.assertIn("invalid or unsupported response format", result)

    def test_malformed_choice_or_message_is_handled(self) -> None:
        malformed_payloads = [
            {"choices": ["not an object"]},
            {"choices": [{"message": "not an object"}]},
            {"choices": {}},
        ]
        for payload in malformed_payloads:
            with self.subTest(payload=payload):
                response = Mock(status_code=200)
                response.json.return_value = payload
                result = self._respond_with(response)
                self.assertIn("AI provider", result)

    def test_malformed_tool_call_is_rejected_before_any_tool_runs(self) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {
            "choices": [{"message": {"content": None, "tool_calls": [{"id": "bad-call", "function": "invalid"}]}}]
        }
        with patch("jarvis.agent.get_api_key", return_value=""), patch(
            "jarvis.agent.requests.post", return_value=response
        ), patch.object(self.agent, "_execute_tool") as execute:
            result = self.agent.respond("Please organize my files.")
        self.assertIn("malformed tool-call", result)
        execute.assert_not_called()

    def test_invalid_json_and_network_errors_are_safe(self) -> None:
        response = Mock(status_code=200)
        response.json.side_effect = ValueError("private response payload very-secret-token")
        result = self._respond_with(response)
        self.assertIn("invalid JSON", result)
        self.assertNotIn("very-secret-token", result)
        self.assertNotIn("private response payload", result)

        with patch("jarvis.agent.get_api_key", return_value=""), patch(
            "jarvis.agent.requests.post",
            side_effect=requests.RequestException("https://localhost: token=very-secret-token"),
        ):
            result = self.agent.respond("Analyze another private plan.")
        self.assertIn("AI request failed safely", result)
        self.assertNotIn("very-secret-token", result)
        self.assertNotIn("token=", result)

    def test_http_status_messages_cover_common_provider_failures(self) -> None:
        for code in (400, 401, 403, 404, 408, 413, 429, 500, 502, 503, 504, 599):
            with self.subTest(code=code):
                message = _safe_provider_http_error(code)
                self.assertIn(f"HTTP {code}", message)
                self.assertIn("raw response body is hidden", message)


    def test_successful_chat_completion_uses_configured_key_and_returns_answer(self) -> None:
        self.agent.settings = {
            "api_base_url": "https://api.example.test/v1",
            "model": "test-chat-model",
        }
        response = Mock(status_code=200)
        response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Hello from the mocked model."}}]
        }
        with patch("jarvis.agent.get_api_key", return_value="test-provider-secret"), patch(
            "jarvis.agent.requests.post", return_value=response
        ) as post:
            result = self.agent.respond("Say hello.")

        self.assertEqual(result, "Hello from the mocked model.")
        self.assertEqual(self.agent.last_outcome, "completed")
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.example.test/v1/chat/completions")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-provider-secret")
        self.assertEqual(kwargs["json"]["model"], "test-chat-model")
        self.assertEqual(kwargs["json"]["messages"][-1], {"role": "user", "content": "Say hello."})
        self.assertNotIn("test-provider-secret", result)


if __name__ == "__main__":
    unittest.main()
