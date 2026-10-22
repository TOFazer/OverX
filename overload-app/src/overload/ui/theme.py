"""Système de design centralisé d'OverLoad — identité partagée OverX Studio.

Palette maîtresse OverX Studio (partagée avec le site OverX) :
- Fond principal (`OVERX_BG` / `FOREST_PINE`)       : `#101713`
- Surfaces (`OVERX_SURFACE` / `FOREST_CHARCOAL`)    : `#1A261F`
- Vert forêt d'action (`OVERX_ACTION` / `FOREST_BRAND`) : `#315E43`
- Accent sauge (`OVERX_SAGE` / `FOREST_SAGE`)       : `#A9C7AE`
- Texte principal (`OVERX_TEXT` / `FOREST_CREAM`)   : `#E1E8E1`
- Texte secondaire gris-vert lisible                : `#B7C5B9` / `#8FA293`

Tous les jetons (couleurs, typographie, marges, rayons, états de focus et
contrôles désactivés) sont centralisés ici pour garantir l'homogénéité entre
les feuilles QSS et les composants dessinés avec `QPainter`.
"""

from __future__ import annotations

import re
import zlib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ACCENT = "forest"

# Jetons de référence partagés avec OverX Studio
OVERX_BG = "#101713"
OVERX_SIDEBAR = "#0C120F"
OVERX_SURFACE = "#1A261F"
OVERX_SURFACE_RAISED = "#202F26"
OVERX_SURFACE_HOVER = "#26382D"
OVERX_ACTION = "#315E43"
OVERX_ACTION_HOVER = "#3B7050"
OVERX_ACTION_PRESSED = "#254A35"
OVERX_SAGE = "#A9C7AE"
OVERX_ACCENT = OVERX_SAGE
OVERX_TEXT = "#E1E8E1"
OVERX_TEXT_SECONDARY = "#B7C5B9"
OVERX_TEXT_MUTED = "#8FA293"

# Alias conservés pour compatibilité ascendante dans le dépôt
FOREST_PINE = OVERX_BG
FOREST_CHARCOAL = OVERX_SURFACE
FOREST_BRAND = OVERX_ACTION
FOREST_MOSS = OVERX_ACTION_HOVER
FOREST_SAGE = OVERX_SAGE
FOREST_CREAM = OVERX_TEXT


@dataclass(frozen=True)
class SpacingTokens:
    """Échelle d'espacement régulière (multiples de 4 px)."""

    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 20
    xxl: int = 26


@dataclass(frozen=True)
class RadiusTokens:
    """Rayons d'arrondi sobres et cohérents dans toute l'application."""

    hero: int = 18
    card: int = 14
    inner: int = 11
    control: int = 10
    pill: int = 8


@dataclass(frozen=True)
class TypographyTokens:
    """Hiérarchie typographique unifiée (en pixels avant facteur d'échelle)."""

    hero: int = 22
    page: int = 19
    section: int = 15
    card: int = 13
    body: int = 13
    caption: int = 12
    micro: int = 10


SPACING = SpacingTokens()
RADII = RadiusTokens()
TYPOGRAPHY = TypographyTokens()


@dataclass(frozen=True)
class Accent:
    """Déclinaison d'une couleur d'accent pour les thèmes sombre et clair."""

    key: str
    label: str
    # Couleur vive/sauge lisible en avant-plan sur fond sombre
    dark: str
    dark_hover: str
    dark_pressed: str
    # Couleur de remplissage du bouton primaire en thème sombre (haute lisibilité)
    dark_fill: str
    dark_fill_hover: str
    dark_fill_pressed: str
    # Couleurs équivalentes en thème clair
    light: str
    light_hover: str
    light_pressed: str
    ink: str = "#EFF4F0"

    def base(self, theme: str) -> str:
        return self.light if theme == "light" else self.dark

    def hover(self, theme: str) -> str:
        return self.light_hover if theme == "light" else self.dark_hover

    def pressed(self, theme: str) -> str:
        return self.light_pressed if theme == "light" else self.dark_pressed

    def fill(self, theme: str) -> str:
        return self.light if theme == "light" else self.dark_fill

    def fill_hover(self, theme: str) -> str:
        return self.light_hover if theme == "light" else self.dark_fill_hover

    def fill_pressed(self, theme: str) -> str:
        return self.light_pressed if theme == "light" else self.dark_fill_pressed

    def rgb(self, theme: str) -> tuple[int, int, int]:
        value = self.base(theme).lstrip("#")
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


