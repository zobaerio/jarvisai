from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from jarvis.health import collect_system_health, summarize_system_health


class SystemHealthCheckTests(unittest.TestCase):
    def make_assets(self, root: Path) -> None:
        studio = root / "assets" / "avatar_studio.html"
        studio.parent.mkdir(parents=True, exist_ok=True)
        studio.write_text("<html></html>", encoding="utf-8")
        logo = root / "assets" / "branding" / "jarvis-mark.svg"
        logo.parent.mkdir(parents=True, exist_ok=True)
        logo.write_text("<svg></svg>", encoding="utf-8")

    def test_all_local_checks_pass_for_a_fully_configured_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_assets(root)
            report = collect_system_health(
                {"api_base_url": "http://127.0.0.1:11434/v1", "model": "qwen2.5:3b"},
                project_root=root,
                python_version=(3, 12, 4),
                os_name="Windows",
                frozen=True,
                module_available=lambda _name: True,
                local_endpoint=lambda _endpoint: True,
                api_key_resolver=lambda _settings: "",
            )
            self.assertEqual({item.status for item in report}, {"PASS"})
            self.assertEqual(summarize_system_health(report), {"overall": "PASS", "PASS": len(report), "WARN": 0, "FAIL": 0})

    def test_missing_core_asset_is_fail_and_missing_optional_modules_warn(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = collect_system_health(
                {},
                project_root=root,
                python_version=(3, 12, 4),
                os_name="Windows",
                frozen=True,
                module_available=lambda name: name == "requests",
            )
            by_component = {item.component: item for item in report}
            self.assertEqual(by_component["3D Character Studio"].status, "FAIL")
            self.assertEqual(by_component["Branding assets"].status, "WARN")
            self.assertEqual(by_component["Core dependencies"].status, "FAIL")
            self.assertEqual(by_component["Speech features"].status, "WARN")
            self.assertEqual(by_component["AI model configuration"].status, "WARN")
            self.assertEqual(summarize_system_health(report)["overall"], "FAIL")

    def test_health_output_never_contains_endpoint_url_or_key_material(self) -> None:
        secret = "PRIVATE_API_KEY_SENTINEL"
        report = collect_system_health(
            {
                "api_base_url": "https://provider.example/v1?token=" + secret,
                "model": "private-model-name",
                "api_key": secret,
            },
            python_version=(3, 12, 3),
            os_name="Windows",
            module_available=lambda _name: True,
            local_endpoint=lambda _endpoint: False,
            api_key_resolver=lambda source: source.get("api_key", ""),
        )
        serialized = json.dumps([item.__dict__ for item in report], ensure_ascii=False)
        self.assertNotIn("provider.example", serialized)
        self.assertNotIn(secret, serialized)
        self.assertNotIn("private-model-name", serialized)
        self.assertIn("configured", serialized)

    def test_cloud_endpoint_reports_missing_key_without_revealing_keyring_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = collect_system_health(
                {"api_base_url": "https://cloud.example/v1", "model": "cloud-model"},
                project_root=Path(directory),
                python_version=(3, 12, 3),
                os_name="Windows",
                frozen=True,
                module_available=lambda _name: True,
                local_endpoint=lambda _endpoint: False,
                api_key_resolver=lambda _settings: "",
            )
            key_check = next(item for item in report if item.component == "AI API key")
            self.assertEqual(key_check.status, "WARN")
            self.assertIn("not found", key_check.detail)


    def test_default_cloud_key_resolver_uses_secure_store_without_exposing_value(self) -> None:
        secret = "SECURE_KEY_SHOULD_NEVER_APPEAR"
        with patch("jarvis.settings.get_api_key", return_value=secret):
            report = collect_system_health(
                {"api_base_url": "https://cloud.example/v1", "model": "cloud-model"},
                python_version=(3, 12, 3),
                os_name="Windows",
                module_available=lambda _name: True,
                local_endpoint=lambda _endpoint: False,
            )
        key_check = next(item for item in report if item.component == "AI API key")
        self.assertEqual(key_check.status, "PASS")
        self.assertNotIn(secret, key_check.detail)

    def test_api_key_store_error_is_sanitized(self) -> None:
        secret = "PRIVATE_KEYRING_ERROR_SENTINEL"
        report = collect_system_health(
            {"api_base_url": "https://cloud.example/v1", "model": "model"},
            module_available=lambda _name: True,
            local_endpoint=lambda _endpoint: False,
            api_key_resolver=lambda _settings: (_ for _ in ()).throw(RuntimeError(secret)),
        )
        serialized = json.dumps([item.__dict__ for item in report], ensure_ascii=False)
        self.assertNotIn(secret, serialized)
        self.assertIn("AI API key", serialized)
        self.assertTrue(any(item.status == "WARN" for item in report if item.component == "AI API key"))

    def test_unusual_python_and_non_windows_platform_show_warn_not_exception(self) -> None:
        report = collect_system_health(
            {"api_base_url": "http://127.0.0.1:11434/v1", "model": "model"},
            python_version=(3, 11, 9),
            os_name="Linux",
            module_available=lambda _name: True,
        )
        by_component = {item.component: item for item in report}
        self.assertEqual(by_component["Python runtime"].status, "WARN")
        self.assertEqual(by_component["Desktop platform"].status, "WARN")
        self.assertEqual(summarize_system_health(report)["overall"], "WARN")


if __name__ == "__main__":
    unittest.main()
