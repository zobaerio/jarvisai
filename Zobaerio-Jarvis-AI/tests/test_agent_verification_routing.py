from __future__ import annotations

import unittest
from unittest.mock import patch

from jarvis.agent import JarvisAgent, SYSTEM_PROMPT, TOOLS


class VerificationToolRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = JarvisAgent(
            {"api_base_url": "http://localhost:11434/v1", "model": "test"},
            approval=lambda _title, _message: False,
        )

    def test_agent_routes_verification_to_automation(self) -> None:
        with patch("jarvis.agent.automation.verify_local_action", return_value="Verified file exists") as verify:
            result = self.agent._execute_tool(
                "verify_local_action",
                {"kind": "file", "target": "report.md", "location": "Documents"},
            )
        self.assertEqual(result, "Verified file exists")
        verify.assert_called_once_with("file", "report.md", "Documents")

    def test_verification_tool_is_advertised_to_the_model(self) -> None:
        names = {
            tool["function"]["name"]
            for tool in TOOLS
            if tool.get("type") == "function" and "function" in tool
        }
        self.assertIn("verify_local_action", names)

    def test_agent_prompt_requires_execution_and_honest_verification(self) -> None:
        self.assertIn("complete supported user requests", SYSTEM_PROMPT)
        self.assertIn("partially completed", SYSTEM_PROMPT)
        self.assertIn("verify_local_action", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