ACCENTS: dict[str, Accent] = {
    "forest": Accent(
        key="forest",
        label="Forêt sauge (OverX)",
        dark=OVERX_SAGE,
        dark_hover="#C2DAC6",
        dark_pressed="#8EB294",
        dark_fill=OVERX_ACTION,
        dark_fill_hover=OVERX_ACTION_HOVER,
        dark_fill_pressed=OVERX_ACTION_PRESSED,
        light=OVERX_ACTION,
        light_hover=OVERX_ACTION_HOVER,
        light_pressed=OVERX_ACTION_PRESSED,
        ink="#EFF4F0",
    ),
    "emerald": Accent(
        key="emerald",
        label="Pin & Mousse",
        dark="#8FC7A3",
        dark_hover="#A9D7B9",
        dark_pressed="#72AF88",
        dark_fill="#2D6A4F",
        dark_fill_hover="#398060",
        dark_fill_pressed="#22523D",
        light="#245C43",
        light_hover="#2D6A4F",
        light_pressed="#1B4633",
    ),
    "cyan": Accent(
        key="cyan",
        label="Ardoise d'eau",
        dark="#93C5CE",
        dark_hover="#B0D8DF",
        dark_pressed="#76ACB6",
        dark_fill="#2C5E68",
        dark_fill_hover="#36727E",
        dark_fill_pressed="#224952",
        light="#235762",
        light_hover="#2C6B78",
        light_pressed="#1B434C",
    ),
    "blue": Accent(
        key="blue",
        label="Bleu minéral",
        dark="#93B4DB",
        dark_hover="#B1CBE8",
        dark_pressed="#779BC7",
        dark_fill="#2E547F",
        dark_fill_hover="#396699",
        dark_fill_pressed="#244264",
        light="#274C77",
        light_hover="#326094",
        light_pressed="#1E3B5C",
    ),
    "amber": Accent(
        key="amber",
        label="Ambre chaud",
        dark="#D4B883",
        dark_hover="#E2CCA1",
        dark_pressed="#BFA068",
        dark_fill="#6E562B",
        dark_fill_hover="#856835",
        dark_fill_pressed="#574422",
        light="#8A6421",
        light_hover="#A17628",
        light_pressed="#6F501A",
    ),
    "violet": Accent(
        key="violet",
        label="Prune sobre",
        dark="#B8A9D4",
        dark_hover="#CCC0E2",
        dark_pressed="#9E8EC0",
        dark_fill="#4E3F6E",
        dark_fill_hover="#5F4D85",
        dark_fill_pressed="#3D3157",
        light="#56437A",
        light_hover="#685294",
        light_pressed="#443561",
    ),
    "rose": Accent(
        key="rose",
        label="Terre rosée",
        dark="#D4A6AD",
        dark_hover="#E2BEC4",
        dark_pressed="#BE8C94",
        dark_fill="#6E3D46",
        dark_fill_hover="#854B55",
        dark_fill_pressed="#573037",
        light="#8B4350",
        light_hover="#A3505F",
        light_pressed="#703540",
    ),
}

UI_SCALES: dict[str, float] = {"compact": 0.92, "normal": 1.0, "large": 1.12}
UI_SCALE_LABELS: dict[str, str] = {
    "compact": "Compact",
    "normal": "Normal",
    "large": "Grand",
}


@dataclass(frozen=True)
class Palette:
    """Jetons de couleur résolus pour un thème et un accent donnés."""

    theme: str
    accent_key: str
    canvas: str
    canvas_soft: str
    sidebar: str
    surface: str
    surface_alt: str
    surface_hover: str
    input: str
    input_focus: str
    border: str
    border_strong: str
    focus_ring: str
    text: str
    text_secondary: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_pressed: str
    action: str
    action_hover: str
    action_pressed: str
    accent_ink: str
    accent_soft: str
    accent_softer: str
    info: str
    info_soft: str
    success: str
    success_soft: str
    warning: str
    warning_soft: str
    danger: str
    danger_soft: str
    overlay: str

    @property
    def dark(self) -> bool:
        return self.theme != "light"

    def accent_rgb(self) -> tuple[int, int, int]:
        value = self.accent.lstrip("#")
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]

    def action_rgb(self) -> tuple[int, int, int]:
        value = self.action.lstrip("#")
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


@dataclass(frozen=True)
class DesignTokens:
    """Regroupement complet des jetons de design actifs."""

    palette: Palette
    spacing: SpacingTokens = SPACING
    radii: RadiusTokens = RADII
    typography: TypographyTokens = TYPOGRAPHY
    scale: float = 1.0


def _rgba(hex_color: str, alpha: float) -> str:
    value = hex_color.lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


