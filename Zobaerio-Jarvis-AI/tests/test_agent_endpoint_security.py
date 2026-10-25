from __future__ import annotations

import unittest
from unittest.mock import patch

from jarvis.agent import JarvisAgent


class AgentEndpointTransportTests(unittest.TestCase):
    def test_agent_blocks_remote_http_before_sending_stored_key(self) -> None:
        agent = JarvisAgent(
            {"api_base_url": "http://api.example.com/v1", "model": "model-a"},
            approval=lambda *_: True,
        )
        with patch("jarvis.agent.get_api_key", return_value="very-secret-key"), patch(
            "jarvis.agent.requests.post"
        ) as post:
            result = agent.respond("Explain how the desktop assistant plans tasks.")
        self.assertIn("HTTPS", result)
        self.assertNotIn("very-secret-key", result)
        post.assert_not_called()

    def test_agent_does_not_mistake_hostname_containing_localhost_for_loopback(self) -> None:
        agent = JarvisAgent(
            {"api_base_url": "https://localhost.example.com/v1", "model": "model-a"},
            approval=lambda *_: True,
        )
        with patch("jarvis.agent.get_api_key", return_value=""), patch(
            "jarvis.agent.requests.post"
        ) as post:
            result = agent.respond("Explain how the desktop assistant plans tasks.")
        self.assertIn("API key", result)
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
