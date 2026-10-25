from __future__ import annotations

import unittest
from unittest.mock import patch

from jarvis import automation


class SocialWebNavigationTests(unittest.TestCase):
    def test_social_site_aliases_open_official_sites(self) -> None:
        cases = {
            "WhatsApp": "https://web.whatsapp.com/",
            "হোয়াটসঅ্যাপ": "https://web.whatsapp.com/",
            "Facebook": "https://www.facebook.com/",
            "ফেসবুক": "https://www.facebook.com/",
            "YouTube": "https://www.youtube.com/",
            "ইউটিউব": "https://www.youtube.com/",
            "Instagram": "https://www.instagram.com/",
            "Messenger": "https://www.messenger.com/",
        }
        for spoken_name, expected_url in cases.items():
            with self.subTest(spoken_name=spoken_name), patch("jarvis.automation.webbrowser.open") as open_url:
                result = automation.open_website(spoken_name)
                open_url.assert_called_once_with(expected_url)
                self.assertIn("Opened", result)

    def test_google_workspace_aliases_open_official_sites(self) -> None:
        cases = {
            "Gmail": "https://mail.google.com/",
            "জিমেইল": "https://mail.google.com/",
            "Google Calendar": "https://calendar.google.com/",
            "ক্যালেন্ডার": "https://calendar.google.com/",
            "Google Drive": "https://drive.google.com/",
            "গুগল ড্রাইভ": "https://drive.google.com/",
            "Google Docs": "https://docs.google.com/",
            "Google Sheets": "https://sheets.google.com/",
            "Google Maps": "https://maps.google.com/",
        }
        for spoken_name, expected_url in cases.items():
            with self.subTest(spoken_name=spoken_name), patch("jarvis.automation.webbrowser.open") as open_url:
                result = automation.open_website(spoken_name)
                open_url.assert_called_once_with(expected_url)
                self.assertIn("Opened", result)

    def test_direct_command_opens_workspace_alias_without_ai(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            result = automation.direct_command("open gmail")
        open_url.assert_called_once_with("https://mail.google.com/")
        self.assertIn("Opened", result)

    def test_english_youtube_search_opens_youtube_results(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            result = automation.open_website("search YouTube for Bangla natok")
        open_url.assert_called_once_with(
            "https://www.youtube.com/results?search_query=Bangla%20natok"
        )
        self.assertIn("Searched YouTube for: Bangla natok", result)

    def test_bangla_youtube_search_opens_youtube_results(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            result = automation.open_website("ইউটিউবে বাংলা নাটক সার্চ করো")
        open_url.assert_called_once_with(
            "https://www.youtube.com/results?search_query=%E0%A6%AC%E0%A6%BE%E0%A6%82%E0%A6%B2%E0%A6%BE%20%E0%A6%A8%E0%A6%BE%E0%A6%9F%E0%A6%95"
        )
        self.assertIn("বাংলা নাটক", result)

    def test_plain_search_remains_google_search(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            result = automation.open_website("weather in Khulna")
        open_url.assert_called_once_with(
            "https://www.google.com/search?q=weather%20in%20Khulna"
        )
        self.assertIn("Searched the web", result)

    def test_empty_input_does_not_open_a_browser(self) -> None:
        with patch("jarvis.automation.webbrowser.open") as open_url:
            result = automation.open_website("   ")
        open_url.assert_not_called()
        self.assertIn("Tell me a website", result)


if __name__ == "__main__":
    unittest.main()