def palette(theme: str = "dark", accent: str = DEFAULT_ACCENT) -> Palette:
    """Retourne les jetons de couleur du thème demandé."""
    theme = "light" if theme == "light" else "dark"
    accent_def = ACCENTS.get(accent, ACCENTS[DEFAULT_ACCENT])
    base = accent_def.base(theme)
    hover = accent_def.hover(theme)
    pressed = accent_def.pressed(theme)
    fill = accent_def.fill(theme)
    fill_hover = accent_def.fill_hover(theme)
    fill_pressed = accent_def.fill_pressed(theme)

    if theme == "light":
        # Thème clair doux et naturel (aucun blanc éblouissant, contraste AA/AAA)
        return Palette(
            theme=theme,
            accent_key=accent_def.key,
            canvas="#EFF3EE",
            canvas_soft="#E5ECE3",
            sidebar="#E8EFE7",
            surface="#F7FAF6",
            surface_alt="#ECF2EA",
            surface_hover="#E1EAE0",
            input="#FCFDFB",
            input_focus="#FFFFFF",
            border="#CFD9CE",
            border_strong="#AABBA9",
            focus_ring=_rgba(fill, 0.55),
            text=OVERX_BG,
            text_secondary="#3B4D40",
            text_muted="#5F7264",
            accent=base,
            accent_hover=hover,
            accent_pressed=pressed,
            action=fill,
            action_hover=fill_hover,
            action_pressed=fill_pressed,
            accent_ink=accent_def.ink,
            accent_soft=_rgba(base, 0.11),
            accent_softer=_rgba(base, 0.055),
            info="#266070",
            info_soft="rgba(38, 96, 112, 0.11)",
            success="#246B43",
            success_soft="rgba(36, 107, 67, 0.11)",
            warning="#8B6112",
            warning_soft="rgba(139, 97, 18, 0.11)",
            danger="#AA3528",
            danger_soft="rgba(170, 53, 40, 0.10)",
            overlay="rgba(247, 250, 246, 0.94)",
        )

    # Thème sombre partagé avec OverX Studio (#101713 / #1A261F / #315E43 / #A9C7AE / #E1E8E1)
    return Palette(
        theme=theme,
        accent_key=accent_def.key,
        canvas=OVERX_BG,
        canvas_soft=OVERX_SIDEBAR,
        sidebar=OVERX_SIDEBAR,
        surface=OVERX_SURFACE,
        surface_alt=OVERX_SURFACE_RAISED,
        surface_hover=OVERX_SURFACE_HOVER,
        input="#131D17",
        input_focus="#17241C",
        border="rgba(169, 199, 174, 0.130)",
        border_strong="rgba(169, 199, 174, 0.250)",
        focus_ring=_rgba(base, 0.52),
        text=OVERX_TEXT,
        text_secondary=OVERX_TEXT_SECONDARY,
        text_muted=OVERX_TEXT_MUTED,
        accent=base,
        accent_hover=hover,
        accent_pressed=pressed,
        action=fill,
        action_hover=fill_hover,
        action_pressed=fill_pressed,
        accent_ink=accent_def.ink,
        accent_soft=_rgba(fill, 0.34),
        accent_softer=_rgba(fill, 0.18),
        info="#8AB4C2",
        info_soft="rgba(138, 180, 194, 0.14)",
        success="#7FC292",
        success_soft="rgba(127, 194, 146, 0.14)",
        warning="#D4B06A",
        warning_soft="rgba(212, 176, 106, 0.14)",
        danger="#E08779",
        danger_soft="rgba(224, 135, 121, 0.14)",
        overlay="rgba(12, 18, 15, 0.90)",
    )


def design_tokens(
    theme: str = "dark",
    accent: str = DEFAULT_ACCENT,
    ui_scale: str = "normal",
) -> DesignTokens:
    return DesignTokens(
        palette=palette(theme, accent),
        spacing=SPACING,
        radii=RADII,
        typography=TYPOGRAPHY,
        scale=scale_factor(ui_scale),
    )


_ASSET_CACHE: dict[tuple[str, str], dict[str, str]] = {}


