"""Generate only the standard Android/iOS host projects without overwriting app source."""
from __future__ import annotations

import plistlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PLATFORMS = ("android", "ios")
APP_DISPLAY_NAME = "ORVIX AI"


def configure_display_names(root: Path) -> None:
    """Set a user-facing app name in generated Android and iOS host projects."""
    manifest = root / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    if manifest.is_file():
        source = manifest.read_text(encoding="utf-8")
        updated, count = re.subn(
            r'android:label="[^"]+"',
            f'android:label="{APP_DISPLAY_NAME}"',
            source,
            count=1,
        )
        if count != 1:
            raise ValueError("Android manifest did not contain an app label")
        manifest.write_text(updated, encoding="utf-8")

    info_plist = root / "ios" / "Runner" / "Info.plist"
    if info_plist.is_file():
        with info_plist.open("rb") as stream:
            values = plistlib.load(stream)
        values["CFBundleDisplayName"] = APP_DISPLAY_NAME
        with info_plist.open("wb") as stream:
            plistlib.dump(values, stream, fmt=plistlib.FMT_XML, sort_keys=False)


def main() -> int:
    missing = [name for name in PLATFORMS if not (ROOT / name).exists()]
    if missing:
        with tempfile.TemporaryDirectory(prefix="orvix-mobile-hosts-") as temporary:
            generated = Path(temporary) / "jarvis_mobile"
            subprocess.run(
                [
                    "flutter",
                    "create",
                    "--platforms=android,ios",
                    "--project-name",
                    "jarvis_mobile",
                    str(generated),
                ],
                check=True,
            )
            for name in missing:
                source = generated / name
                destination = ROOT / name
                if not source.is_dir():
                    raise FileNotFoundError(
                        f"Flutter did not generate the expected {name}/ host project"
                    )
                shutil.copytree(source, destination)
                print(f"Created {destination.relative_to(ROOT)} host project.")
    else:
        print("Android and iOS host projects already exist.")

    configure_display_names(ROOT)
    print(f"Configured mobile app display name: {APP_DISPLAY_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
