from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from jarvis.settings import (
    auto_configure_from_api_key,
    is_local_api_endpoint,
    test_api_connection,
    validate_api_base_url,
    validate_api_key_transport,
)


class ApiEndpointValidationTests(unittest.TestCase):
    def test_accepts_local_and_https_endpoints(self) -> None:
        self.assertEqual(validate_api_base_url(" http://localhost:11434/v1/ "), "http://localhost:11434/v1")
        self.assertTrue(is_local_api_endpoint("http://localhost:11434/v1"))
        self.assertTrue(is_local_api_endpoint("http://127.0.0.2:8000/v1"))
        self.assertTrue(is_local_api_endpoint("http://[::1]:8000/v1"))
        self.assertFalse(is_local_api_endpoint("https://localhost.example.com/v1"))

    def test_normalizes_common_full_openrouter_endpoint_urls(self) -> None:
        self.assertEqual(
            validate_api_base_url("https://openrouter.ai/api/v1/chat/completions"),
            "https://openrouter.ai/api/v1",
        )
        self.assertEqual(
            validate_api_base_url("https://openrouter.ai/api/v1/models"),
            "https://openrouter.ai/api/v1",
        )
        self.assertEqual(
            validate_api_base_url("https://openrouter.ai/api/v1/"),
            "https://openrouter.ai/api/v1",
        )

    def test_rejects_embedded_credentials_query_fragment_and_bad_schemes(self) -> None:
        bad_values = [
            "ftp://api.example.com/v1",
            "https://user:secret@api.example.com/v1",
            "https://api.example.com/v1?token=secret",
            "https://api.example.com/v1#fragment",
            "https:///v1",
            "https://api.example.com:bad/v1",
        ]
        for value in bad_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_api_base_url(value)

    def test_blocks_api_key_over_remote_plain_http(self) -> None:
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            validate_api_key_transport("http://api.example.com/v1", "very-secret")
        self.assertEqual(
            validate_api_key_transport("http://localhost:11434/v1", "local-secret"),
            "http://localhost:11434/v1",
        )
        self.assertEqual(
            validate_api_key_transport("https://api.example.com/v1", "remote-secret"),
            "https://api.example.com/v1",
        )

    @patch("requests.get")
    def test_auto_setup_detects_openrouter_and_selects_preferred_model(self, get) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {"data": [{"id": "openai/gpt-4o-mini"}, {"id": "other-model"}]}
        get.return_value = response
        result = auto_configure_from_api_key("sk-or-v1-test-secret")
        self.assertEqual(result["provider"], "OpenRouter")
        self.assertEqual(result["api_base_url"], "https://openrouter.ai/api/v1")
        self.assertEqual(result["model"], "openai/gpt-4o-mini")
        get.assert_called_once_with(
            "https://openrouter.ai/api/v1/models",
            headers={"Accept": "application/json", "Authorization": "Bearer sk-or-v1-test-secret"},
            timeout=(3, 8.0),
        )

    @patch("requests.get")
    def test_auto_setup_detects_google_gemini_and_selects_available_model(self, get) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {"data": [{"id": "gemini-2.5-flash"}, {"id": "gemini-embedding-001"}]}
        get.return_value = response
        result = auto_configure_from_api_key("AIza-test-secret")
        self.assertEqual(result["provider"], "Google Gemini")
        self.assertEqual(result["api_base_url"], "https://generativelanguage.googleapis.com/v1beta/openai")
        self.assertEqual(result["model"], "gemini-2.5-flash")
        get.assert_called_once_with(
            "https://generativelanguage.googleapis.com/v1beta/openai/models",
            headers={"Accept": "application/json", "Authorization": "Bearer AIza-test-secret"},
            timeout=(3, 8.0),
        )


    @patch("requests.get")
    def test_auto_setup_fallback_skips_embedding_models(self, get) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {
            "data": [
                {"id": "gemini-embedding-001"},
                {"id": "gemini-2.5-pro-preview"},
                {"id": "text-embedding-3-large"},
            ]
        }
        get.return_value = response
        result = auto_configure_from_api_key("AIza-test-secret")
        self.assertEqual(result["model"], "gemini-2.5-pro-preview")

    @patch("requests.get")
    def test_auto_setup_rejects_catalog_without_recognizable_chat_model(self, get) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {"data": [{"id": "gemini-embedding-001"}]}
        get.return_value = response
        with self.assertRaisesRegex(ValueError, "no safely recognizable chat model"):
            auto_configure_from_api_key("AIza-test-secret")

    @patch("requests.get")
    def test_auto_setup_prefers_current_groq_models_over_retired_ids(self, get) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {
            "data": [
                {"id": "llama-3.3-70b-versatile"},
                {"id": "llama-3.1-8b-instant"},
                {"id": "openai/gpt-oss-120b"},
                {"id": "openai/gpt-oss-20b"},
            ]
        }
        get.return_value = response
        result = auto_configure_from_api_key("gsk_test-secret")
        self.assertEqual(result["provider"], "Groq")
        self.assertEqual(result["model"], "openai/gpt-oss-120b")
        self.assertEqual(result["api_base_url"], "https://api.groq.com/openai/v1")
        get.assert_called_once_with(
            "https://api.groq.com/openai/v1/models",
            headers={"Accept": "application/json", "Authorization": "Bearer gsk_test-secret"},
            timeout=(3, 8.0),
        )

    @patch("requests.get")
    def test_auto_setup_detects_xai_and_selects_available_grok_model(self, get) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {"data": [{"id": "grok-4.7"}, {"id": "grok-3-mini"}]}
        get.return_value = response
        result = auto_configure_from_api_key("xai-test-secret")
        self.assertEqual(result["provider"], "xAI")
        self.assertEqual(result["api_base_url"], "https://api.x.ai/v1")
        self.assertEqual(result["model"], "grok-4.7")
        get.assert_called_once_with(
            "https://api.x.ai/v1/models",
            headers={"Accept": "application/json", "Authorization": "Bearer xai-test-secret"},
            timeout=(3, 8.0),
        )

    @patch("requests.get")
    def test_auto_setup_never_probes_unknown_or_ambiguous_provider_keys(self, get) -> None:
        # Generic sk-* values overlap across providers (for example Anthropic and
        # legacy OpenAI-style keys); do not send them to an assumed provider.
        for key in ("unknown-provider-secret", "sk-ant-api03-test-secret", "sk-legacy-test-secret"):
            with self.subTest(key_prefix=key.split("-")[0]):
                with self.assertRaisesRegex(ValueError, "could not be identified safely"):
                    auto_configure_from_api_key(key)
        get.assert_not_called()

    @patch("requests.get")
    def test_auto_setup_handles_invalid_key_without_echoing_secret(self, get) -> None:
        get.return_value = Mock(status_code=401)
        with self.assertRaisesRegex(ValueError, "rejected this API key"):
            auto_configure_from_api_key("sk-or-v1-test-secret")
        get.assert_called_once()

    @patch("requests.get")
    def test_connection_check_uses_models_endpoint_and_matches_model(self, get) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {"data": [{"id": "model-a"}, {"id": "model-b"}]}
        get.return_value = response
        result = test_api_connection("https://api.example.com/v1/", "model-b", "test-key")
        self.assertTrue(result["ok"])
        self.assertTrue(result["model_available"])
        self.assertEqual(result["status_code"], 200)
        get.assert_called_once_with(
            "https://api.example.com/v1/models",
            headers={"Accept": "application/json", "Authorization": "Bearer test-key"},
            timeout=(3, 7.0),
        )

    @patch("requests.get")
    def test_connection_test_blocks_insecure_endpoint_before_network_call(self, get) -> None:
        result = test_api_connection("http://api.example.com/v1", "model-a", "test-key")
        self.assertFalse(result["ok"])
        self.assertIn("HTTPS", result["message"])
        get.assert_not_called()

    @patch("requests.get")
    def test_connection_test_handles_unauthorized_without_exposing_key(self, get) -> None:
        get.return_value = Mock(status_code=401)
        result = test_api_connection("https://api.example.com/v1", "model-a", "very-secret-key")
        self.assertFalse(result["ok"])
        self.assertIn("401", result["message"])
        self.assertNotIn("very-secret-key", result["message"])

    @patch("requests.get")
    def test_connection_check_does_not_generate_a_chat_completion(self, get) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {"data": [{"id": "qwen2.5:3b"}]}
        get.return_value = response
        result = test_api_connection("http://localhost:11434/v1", "qwen2.5:3b", "")
        self.assertTrue(result["ok"])
        self.assertIn("/models", get.call_args.args[0])
        self.assertNotIn("/chat/completions", get.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