def _asset_dir() -> Path:
    import tempfile

    folder = Path(tempfile.gettempdir()) / "overload-ui-assets"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _render_asset(name: str, size: int, paint) -> str:  # noqa: ANN001
    """Rend une image QSS en 2x pour rester nette sur les écrans HiDPI."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPainter, QPixmap

    path = _asset_dir() / f"{name}.png"
    if path.is_file():
        return path.as_posix()
    size *= 2
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    paint(painter, size)
    painter.end()
    pix.save(str(path), "PNG")
    return path.as_posix()


def _paint_chevron(painter, size: int, color: str, direction: str) -> None:  # noqa: ANN001
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QPen

    pen = QPen(QColor(color), max(1.4, size / 8.5))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    margin = size * 0.24
    if direction == "down":
        points = [
            QPointF(margin, size * 0.36),
            QPointF(size / 2, size * 0.66),
            QPointF(size - margin, size * 0.36),
        ]
    else:
        points = [
            QPointF(margin, size * 0.64),
            QPointF(size / 2, size * 0.34),
            QPointF(size - margin, size * 0.64),
        ]
    painter.drawPolyline(points)


def _paint_indicator(painter, size: int, theme: Palette, checked: bool, kind: str) -> None:  # noqa: ANN001
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QPen

    colors = palette(theme.theme, theme.accent_key)
    fill_color = qcolor(colors.action if checked else colors.input)
    stroke_color = qcolor(colors.accent if checked else colors.border_strong)
    if kind == "check":
        painter.setPen(QPen(stroke_color, 1.4))
        painter.setBrush(fill_color)
        painter.drawRoundedRect(QRectF(1, 1, size - 2, size - 2), 4, 4)
        if checked:
            pen = QPen(qcolor(colors.accent_ink), 1.9)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPolyline(
                [
                    QPointF(size * 0.26, size * 0.52),
                    QPointF(size * 0.43, size * 0.69),
                    QPointF(size * 0.75, size * 0.32),
                ]
            )
        return
    center = QPointF(size / 2, size / 2)
    painter.setPen(QPen(stroke_color, 1.4))
    painter.setBrush(fill_color)
    painter.drawEllipse(center, size * 0.42, size * 0.42)
    if checked:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qcolor(colors.accent_ink))
        painter.drawEllipse(center, size * 0.19, size * 0.19)


def theme_assets(theme: str = "dark", accent: str = DEFAULT_ACCENT) -> dict[str, str]:
    """Génère (une seule fois par thème/accent) les images QSS des contrôles natifs."""
    key = (theme, accent)
    cached = _ASSET_CACHE.get(key)
    if cached is not None:
        return cached
    p = palette(theme, accent)
    signature = zlib.crc32(
        "|".join(
            (p.canvas, p.surface, p.input, p.border_strong, p.text_muted, p.accent, p.action)
        ).encode("utf-8")
    )
    suffix = f"{p.theme}-{p.accent_key}-{signature:08x}"
    assets = {
        "down": _render_asset(
            f"chevron-down-{suffix}",
            18,
            lambda painter, size: _paint_chevron(painter, size, p.text_muted, "down"),
        ),
        "up": _render_asset(
            f"chevron-up-{suffix}",
            18,
            lambda painter, size: _paint_chevron(painter, size, p.text_muted, "up"),
        ),
        "check_on": _render_asset(
            f"check-on-{suffix}",
            16,
            lambda painter, size: _paint_indicator(painter, size, p, True, "check"),
        ),
        "check_off": _render_asset(
            f"check-off-{suffix}",
            16,
            lambda painter, size: _paint_indicator(painter, size, p, False, "check"),
        ),
        "radio_on": _render_asset(
            f"radio-on-{suffix}",
            16,
            lambda painter, size: _paint_indicator(painter, size, p, True, "radio"),
        ),
        "radio_off": _render_asset(
            f"radio-off-{suffix}",
            16,
            lambda painter, size: _paint_indicator(painter, size, p, False, "radio"),
        ),
    }
    _ASSET_CACHE[key] = assets
    return assets


def scale_factor(ui_scale: str) -> float:
    return UI_SCALES.get(ui_scale, 1.0)


def font_family() -> str:
    return '"Inter", "Manrope", "Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI", "Arial"'


def display_family() -> str:
    return (
        '"Inter", "Manrope", "Segoe UI Variable Display", "Segoe UI Variable", "Segoe UI", "Arial"'
    )


def build_stylesheet(
    theme: str = "dark",
    accent: str = DEFAULT_ACCENT,
    ui_scale: str = "normal",
) -> str:
    """Construit la feuille de style Qt complète de l'application."""
    p = palette(theme, accent)
    f = scale_factor(ui_scale)
    try:
        assets = theme_assets(p.theme, p.accent_key)
    except Exception:
        assets = {}
    down_arrow = assets.get("down", "")
    up_arrow = assets.get("up", "")
    check_on = assets.get("check_on", "")
    check_off = assets.get("check_off", "")
    radio_on = assets.get("radio_on", "")
    radio_off = assets.get("radio_off", "")

    def s(value: float) -> int:
        return max(1, round(value * f))

    return f"""
    QWidget {{
        color: {p.text};
        font-family: {font_family()};
        font-size: {s(TYPOGRAPHY.body)}px;
    }}
    QMainWindow, QWidget#rootWidget, QWidget#pageHost, QDialog {{
        background-color: {p.canvas};
    }}
    QFrame#sidebar {{
        background-color: {p.sidebar};
        border: none;
        border-right: 1px solid {p.border};
    }}
    QFrame#topBar {{
        background-color: {p.canvas};
        border: none;
        border-bottom: 1px solid {p.border};
    }}
    QFrame#panelCard, QFrame#settingCard, QFrame#libraryCard {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-radius: {s(RADII.card)}px;
    }}
    QFrame#taskCard, QFrame#historyCard {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-radius: {s(RADII.card)}px;
    }}
    QFrame#taskCard:hover, QFrame#historyCard:hover, QFrame#libraryCard:hover {{
        background-color: {p.surface_alt};
        border: 1px solid {p.border_strong};
    }}
    QFrame#statCard {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-radius: {s(RADII.card)}px;
    }}
    QFrame#innerCard, QFrame#toolIntroCard {{
        background-color: {p.surface_alt};
        border: 1px solid {p.border};
        border-radius: {s(RADII.inner)}px;
    }}
    QFrame#heroCard {{
        background-color: {p.surface};
        border: 1px solid {p.border_strong};
        border-radius: {s(RADII.hero)}px;
        background-image: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {p.surface}, stop:0.62 {p.surface}, stop:1 {p.accent_softer});
    }}
    QFrame#guideCard {{
        background-color: {p.surface};
        border: 1px solid {p.border_strong};
        border-radius: {s(RADII.card)}px;
    }}
    QFrame#promoCard {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-radius: {s(RADII.card)}px;
        background-image: qlineargradient(x1:0, y1:1, x2:1, y2:0,
            stop:0 {p.surface}, stop:1 {p.accent_softer});
    }}
    QFrame#segmented {{
        background-color: {p.input};
        border: 1px solid {p.border};
        border-radius: {s(RADII.inner)}px;
    }}
    QFrame#errorPanel {{
        background-color: {p.danger_soft};
        border: 1px solid {_rgba(p.danger, 0.36)};
        border-radius: {s(RADII.control)}px;
    }}
    QFrame#warningPanel {{
        background-color: {p.warning_soft};
        border: 1px solid {_rgba(p.warning, 0.34)};
        border-radius: {s(RADII.control)}px;
    }}
    QFrame#infoPanel {{
        background-color: {p.info_soft};
        border: 1px solid {_rgba(p.info, 0.30)};
        border-radius: {s(RADII.control)}px;
    }}
    QFrame#successPanel {{
        background-color: {p.success_soft};
        border: 1px solid {_rgba(p.success, 0.30)};
        border-radius: {s(RADII.control)}px;
    }}
    QFrame#toast {{
        background-color: {p.surface_alt};
        border: 1px solid {p.border_strong};
        border-radius: {s(RADII.inner)}px;
    }}
    QFrame#divider {{
        background-color: {p.border};
        border: none;
        max-height: 1px;
    }}
    QLabel {{
        color: {p.text};
        background: transparent;
    }}
    QLabel#pageTitle {{
        font-family: {display_family()};
        font-size: {s(TYPOGRAPHY.page)}px;
        font-weight: 700;
    }}
    QLabel#pageSubtitle {{
        color: {p.text_secondary};
        font-size: {s(TYPOGRAPHY.caption)}px;
    }}
    QLabel#heroTitle {{
        font-family: {display_family()};
        font-size: {s(TYPOGRAPHY.hero)}px;
        font-weight: 700;
    }}
    QLabel#heroSubtitle {{
        color: {p.text_secondary};
        font-size: {s(TYPOGRAPHY.body)}px;
    }}
    QLabel#brandTitle {{
        font-family: {display_family()};
        font-size: {s(17)}px;
        font-weight: 700;
    }}
    QLabel#brandSubtitle {{
        color: {p.accent};
        font-size: {s(9)}px;
        font-weight: 700;
    }}
    QLabel#sectionTitle {{
        font-family: {display_family()};
        font-size: {s(TYPOGRAPHY.section)}px;
        font-weight: 700;
    }}
    QLabel#cardTitle {{
        font-size: {s(TYPOGRAPHY.card)}px;
        font-weight: 600;
    }}
    QLabel#mutedLabel {{
        color: {p.text_secondary};
        font-size: {s(TYPOGRAPHY.caption)}px;
    }}
    QLabel#tinyLabel {{
        color: {p.text_muted};
        font-size: {s(11)}px;
    }}
    QLabel#fieldLabel {{
        color: {p.text_secondary};
        font-size: {s(11)}px;
        font-weight: 600;
    }}
    QLabel#eyebrowLabel {{
        color: {p.accent};
        font-size: {s(10)}px;
        font-weight: 700;
    }}
    QLabel#statValue {{
        font-family: {display_family()};
        font-size: {s(20)}px;
        font-weight: 700;
    }}
    QLabel#statCaption {{
        color: {p.text_muted};
        font-size: {s(10)}px;
        font-weight: 700;
    }}
    QLabel#statHint {{
        color: {p.text_secondary};
        font-size: {s(11)}px;
    }}
    QLabel#dangerText {{
        color: {p.danger};
        font-size: {s(12)}px;
        font-weight: 600;
    }}
    QLabel#successText {{
        color: {p.success};
        font-size: {s(12)}px;
        font-weight: 600;
    }}
    QLabel#infoText {{
        color: {p.info};
        font-size: {s(12)}px;
        font-weight: 600;
    }}
    QLabel#warningText {{
        color: {p.warning};
        font-size: {s(12)}px;
        font-weight: 600;
    }}
    QLabel#statePill {{
        border-radius: {s(RADII.pill)}px;
        padding: {s(2)}px {s(9)}px;
        font-size: {s(10)}px;
        font-weight: 700;
    }}
    QLabel#statePill[state="running"] {{
        color: {p.accent};
        background-color: {p.accent_soft};
    }}
    QLabel#statePill[state="queued"] {{
        color: {p.text_secondary};
        background-color: {p.surface_alt};
    }}
    QLabel#statePill[state="paused"] {{
        color: {p.info};
        background-color: {p.info_soft};
    }}
    QLabel#statePill[state="completed"] {{
        color: {p.success};
        background-color: {p.success_soft};
    }}
    QLabel#statePill[state="failed"] {{
        color: {p.danger};
        background-color: {p.danger_soft};
    }}
    QLabel#statePill[state="warning"] {{
        color: {p.warning};
        background-color: {p.warning_soft};
    }}
    QLabel#statePill[state="neutral"] {{
        color: {p.text_secondary};
        background-color: {p.surface_alt};
    }}
    QLabel#formatChip, QLabel#kbdBadge {{
        color: {p.text_secondary};
        background-color: {p.surface_alt};
        border: 1px solid {p.border};
        border-radius: {s(6)}px;
        padding: {s(2)}px {s(7)}px;
        font-size: {s(10)}px;
        font-weight: 700;
    }}
    QLabel#navSectionLabel {{
        color: {p.text_muted};
        font-size: {s(10)}px;
        font-weight: 700;
        padding-left: {s(14)}px;
    }}
    QLabel#versionLabel {{
        color: {p.text_muted};
        font-size: {s(11)}px;
    }}
    QLabel#emptyTitle {{
        font-family: {display_family()};
        font-size: {s(15)}px;
        font-weight: 700;
    }}
    QLabel#emptyText {{
        color: {p.text_secondary};
        font-size: {s(12)}px;
    }}
    QLabel#monoLabel, QPlainTextEdit#analyzerOutput, QPlainTextEdit#creatorsTracksOutput,
    QPlainTextEdit#diagLogOutput {{
        font-family: "Cascadia Mono", "Consolas", "SFMono-Regular", monospace;
        font-size: {s(12)}px;
    }}
    QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background-color: {p.input};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: {s(RADII.control)}px;
        padding: {s(6)}px {s(10)}px;
        selection-background-color: {p.action};
        selection-color: {p.accent_ink};
    }}
    QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover, QComboBox:hover, QSpinBox:hover {{
        border: 1px solid {p.border_strong};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus,
    QDoubleSpinBox:focus {{
        border: 1px solid {p.focus_ring};
        background-color: {p.input_focus};
    }}
    QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
        color: {p.text_muted};
        background-color: {p.surface_alt};
    }}
    QLineEdit#searchField {{
        background-color: {p.input};
        border: 1px solid {p.border};
        border-radius: {s(RADII.control)}px;
        padding: {s(6)}px {s(12)}px;
        font-size: {s(12)}px;
    }}
    QLineEdit#searchField:focus {{
        border: 1px solid {p.focus_ring};
        background-color: {p.input_focus};
    }}
    QLineEdit#urlField {{
        background-color: {p.input};
        border: 1px solid {p.border_strong};
        border-radius: {s(11)}px;
        padding: {s(10)}px {s(13)}px;
        font-size: {s(13)}px;
    }}
    QLineEdit#urlField:focus {{
        border: 1px solid {p.focus_ring};
        background-color: {p.input_focus};
    }}
    QLineEdit#urlField[invalid="true"] {{
        border: 1px solid {p.danger};
    }}
    QLineEdit#urlField[valid="true"] {{
        border: 1px solid {_rgba(p.success, 0.72)};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: center right;
        border: none;
        width: {s(26)}px;
    }}
    QComboBox::down-arrow {{
        image: url("{down_arrow}");
        width: {s(14)}px;
        height: {s(14)}px;
    }}
    QAbstractSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: {s(20)}px;
        border-left: 1px solid {p.border};
        border-top-right-radius: {s(RADII.control)}px;
        background: transparent;
    }}
    QAbstractSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: {s(20)}px;
        border-left: 1px solid {p.border};
        border-bottom-right-radius: {s(RADII.control)}px;
        background: transparent;
    }}
    QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{
        background-color: {p.surface_hover};
    }}
    QAbstractSpinBox::up-arrow {{
        image: url("{up_arrow}");
        width: {s(11)}px;
        height: {s(11)}px;
    }}
    QAbstractSpinBox::down-arrow {{
        image: url("{down_arrow}");
        width: {s(11)}px;
        height: {s(11)}px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {p.surface_alt};
        color: {p.text};
        border: 1px solid {p.border_strong};
        border-radius: {s(9)}px;
        padding: {s(4)}px;
        selection-background-color: {p.accent_soft};
        selection-color: {p.text};
        outline: 0;
    }}
    QPushButton {{
        background-color: {p.surface_alt};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: {s(RADII.control)}px;
        padding: {s(6)}px {s(13)}px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {p.surface_hover};
        border: 1px solid {p.border_strong};
    }}
    QPushButton:focus {{
        border: 1px solid {p.focus_ring};
    }}
    QPushButton:pressed {{
        background-color: {p.surface};
    }}
    QPushButton:disabled {{
        color: {p.text_muted};
        background-color: {p.surface};
        border: 1px solid {p.border};
    }}
    QPushButton#primaryBtn, QPushButton[primary="true"] {{
        background-color: {p.action};
        color: {p.accent_ink};
        border: 1px solid {p.action_hover};
        font-weight: 700;
    }}
    QPushButton#primaryBtn:hover, QPushButton[primary="true"]:hover {{
        background-color: {p.action_hover};
        border: 1px solid {p.accent};
    }}
    QPushButton#primaryBtn:pressed, QPushButton[primary="true"]:pressed {{
        background-color: {p.action_pressed};
        border: 1px solid {p.action};
    }}
    QPushButton#primaryBtn:disabled, QPushButton[primary="true"]:disabled {{
        background-color: {p.surface_alt};
        color: {p.text_muted};
        border: 1px solid {p.border};
    }}
    QPushButton#secondaryBtn {{
        background-color: {p.accent_soft};
        color: {p.accent};
        border: 1px solid {p.border_strong};
        font-weight: 700;
    }}
    QPushButton#secondaryBtn:hover {{
        border: 1px solid {p.accent};
        background-color: {p.surface_hover};
        color: {p.text};
    }}
    QPushButton#secondaryBtn:disabled {{
        background-color: {p.surface};
        color: {p.text_muted};
        border: 1px solid {p.border};
    }}
    QPushButton#dangerBtn {{
        background-color: {p.danger_soft};
        color: {p.danger};
        border: 1px solid {_rgba(p.danger, 0.28)};
        font-weight: 600;
    }}
    QPushButton#dangerBtn:hover {{
        border: 1px solid {_rgba(p.danger, 0.6)};
    }}
    QPushButton#ghostBtn {{
        background-color: transparent;
        border: 1px solid {p.border};
        color: {p.text_secondary};
        font-weight: 600;
    }}
    QPushButton#ghostBtn:hover {{
        background-color: {p.surface_hover};
        border: 1px solid {p.border_strong};
        color: {p.text};
    }}
    QPushButton#linkBtn {{
        background-color: transparent;
        border: none;
        color: {p.accent};
        padding: {s(2)}px {s(4)}px;
        font-weight: 600;
        text-align: left;
    }}
    QPushButton#linkBtn:hover {{
        color: {p.accent_hover};
        text-decoration: underline;
    }}
    QPushButton#iconBtn, QPushButton#iconBtnDanger {{
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: {s(9)}px;
        padding: 0px;
    }}
    QPushButton#iconBtn:hover {{
        background-color: {p.surface_hover};
        border: 1px solid {p.border};
    }}
    QPushButton#iconBtn:focus {{
        border: 1px solid {p.focus_ring};
    }}
    QPushButton#iconBtn:pressed {{
        background-color: {p.surface};
    }}
    QPushButton#iconBtnDanger:hover {{
        background-color: {p.danger_soft};
        border: 1px solid {_rgba(p.danger, 0.35)};
    }}
    QPushButton#segment {{
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: {s(8)}px;
        padding: {s(5)}px {s(11)}px;
        color: {p.text_secondary};
        font-weight: 600;
        font-size: {s(12)}px;
    }}
    QPushButton#segment:hover {{
        color: {p.text};
        background-color: {p.surface_hover};
    }}
    QPushButton#segment:checked {{
        background-color: {p.action};
        color: {p.accent_ink};
        border: 1px solid {p.action_hover};
    }}
    QPushButton#chip {{
        background-color: {p.input};
        border: 1px solid {p.border};
        border-radius: {s(14)}px;
        padding: {s(4)}px {s(11)}px;
        color: {p.text_secondary};
        font-size: {s(11)}px;
        font-weight: 600;
    }}
    QPushButton#chip:hover {{
        border: 1px solid {p.border_strong};
        color: {p.text};
    }}
    QPushButton#chip:checked {{
        background-color: {p.accent_soft};
        border: 1px solid {p.accent};
        color: {p.text};
    }}
    QTabWidget::pane {{
        border: 1px solid {p.border};
        border-radius: {s(RADII.card)}px;
        background-color: {p.surface};
        top: -1px;
    }}
    QTabWidget#creatorsTabs::pane {{
        background-color: {p.surface};
    }}
    QTabBar::tab {{
        background-color: transparent;
        color: {p.text_secondary};
        padding: {s(7)}px {s(12)}px;
        margin: 0px {s(3)}px {s(4)}px 0px;
        border-radius: {s(8)}px;
        border: 1px solid transparent;
        font-weight: 600;
        font-size: {s(12)}px;
    }}
    QTabBar::tab:hover {{
        color: {p.text};
        background-color: {p.surface_hover};
    }}
    QTabBar::tab:selected {{
        color: {p.text};
        background-color: {p.accent_soft};
        border: 1px solid {p.border_strong};
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: {s(10)}px;
        margin: {s(2)}px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {p.border_strong};
        border-radius: {s(4)}px;
        min-height: {s(30)}px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {p.text_muted};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        height: 0px;
        background: transparent;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: {s(10)}px;
        margin: {s(2)}px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {p.border_strong};
        border-radius: {s(4)}px;
        min-width: {s(30)}px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        width: 0px;
        background: transparent;
    }}
    QCheckBox, QRadioButton {{
        color: {p.text};
        spacing: {s(8)}px;
        background: transparent;
    }}
    QCheckBox::indicator {{
        image: url("{check_off}");
        width: {s(16)}px;
        height: {s(16)}px;
    }}
    QCheckBox::indicator:checked {{
        image: url("{check_on}");
    }}
    QRadioButton::indicator {{
        image: url("{radio_off}");
        width: {s(16)}px;
        height: {s(16)}px;
    }}
    QRadioButton::indicator:checked {{
        image: url("{radio_on}");
    }}
    QProgressBar {{
        background-color: {p.input};
        border: 1px solid {p.border};
        border-radius: {s(5)}px;
        height: {s(10)}px;
        text-align: center;
        color: {p.text};
    }}
    QProgressBar::chunk {{
        background-color: {p.action_hover};
        border-radius: {s(4)}px;
    }}
    QTableWidget, QTreeWidget, QListWidget {{
        background-color: {p.surface};
        alternate-background-color: {p.surface_alt};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: {s(RADII.control)}px;
        gridline-color: {p.border};
        selection-background-color: {p.accent_soft};
        selection-color: {p.text};
        outline: 0;
    }}
    QHeaderView::section {{
        background-color: {p.surface_alt};
        color: {p.text_secondary};
        border: none;
        border-bottom: 1px solid {p.border};
        padding: {s(6)}px {s(8)}px;
        font-weight: 600;
        font-size: {s(11)}px;
    }}
    QTableCornerButton::section {{
        background-color: {p.surface_alt};
        border: none;
    }}
    QMenu {{
        background-color: {p.surface_alt};
        color: {p.text};
        border: 1px solid {p.border_strong};
        border-radius: {s(9)}px;
        padding: {s(5)}px;
    }}
    QMenu::item {{
        padding: {s(6)}px {s(14)}px;
        border-radius: {s(6)}px;
    }}
    QMenu::item:selected {{
        background-color: {p.accent_soft};
        color: {p.text};
    }}
    QToolTip {{
        background-color: {p.surface_alt};
        color: {p.text};
        border: 1px solid {p.border_strong};
        padding: {s(5)}px {s(9)}px;
        font-size: {s(11)}px;
    }}
    QMessageBox {{
        background-color: {p.canvas};
    }}
    QMessageBox QLabel {{
        color: {p.text};
    }}
    QDialogButtonBox QPushButton {{
        min-width: {s(88)}px;
    }}
    """


