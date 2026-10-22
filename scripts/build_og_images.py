#!/usr/bin/env python3
"""Render the 1200x630 social preview cards used by og:image / twitter:image.

Pillow is the only dependency and it is *not* needed to build the site: the
generated PNGs are committed, so `build_site.py` stays dependency-free.

    python3 -m venv .venv && .venv/bin/pip install pillow
    .venv/bin/python scripts/build_og_images.py
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
BG = (16, 23, 19, 255)      # #101713 — fond principal vert-noir profond
PANEL = (26, 38, 31)        # #1A261F — surface secondaire vert forêt
ACTION = (49, 94, 67)       # #315E43 — vert naturel d'action
ACCENT = (169, 199, 174)    # #A9C7AE — vert sauge
TEXT = (225, 232, 225)      # #E1E8E1 — texte clair non agressif
SOFT = (183, 197, 185)
MUTED = (143, 162, 147)

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


def composite_shape(base: Image.Image, draw_on: list) -> ImageDraw.ImageDraw:
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


def letterspaced(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    spacing: int = 7,
) -> int:
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
    glow(image, (980, 90), 420, ACTION, 82)
    glow(image, (80, 560), 340, PANEL, 120)
    layers: list[tuple[Image.Image, Image.Image]] = []

    card = composite_shape(image, layers)
    card.ellipse((812, 74, 1080, 342), outline=(*ACCENT, 26), width=1)
    card.rounded_rectangle((756, 118, 1130, 512), radius=24, fill=(*PANEL, 242), outline=(*ACCENT, 38), width=1)
    card.rounded_rectangle((788, 154, 1098, 232), radius=14, fill=(*ACTION, 255))
    mark_font = load_font(42)
    probe = ImageDraw.Draw(image)
    box = probe.textbbox((0, 0), mark, font=mark_font)
    card.text((943 - (box[2] - box[0]) / 2, 193 - (box[3] - box[1]) / 2 - box[1]), mark, font=mark_font, fill=(*TEXT, 255))
    sub_font = load_font(15)
    box = probe.textbbox((0, 0), mark_sub, font=sub_font)
    letterspaced(card, (int(943 - ((box[2] - box[0]) + 9 * (len(mark_sub) - 1)) / 2), 254), mark_sub, sub_font, (*ACCENT, 235), 9)
    for index, chip in enumerate(chips[:3]):
        top = 298 + index * 58
        chip_font = load_font(18)
        label = truncate(card, chip, chip_font, 1098 - 838)
        card.rounded_rectangle((788, top, 1098, top + 44), radius=10, fill=(16, 23, 19, 175), outline=(*ACCENT, 24), width=1)
        card.ellipse((808, top + 17, 818, top + 27), fill=(*ACCENT, 255))
        card.text((836, top + 11), label, font=chip_font, fill=(*TEXT, 255))

    draw = ImageDraw.Draw(image)
    eyebrow_font = load_font(20)
    letterspaced(draw, (78, 108), eyebrow, eyebrow_font, (*ACCENT, 255), 6)
    line_layer = composite_shape(image, layers)
    line_layer.line((78, 160, 198, 160), fill=(*ACCENT, 110), width=2)

    y = 184
    for index, text in enumerate(lines):
        font = fit_font(draw, text, 630, 62)
        draw.text((76, y), text, font=font, fill=TEXT if index != len(lines) - 1 else ACCENT)
        y += 80

    lead_font = load_font(25)
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
        y += 37

    rule = composite_shape(image, layers)
    rule.line((78, 548, 1122, 548), fill=(*ACCENT, 30), width=1)
    flush(layers)
    draw = ImageDraw.Draw(image)
    brand_font = load_font(23)
    letterspaced(draw, (78, 570), "OVERX", brand_font, (*TEXT, 255), 5)
    tag_font = load_font(16)
    letterspaced(draw, (200, 576), "STUDIO LOGICIEL INDÉPENDANT", tag_font, (*MUTED, 255), 4)
    draw.ellipse((1098, 573, 1108, 583), fill=(*ACCENT, 255))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, "PNG", optimize=True)
    print(f"generated {path.relative_to(ROOT)}")


def main() -> None:
    render(
        OUT_DIR / "overx.png",
        eyebrow="STUDIO LOGICIEL INDÉPENDANT",
        lines=["Des outils", "pensés", "pour vous."],
        lead="OverLoad pour Windows, FreeGameDrop pour Discord. Conçus avec soin.",
        chips=["OverLoad · Windows 11", "FreeGameDrop · Discord", "Atelier indépendant"],
        mark="OX",
        mark_sub="OVERX",
    )
    render(
        OUT_DIR / "overload.png",
        eyebrow="OVERLOAD · WINDOWS 11",
        lines=["Vos médias,", "téléchargés et", "prêts au montage."],
        lead="Liens directs HTTP(S), analyse FFprobe et Espace Créateurs natif.",
        chips=["Liens HTTP(S) directs", "Analyse FFprobe", "Espace Créateurs"],
        mark="OL",
        mark_sub="OVERLOAD",
    )
    render(
        OUT_DIR / "freegamedrop.png",
        eyebrow="FREEGAMEDROP · BOT DISCORD",
        lines=["Les jeux gratuits,", "annoncés", "sans bruit."],
        lead="Les offres Steam, Epic, GOG et Ubisoft triées par rôle sur votre serveur.",
        chips=["Veille chaque heure", "Salons par plateforme", "Favoris et rappels"],
        mark="FGD",
        mark_sub="FREEGAMEDROP",
    )


if __name__ == "__main__":
    main()
