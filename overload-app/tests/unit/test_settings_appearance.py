from overload.settings.store import SETTINGS_SCHEMA_VERSION, SettingsStore
from overload.ui.theme import (
    ACCENTS,
    DEFAULT_ACCENT,
    FOREST_BRAND,
    FOREST_CHARCOAL,
    FOREST_CREAM,
    FOREST_PINE,
    FOREST_SAGE,
    OVERX_ACCENT,
    OVERX_ACTION,
    OVERX_BG,
    OVERX_SURFACE,
    OVERX_TEXT,
    build_stylesheet,
    design_tokens,
    palette,
)


def test_appearance_defaults_and_persistence(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    prefs = store.get()
    assert prefs.schema_version == SETTINGS_SCHEMA_VERSION == 4
    assert prefs.theme == "dark"
    assert prefs.accent == "forest"
    assert DEFAULT_ACCENT == "forest"
    assert prefs.ui_scale == "normal"
    assert prefs.onboarding_dismissed is False

    store.update(accent="blue", ui_scale="large", onboarding_dismissed=True)
    reloaded = SettingsStore(tmp_path / "settings.json").get()
    assert reloaded.accent == "blue"
    assert reloaded.ui_scale == "large"
    assert reloaded.onboarding_dismissed is True

    # Reset restores recommended defaults while preserving destination directory
    custom_dir = tmp_path / "custom-downloads"
    store.update(destination_dir=str(custom_dir))
    reset_prefs = store.reset_to_defaults(keep_destination=True)
    assert reset_prefs.theme == "dark"
    assert reset_prefs.accent == "forest"
    assert reset_prefs.ui_scale == "normal"
    assert reset_prefs.destination_dir == str(custom_dir)


def test_invalid_appearance_values_fall_back(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"accent": "neon", "ui_scale": "geante"}', encoding="utf-8")
    prefs = SettingsStore(path).get()
    assert prefs.accent == "forest"
    assert prefs.ui_scale == "normal"


def test_old_default_violet_migrates_once_to_forest(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"schema_version": 2, "accent": "violet"}', encoding="utf-8")
    assert SettingsStore(path).get().accent == "forest"

    store = SettingsStore(path)
    store.update(accent="violet")
    assert SettingsStore(path).get().accent == "violet"


def test_forest_palette_matches_overx_studio_tokens():
    dark = palette("dark", "forest")
    assert dark.canvas == OVERX_BG == FOREST_PINE == "#101713"
    assert dark.surface == OVERX_SURFACE == FOREST_CHARCOAL == "#1A261F"
    assert dark.action == OVERX_ACTION == FOREST_BRAND == "#315E43"
    assert dark.accent == OVERX_ACCENT == FOREST_SAGE == "#A9C7AE"
    assert dark.text == OVERX_TEXT == FOREST_CREAM == "#E1E8E1"

    tokens = design_tokens("dark", "forest", "normal")
    assert tokens.spacing.lg == 16
    assert tokens.radii.card == 14
    assert tokens.typography.body == 13

    light = palette("light", "forest")
    assert light.theme == "light"
    assert light.text == OVERX_BG
    assert light.accent == OVERX_ACTION


def test_palette_uses_requested_accent_and_theme():
    dark = palette("dark", "violet")
    assert dark.canvas == "#101713"
    assert dark.accent == ACCENTS["violet"].dark
    light = palette("light", "blue")
    assert light.theme == "light"
    assert light.accent == ACCENTS["blue"].light


def test_stylesheet_scales_with_ui_size():
    normal = build_stylesheet("dark", "forest", "normal")
    large = build_stylesheet("dark", "forest", "large")
    assert "#101713" in normal
    assert "#1A261F" in normal
    assert "#315E43" in normal
    assert normal != large
    assert "font-size: 15px" in large
