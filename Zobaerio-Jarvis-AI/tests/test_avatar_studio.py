from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import urlparse
from urllib.request import urlopen

from jarvis import avatar_studio, automation


class AvatarStudioTests(unittest.TestCase):
    def tearDown(self) -> None:
        server = avatar_studio._SERVER
        if server is not None:
            server.shutdown()
            server.server_close()
            avatar_studio._SERVER = None

    def test_studio_is_loopback_only_and_serves_selected_character(self) -> None:
        with patch("jarvis.avatar_studio.webbrowser.open_new_tab", return_value=True) as open_browser:
            self.assertTrue(avatar_studio.launch_avatar_studio("ruby"))
        url = open_browser.call_args.args[0]
        parsed = urlparse(url)
        self.assertEqual(parsed.hostname, "127.0.0.1")
        self.assertTrue(parsed.port)
        self.assertIn("character=ruby", parsed.query)
        with urlopen(url, timeout=3) as response:
            html = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
        self.assertIn("J.A.R.V.I.S 3D CHARACTER STUDIO", html.upper())
        self.assertIn("CapsuleGeometry", html)
        self.assertIn("data-character=\"ruby\"", html)

    def test_studio_supports_local_glb_import_and_embedded_clips(self) -> None:
        project_root = Path(avatar_studio.__file__).resolve().parent.parent
        html = (project_root / "assets" / "avatar_studio.html").read_text(encoding="utf-8")
        self.assertIn('id="importBtn"', html)
        self.assertIn('accept=".glb,model/gltf-binary"', html)
        self.assertIn("new GLTFLoader()", html)
        self.assertIn("loader.parse(reader.result", html)
        self.assertIn("reader.readAsArrayBuffer(file)", html)
        self.assertIn("/wave|hello|gesture/i", html)
        self.assertIn("/talk|speak|talking/i", html)

    def test_unknown_character_falls_back_to_luna(self) -> None:
        with patch("jarvis.avatar_studio.webbrowser.open_new_tab", return_value=True) as open_browser:
            self.assertTrue(avatar_studio.launch_avatar_studio("anything-else"))
        url = open_browser.call_args.args[0]
        self.assertIn("character=luna", url)


class AutomationSafetyTests(unittest.TestCase):
    def test_user_file_names_cannot_escape_allowed_folder(self) -> None:
        with TemporaryDirectory() as tmp:
            fake_root = Path(tmp).resolve()
            with patch.dict(automation.ROOTS, {"downloads": fake_root}):
                self.assertEqual(automation.safe_child_path("Downloads", "report.txt"), fake_root / "report.txt")
                for unsafe in ("../outside.txt", "subdir/report.txt", "bad?.txt", "..", ""):
                    with self.subTest(name=unsafe), self.assertRaises(ValueError):
                        automation.safe_child_path("Downloads", unsafe)


if __name__ == "__main__":
    unittest.main()