def _qcolor(hex_color: str):
    return qcolor(hex_color)


def qcolor(value: str):
    """Convertit une couleur QSS (hex ou `rgba(r, g, b, a)`) en QColor valide."""
    from PySide6.QtGui import QColor

    text = value.strip()
    pattern = (
        r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)"
        r"\s*(?:,\s*([\d.]+)\s*)?\)"
    )
    match = re.fullmatch(pattern, text)
    if match:
        r, g, b = (int(float(match.group(i))) for i in (1, 2, 3))
        alpha_raw = match.group(4)
        alpha = 255 if alpha_raw is None else round(float(alpha_raw) * 255)
        return QColor(r, g, b, max(0, min(255, alpha)))
    return QColor(text)


def apply_appearance(
    app, theme: str = "dark", accent: str = DEFAULT_ACCENT, ui_scale: str = "normal"
):
    """Applique palette, police et feuille de style à toute l'application."""
    from PySide6.QtGui import QFont, QPalette

    p = palette(theme, accent)
    f = scale_factor(ui_scale)

    app.setStyle("Fusion")

    font = QFont()
    font.setFamilies(
        ["Inter", "Manrope", "Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI", "Arial"]
    )
    font.setPixelSize(max(10, round(TYPOGRAPHY.body * f)))
    app.setFont(font)

    qt_palette = QPalette()
    qt_palette.setColor(QPalette.ColorRole.Window, qcolor(p.canvas))
    qt_palette.setColor(QPalette.ColorRole.WindowText, qcolor(p.text))
    qt_palette.setColor(QPalette.ColorRole.Base, qcolor(p.input))
    qt_palette.setColor(QPalette.ColorRole.AlternateBase, qcolor(p.surface_alt))
    qt_palette.setColor(QPalette.ColorRole.ToolTipBase, qcolor(p.surface_alt))
    qt_palette.setColor(QPalette.ColorRole.ToolTipText, qcolor(p.text))
    qt_palette.setColor(QPalette.ColorRole.Text, qcolor(p.text))
    qt_palette.setColor(QPalette.ColorRole.Button, qcolor(p.surface_alt))
    qt_palette.setColor(QPalette.ColorRole.ButtonText, qcolor(p.text))
    qt_palette.setColor(QPalette.ColorRole.BrightText, qcolor(p.danger))
    qt_palette.setColor(QPalette.ColorRole.Link, qcolor(p.accent))
    qt_palette.setColor(QPalette.ColorRole.Highlight, qcolor(p.action))
    qt_palette.setColor(QPalette.ColorRole.HighlightedText, qcolor(p.accent_ink))
    qt_palette.setColor(QPalette.ColorRole.PlaceholderText, qcolor(p.text_muted))
    qt_palette.setColor(QPalette.ColorRole.Mid, qcolor(p.border_strong))
    qt_palette.setColor(QPalette.ColorRole.Dark, qcolor(p.border_strong))
    qt_palette.setColor(QPalette.ColorRole.Light, qcolor(p.surface))
    app.setPalette(qt_palette)
    app.setStyleSheet(build_stylesheet(theme, accent, ui_scale))
    return p
