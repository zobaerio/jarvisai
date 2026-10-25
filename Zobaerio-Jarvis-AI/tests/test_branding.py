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
                self.assertIn((32, 32), icon.info.get("sizes", set()) or {(32, 32)})

    def test_mark_remains_square_and_transparent_outside_badge(self) -> None:
        image = branding._paint_icon(128)
        self.assertEqual(image.size, (128, 128))
        self.assertEqual(image.mode, "RGBA")
        self.assertEqual(image.getpixel((0, 0))[3], 0)
        self.assertGreater(image.getpixel((64, 64))[3], 0)


if __name__ == "__main__":
    unittest.main()
