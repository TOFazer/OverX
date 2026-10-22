#!/usr/bin/env python3
"""Render the 1200x630 social preview cards used by og:image / twitter:image.

Pillow is the only dependency and it is *not* needed to build the site: the
generated PNGs are committed, so `build_site.py` stays dependency-free.

    python3 -m venv .venv && .venv/bin/pip install pillow
    .venv/bin/python scripts/build_og_images.py

Discord, X and Facebook do not read SVG previews, which is why these are PNGs.
All translucent shapes are drawn on overlay layers and composited, because
ImageDraw replaces pixels instead of blending when painting straight onto an
RGBA canvas.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - documented in the module docstring
    sys.exit("Pillow is required: .venv/bin/pip install pillow")

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "og"

WIDTH, HEIGHT = 1200, 630
BG = (9, 10, 17, 255)
PANEL = (21, 23, 35)
TEXT = (243, 243, 251)
SOFT = (168, 171, 188)
MUTED = (146, 150, 170)
VIOLET = (183, 161, 255)
VIOLET_DEEP = (142, 112, 218)
LIME = (185, 239, 140)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size)


def composite_shape(base: Image.Image, draw_on) -> ImageDraw.ImageDraw:
    """Give the caller a fresh transparent layer that is composited on exit."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw_on.append((base, layer))
    return ImageDraw.Draw(layer)


def flush(layers: list) -> None:
    for base, layer in layers:
        base.alpha_composite(layer)


