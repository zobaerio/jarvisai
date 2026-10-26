from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from jarvis import branding


class BrandingTests(unittest.TestCase):
    def test_brand_assets_are_generated_in_app_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(branding, "APP_DIR", Path(directory)):
                assets = branding.ensure_brand_assets()
            self.assertTrue(assets.png.is_file())
            self.assertTrue(assets.ico.is_file())
            with Image.open(assets.png) as logo:
                self.assertEqual(logo.format, "PNG")
                self.assertEqual(logo.size, (512, 512))
                self.assertEqual(logo.mode, "RGBA")
            with Image.open(assets.ico) as icon:
                self.assertEqual(icon.format, "ICO")
                self.assertGreater(icon.size[0], 0)
                self.assertGreater(icon.size[1], 0)

    def test_mark_remains_square_and_transparent_outside_badge(self) -> None:
        image = branding._paint_icon(128)
        self.assertEqual(image.size, (128, 128))
        self.assertEqual(image.mode, "RGBA")
        self.assertEqual(image.getpixel((0, 0))[3], 0)
        self.assertGreater(image.getpixel((64, 64))[3], 0)

    def test_generation_failure_preserves_existing_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory)
            png_path = app_dir / "jarvis_logo.png"
            ico_path = app_dir / "jarvis.ico"
            png_path.write_bytes(b"existing-png")
            ico_path.write_bytes(b"existing-ico")

            with patch.object(branding, "APP_DIR", app_dir), patch.object(
                branding, "_paint_icon", side_effect=RuntimeError("simulated render failure")
            ):
                with self.assertRaisesRegex(RuntimeError, "simulated render failure"):
                    branding.ensure_brand_assets()

            self.assertEqual(png_path.read_bytes(), b"existing-png")
            self.assertEqual(ico_path.read_bytes(), b"existing-ico")
            self.assertEqual(list(app_dir.glob("*.tmp.*")), [])

    def test_save_failure_does_not_replace_existing_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory)
            png_path = app_dir / "jarvis_logo.png"
            ico_path = app_dir / "jarvis.ico"
            png_path.write_bytes(b"existing-png")
            ico_path.write_bytes(b"existing-ico")

            original_save = Image.Image.save

            def fail_on_ico(image, fp, format=None, **kwargs):
                if format == "ICO":
                    raise OSError("simulated icon save failure")
                return original_save(image, fp, format=format, **kwargs)

            with patch.object(branding, "APP_DIR", app_dir), patch.object(
                Image.Image, "save", new=fail_on_ico
            ):
                with self.assertRaisesRegex(OSError, "simulated icon save failure"):
                    branding.ensure_brand_assets()

            self.assertEqual(png_path.read_bytes(), b"existing-png")
            self.assertEqual(ico_path.read_bytes(), b"existing-ico")
            self.assertEqual(list(app_dir.glob("*.tmp.*")), [])


if __name__ == "__main__":
    unittest.main()
