from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from jarvis.settings import (
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