def glow(base: Image.Image, center: tuple[int, int], radius: int, color: tuple[int, int, int], alpha: int) -> None:
    halo = Image.new("RGBA", (radius * 2, radius * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(halo)
    steps = 60
    for step in range(steps, 0, -1):
        size = int(radius * (step / steps))
        draw.ellipse(
            (radius - size, radius - size, radius + size, radius + size),
            fill=(*color, int(alpha * (1 - step / steps) ** 1.6)),
        )
    base.alpha_composite(halo, (center[0] - radius, center[1] - radius))


def dotted_grid(base: Image.Image) -> None:
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for x in range(28, WIDTH, 28):
        for y in range(28, HEIGHT, 28):
            fade = max(0.0, 1 - (y / HEIGHT) * 1.25)
            if fade <= 0.02:
                continue
            draw.ellipse((x, y, x + 2, y + 2), fill=(195, 198, 231, int(46 * fade)))
    base.alpha_composite(overlay)


def letterspaced(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.FreeTypeFont,
                 fill: tuple[int, int, int, int], spacing: int = 8) -> int:
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        x += int(draw.textlength(char, font=font)) + spacing
    return x


def fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, min_size: int = 34) -> ImageFont.FreeTypeFont:
    size = start_size
    while size > min_size:
        font = load_font(size)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size -= 4
    return load_font(min_size)


def truncate(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(text + "…", font=font) > max_width:
        text = text[:-1]
    return text + "…"


def render(path: Path, *, eyebrow: str, lines: list[str], lead: str, chips: list[str], mark: str, mark_sub: str) -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    glow(image, (1010, 60), 430, VIOLET_DEEP, 90)
    glow(image, (-40, 520), 380, (54, 119, 141), 70)
    dotted_grid(image)
    layers: list[tuple[Image.Image, Image.Image]] = []

    # Framed "Discord window" on the right, echoing the site's hero visual.
    card = composite_shape(image, layers)
    card.rounded_rectangle((760, 118, 1132, 512), radius=26, fill=(*PANEL, 235), outline=(232, 228, 255, 38), width=2)
    card.rounded_rectangle((792, 158, 1100, 236), radius=16, fill=(*VIOLET_DEEP, 255))
    mark_font = load_font(44)
    probe = ImageDraw.Draw(image)
    box = probe.textbbox((0, 0), mark, font=mark_font)
    card.text((946 - (box[2] - box[0]) / 2, 197 - (box[3] - box[1]) / 2 - box[1]), mark, font=mark_font, fill=(23, 19, 32, 255))
    sub_font = load_font(16)
    box = probe.textbbox((0, 0), mark_sub, font=sub_font)
    letterspaced(card, (int(946 - ((box[2] - box[0]) + 10 * (len(mark_sub) - 1)) / 2), 258), mark_sub, sub_font, (*MUTED, 255), 10)
    for index, chip in enumerate(chips[:3]):
        top = 300 + index * 58
        chip_font = load_font(18)
        label = truncate(card, chip, chip_font, 1100 - 842)
        card.rounded_rectangle((792, top, 1100, top + 44), radius=11, fill=(255, 255, 255, 14), outline=(235, 236, 255, 26), width=1)
        card.ellipse((812, top + 16, 824, top + 28), fill=(*LIME, 255))
        card.text((842, top + 11), label, font=chip_font, fill=(226, 229, 240, 255))

    # Left column: brand, headline, lead.
    draw = ImageDraw.Draw(image)
    eyebrow_font = load_font(21)
    letterspaced(draw, (78, 108), eyebrow, eyebrow_font, (*VIOLET, 255), 7)
    line_layer = composite_shape(image, layers)
    line_layer.line((78, 164, 210, 164), fill=(167, 139, 250, 140), width=2)

    y = 186
    for index, text in enumerate(lines):
        font = fit_font(draw, text, 640, 62)
        draw.text((76, y), text, font=font, fill=TEXT if index != len(lines) - 1 else VIOLET)
        y += 80

    lead_font = load_font(26)
    words, rows, current = lead.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=lead_font) > 610 and current:
            rows.append(current)
            current = word
        else:
            current = trial
    if current:
        rows.append(current)
    for row in rows[:2]:
        draw.text((78, y + 10), row, font=lead_font, fill=SOFT)
        y += 38

    # Bottom rule with the wordmark, mirroring the site footer.
    rule = composite_shape(image, layers)
    rule.line((78, 548, 1122, 548), fill=(235, 236, 255, 26), width=1)
    flush(layers)
    draw = ImageDraw.Draw(image)
    brand_font = load_font(24)
    letterspaced(draw, (78, 570), "OVERX", brand_font, (*TEXT, 255), 5)
    tag_font = load_font(17)
    letterspaced(draw, (200, 576), "APPLICATIONS & PROJETS", tag_font, (*MUTED, 255), 5)
    draw.ellipse((1096, 572, 1108, 584), fill=(*LIME, 255))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, "PNG", optimize=True)
    print(f"generated {path.relative_to(ROOT)}")


def main() -> None:
    render(
        OUT_DIR / "overx.png",
        eyebrow="LE POINT DE DÉPART",
        lines=["Des applications.", "Des projets.", "Un même univers."],
        lead="OverLoad pour Windows, FreeGameDrop pour Discord. Et les projets à venir.",
        chips=["OverLoad · Windows", "FreeGameDrop · Discord", "Nouveaux projets"],
        mark="O",
        mark_sub="OVERX",
    )
    render(
        OUT_DIR / "overload.png",
        eyebrow="OVERLOAD · WINDOWS",
        lines=["Télécharge.", "Analyse.", "Organise tes médias."],
        lead="Des liens directs aux projets vidéo, dans une application native Windows.",
        chips=["Liens HTTP(S) directs", "Analyse multimédia", "Espace Créateurs"],
        mark="OL",
        mark_sub="OVERLOAD",
    )
    render(
        OUT_DIR / "freegamedrop.png",
        eyebrow="FREEGAMEDROP · BOT DISCORD",
        lines=["Ne rate plus", "les jeux", "gratuits."],
        lead="Les offres Steam, Epic, GOG et Ubisoft annoncées sur ton serveur Discord.",
        chips=["Veille chaque heure", "Salons par plateforme", "Favoris et rappels"],
        mark="FGD",
        mark_sub="FREEGAMEDROP",
    )


if __name__ == "__main__":
    main()
