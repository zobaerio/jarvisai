"""Generate and install J.A.R.V.I.S brand assets without external image dependencies."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import NamedTuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .settings import APP_DIR


class BrandAssets(NamedTuple):
    png: Path
    ico: Path


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _paint_icon(size: int = 512) -> Image.Image:
    """Draw the ORVIX AI app icon using Pillow, with no external asset dependency."""
    scale = size / 512
    def pt(value: float) -> int:
        return round(value * scale)

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    navy = (6, 19, 41, 255)
    cyan = (6, 182, 212, 255)
    blue = (37, 99, 235, 255)
    orange = (249, 115, 22, 255)
    d.rounded_rectangle((pt(10), pt(10), pt(502), pt(502)), radius=pt(112), fill=navy)
    # Open orbital O: deliberate gap on the right, plus an orange trajectory.
    d.arc((pt(86), pt(86), pt(426), pt(426)), start=48, end=312, fill=cyan, width=max(1, pt(34)))
    d.arc((pt(86), pt(86), pt(426), pt(426)), start=312, end=405, fill=blue, width=max(1, pt(34)))
    d.arc((pt(112), pt(112), pt(400), pt(400)), start=210, end=320, fill=orange, width=max(1, pt(12)))
    # Forward-moving intelligence spark.
    d.polygon([
        (pt(211), pt(291)), (pt(276), pt(176)), (pt(270), pt(245)),
        (pt(326), pt(220)), (pt(252), pt(337)), (pt(258), pt(270)),
    ], fill=(230, 250, 255, 255))
    d.ellipse((pt(362), pt(112), pt(386), pt(136)), fill=orange)
    d.ellipse((pt(386), pt(137), pt(398), pt(149)), fill=cyan)
    return image

def ensure_brand_assets() -> BrandAssets:
    """Generate both assets in temporary files before atomically replacing installed copies."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    png_path = APP_DIR / "jarvis_logo.png"
    ico_path = APP_DIR / "jarvis.ico"
    token = uuid.uuid4().hex
    temp_png = APP_DIR / f".jarvis_logo.{token}.tmp.png"
    temp_ico = APP_DIR / f".jarvis_icon.{token}.tmp.ico"
    try:
        image = _paint_icon(512)
        image.save(temp_png, format="PNG", optimize=True)
        image.save(temp_ico, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        # Do not truncate the existing working assets if image generation fails.
        os.replace(temp_png, png_path)
        os.replace(temp_ico, ico_path)
    finally:
        for temporary in (temp_png, temp_ico):
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
    return BrandAssets(png=png_path, ico=ico_path)


def main() -> None:
    assets = ensure_brand_assets()
    print(f"J.A.R.V.I.S logo generated: {assets.png}")
    print(f"Windows icon generated: {assets.ico}")


if __name__ == "__main__":
    main()
