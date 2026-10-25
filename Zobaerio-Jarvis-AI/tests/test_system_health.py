from __future__ import annotations

import json
import tempfile
import unittest
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
        )
        serialized = json.dumps([item.__dict__ for item in report], ensure_ascii=False)
        self.assertNotIn("provider.example", serialized)
        self.assertNotIn(secret, serialized)
        self.assertNotIn("private-model-name", serialized)
        self.assertIn("configured", serialized)

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
