"""Le build direct doit préparer ses dépendances sans compter sur le workflow CI."""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from overload import __version__

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_windows.py"
spec = importlib.util.spec_from_file_location("windows_build", SCRIPT)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def test_existing_tools_do_not_download(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "ROOT", tmp_path)
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ("ffmpeg.exe", "ffprobe.exe"):
        (tools / name).touch()
    monkeypatch.setitem(sys.modules, "prepare_ffmpeg", None)
    build.ensure_media_tools()


def test_missing_tools_are_prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "ROOT", tmp_path)
    calls = []

    def prepare():
        calls.append(True)
        tools = tmp_path / "tools"
        tools.mkdir()
        for name in ("ffmpeg.exe", "ffprobe.exe"):
            (tools / name).touch()

    monkeypatch.setitem(sys.modules, "prepare_ffmpeg", SimpleNamespace(prepare=prepare))
    monkeypatch.syspath_prepend(str(tmp_path))
    build.ensure_media_tools()
    assert calls == [True]


def test_incomplete_preparation_fails_early(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "ROOT", tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setitem(sys.modules, "prepare_ffmpeg", SimpleNamespace(prepare=lambda: None))
    with pytest.raises(RuntimeError, match="ffmpeg.exe"):
        build.ensure_media_tools()


def test_release_version_is_synchronised_everywhere():
    """Le paquet, le pyproject et l'installateur Inno Setup doivent partager
    la même version, sinon l'exécutable et la release publiée divergent."""
    root = SCRIPT.parents[1]
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    installer = (root / "packaging" / "OverLoad.iss").read_text(encoding="utf-8")
    assert pyproject["project"]["version"] == __version__
    assert f'#define MyAppVersion "{__version__}"' in installer


def test_redesigned_ui_modules_are_bundled():
    """L'interface native est importée dynamiquement : PyInstaller doit la voir."""
    for module in (
        "overload.ui.window",
        "overload.ui.components",
        "overload.ui.icons",
        "overload.ui.failure_text",
        "overload.ui.theme",
    ):
        assert module in build.HIDDEN_IMPORTS
    spec = (SCRIPT.parents[1] / "OverLoad.spec").read_text(encoding="utf-8")
    assert '"overload.ui.window"' in spec
    assert '"overload.ui.icons"' in spec


def test_youtube_extractor_is_bundled_in_the_exe():
    """yt-dlp doit être collecté en entier : il charge ses extracteurs à l'exécution."""
    assert "overload.downloads.youtube" in build.HIDDEN_IMPORTS
    assert "yt_dlp" in build.HIDDEN_IMPORTS
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"--collect-submodules", "yt_dlp"' in source
    spec = (SCRIPT.parents[1] / "OverLoad.spec").read_text(encoding="utf-8")
    assert '"overload.downloads.youtube"' in spec
    assert 'collect_submodules("yt_dlp")' in spec


def test_every_overload_module_is_bundled_in_script_and_spec():
    """Tout nouveau module du paquet doit être inclus dans build_windows.py et OverLoad.spec."""
    root = SCRIPT.parents[1]
    src_root = root / "src"
    spec_text = (root / "OverLoad.spec").read_text(encoding="utf-8")
    entry_points = {"overload.__main__", "overload.exe_entry", "overload.ui.web"}

    missing_script = []
    missing_spec = []
    for py_file in sorted((src_root / "overload").rglob("*.py")):
        rel = py_file.relative_to(src_root).with_suffix("")
        parts = list(rel.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        dotted = ".".join(parts)
        if dotted in entry_points:
            continue
        if dotted not in build.HIDDEN_IMPORTS:
            missing_script.append(dotted)
        if f'"{dotted}"' not in spec_text:
            missing_spec.append(dotted)

    assert not missing_script, f"Manquant dans build_windows.py : {missing_script}"
    assert not missing_spec, f"Manquant dans OverLoad.spec : {missing_spec}"


def test_windows_ico_has_all_standard_resolutions():
    import struct

    ico_path = SCRIPT.parents[1] / "assets" / "overload.ico"
    data = ico_path.read_bytes()
    reserved, ico_type, count = struct.unpack_from("<HHH", data, 0)
    assert reserved == 0
    assert ico_type == 1
    assert count == 7
    sizes = set()
    for i in range(count):
        width, height = struct.unpack_from("<BB", data, 6 + i * 16)
        sizes.add((width or 256, height or 256))
    assert sizes == {(s, s) for s in (16, 24, 32, 48, 64, 128, 256)}
