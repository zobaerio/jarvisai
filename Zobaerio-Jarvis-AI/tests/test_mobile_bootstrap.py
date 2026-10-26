from __future__ import annotations

import plistlib
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "mobile"))

from bootstrap_platforms import APP_DISPLAY_NAME, configure_display_names  # noqa: E402


class MobileBootstrapTests(unittest.TestCase):
    def test_configures_android_and_ios_display_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "android/app/src/main/AndroidManifest.xml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                '<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
                '<application android:label="jarvis_mobile" /></manifest>',
                encoding="utf-8",
            )
            info_plist = root / "ios/Runner/Info.plist"
            info_plist.parent.mkdir(parents=True)
            with info_plist.open("wb") as stream:
                plistlib.dump({"CFBundleDisplayName": "Runner", "CFBundleName": "jarvis_mobile"}, stream)

            configure_display_names(root)

            self.assertIn(f'android:label="{APP_DISPLAY_NAME}"', manifest.read_text(encoding="utf-8"))
            with info_plist.open("rb") as stream:
                values = plistlib.load(stream)
            self.assertEqual(values["CFBundleDisplayName"], APP_DISPLAY_NAME)
            self.assertEqual(values["CFBundleName"], "jarvis_mobile")

    def test_missing_host_projects_are_safe_to_configure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            configure_display_names(Path(temporary))


if __name__ == "__main__":
    unittest.main()
