from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from jarvis import agent, automation


class CalendarEventDraftTests(unittest.TestCase):
    def test_valid_event_opens_prefilled_template_without_saving(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            result = automation.prepare_calendar_event_draft(
                "Site inspection & review", "2026-10-26T14:30", "2026-10-26T15:30",
                "Bring drawings\nReview BBS", "Satkhira site", "Asia/Dhaka"
            )
        open_url.assert_called_once()
        parsed = urlparse(open_url.call_args.args[0])
        params = parse_qs(parsed.query)
        self.assertEqual(parsed.netloc, "calendar.google.com")
        self.assertEqual(params["action"], ["TEMPLATE"])
        self.assertEqual(params["text"], ["Site inspection & review"])
        self.assertEqual(params["dates"], ["20261026T143000/20261026T153000"])
        self.assertEqual(params["ctz"], ["Asia/Dhaka"])
        self.assertIn("Nothing was saved", result)

    def test_invalid_dates_are_rejected(self) -> None:
        cases = [
            ("not-a-date", "2026-10-26T15:30"),
            ("2026-10-26T15:30", "2026-10-26T14:30"),
            ("2026-10-26T14:30+06:00", "2026-10-26T15:30+06:00"),
            ("2026-10-26T14:30", "2026-11-04T14:30"),
        ]
        for start, end in cases:
            with self.subTest(start=start, end=end), patch("jarvis.automation.webbrowser.open") as open_url:
                result = automation.prepare_calendar_event_draft("Review", start, end)
                open_url.assert_not_called()
                self.assertIn("blocked", result)

    def test_limits_and_timezone_allow_list(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            empty = automation.prepare_calendar_event_draft("  ", "2026-10-26T14:30", "2026-10-26T15:30")
            bad_zone = automation.prepare_calendar_event_draft("Review", "2026-10-26T14:30", "2026-10-26T15:30", timezone_name="../../etc")
            too_long = automation.prepare_calendar_event_draft("Review", "2026-10-26T14:30", "2026-10-26T15:30", details="x" * 4001)
        open_url.assert_not_called()
        self.assertIn("title", empty)
        self.assertIn("timezone", bad_zone)
        self.assertIn("4,000", too_long)

    def test_agent_dispatch_and_schema(self) -> None:
        jarvis_agent = agent.JarvisAgent({}, lambda _title, _details: True)
        with patch("jarvis.agent.automation.prepare_calendar_event_draft", return_value="draft opened") as draft:
            result = jarvis_agent._execute_tool("prepare_calendar_event_draft", {
                "title": "Review", "start": "2026-10-26T14:30", "end": "2026-10-26T15:30"
            })
        self.assertEqual(result, "draft opened")
        draft.assert_called_once_with("Review", "2026-10-26T14:30", "2026-10-26T15:30", "", "", "Asia/Dhaka")
        tool = next(item["function"] for item in agent.TOOLS if item["function"]["name"] == "prepare_calendar_event_draft")
        self.assertEqual(tool["parameters"]["required"], ["title", "start", "end"])


if __name__ == "__main__":
    unittest.main()
