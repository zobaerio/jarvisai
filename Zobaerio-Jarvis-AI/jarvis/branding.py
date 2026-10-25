"""Generate and install J.A.R.V.I.S brand assets without external image dependencies."""
from __future__ import annotations

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
    scale = size / 512
    def pt(value: float) -> int:
        return round(value * scale)

    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    art = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(art)
    navy = (5, 9, 21, 255)
    dark_blue = (20, 43, 69, 255)
    cyan = (34, 211, 238, 255)
    blue = (37, 99, 235, 255)
    orange = (249, 115, 22, 255)
    pale = (165, 243, 252, 255)

    d.rounded_rectangle((pt(10), pt(10), pt(502), pt(502)), radius=pt(116), fill=navy, outline=(26, 69, 105, 255), width=max(1, pt(4)))
    d.ellipse((pt(66), pt(66), pt(446), pt(446)), outline=(12, 52, 84, 255), width=max(1, pt(2)))
    d.ellipse((pt(85), pt(85), pt(427), pt(427)), outline=(30, 130, 190, 255), width=max(1, pt(7)))
    d.ellipse((pt(109), pt(109), pt(403), pt(403)), outline=(28, 84, 125, 255), width=max(1, pt(2)))
    d.arc((pt(80), pt(80), pt(432), pt(432)), start=205, end=282, fill=orange, width=max(1, pt(11)))
    d.arc((pt(80), pt(80), pt(432), pt(432)), start=12, end=76, fill=cyan, width=max(1, pt(8)))
    # Circuit traces and nodes.
    for points in [
        [(pt(95), pt(215)), (pt(144), pt(215)), (pt(165), pt(195)), (pt(187), pt(195))],
        [(pt(90), pt(250)), (pt(131), pt(250)), (pt(151), pt(230)), (pt(181), pt(230))],
        [(pt(104), pt(285)), (pt(145), pt(285)), (pt(164), pt(266)), (pt(185), pt(266))],
    ]:
        d.line(points, fill=cyan, width=max(1, pt(7)), joint="curve")
    for x, y in [(192, 195), (187, 230), (190, 266)]:
        d.ellipse((pt(x-7), pt(y-7), pt(x+7), pt(y+7)), fill=cyan)
    # Geometric J monogram: a thick curved hook with a strong vertical stem.
    outline = [(pt(224),pt(132)),(pt(300),pt(132)),(pt(300),pt(291)),(pt(297),pt(316)),(pt(287),pt(335)),(pt(270),pt(345)),(pt(248),pt(345)),(pt(226),pt(337)),(pt(209),pt(322)),(pt(198),pt(313)),(pt(221),pt(293)),(pt(233),pt(307)),(pt(248),pt(315)),(pt(262),pt(309)),(pt(267),pt(287)),(pt(267),pt(166)),(pt(224),pt(166))]
    d.polygon(outline, fill=cyan)
    d.line(outline + [outline[0]], fill=pale, width=max(1, pt(3)), joint="curve")
    # Orange orbit under the mark.
    d.arc((pt(126), pt(318), pt(395), pt(439)), start=12, end=167, fill=orange, width=max(1, pt(10)))
    d.ellipse((pt(381), pt(136), pt(399), pt(154)), fill=(251,191,36,255))
    d.ellipse((pt(402), pt(157), pt(410), pt(165)), fill=cyan)
    d.ellipse((pt(117), pt(339), pt(127), pt(349)), fill=orange)
    # Soft glow layered behind line art.
    glow = art.filter(ImageFilter.GaussianBlur(radius=max(1, pt(8))))
    base.alpha_composite(glow)
    base.alpha_composite(art)
    return base


def ensure_brand_assets() -> BrandAssets:
    """Create a PNG logo and multi-size Windows ICO in the per-user app-data folder."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    png_path = APP_DIR / "jarvis_logo.png"
    ico_path = APP_DIR / "jarvis.ico"
    image = _paint_icon(512)
    image.save(png_path, format="PNG", optimize=True)
    image.save(ico_path, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return BrandAssets(png=png_path, ico=ico_path)


def main() -> None:
    assets = ensure_brand_assets()
    print(f"J.A.R.V.I.S logo generated: {assets.png}")
    print(f"Windows icon generated: {assets.ico}")


if __name__ == "__main__":
    main()
