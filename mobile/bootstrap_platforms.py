"""Generate only the standard Android/iOS host projects without overwriting app source."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PLATFORMS = ("android", "ios")


def main() -> int:
    missing = [name for name in PLATFORMS if not (ROOT / name).exists()]
    if not missing:
        print("Android and iOS host projects already exist; nothing to do.")
        return 0

    with tempfile.TemporaryDirectory(prefix="jarvis-mobile-hosts-") as temporary:
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
                raise FileNotFoundError(f"Flutter did not generate the expected {name}/ host project")
            shutil.copytree(source, destination)
            print(f"Created {destination.relative_to(ROOT)} host project.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
