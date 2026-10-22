from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)


def _make_app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_desktop_window_renders_tasks_library_history_and_settings(server, tmp_path):
    from overload.downloads.manager import DownloadManager
    from overload.history.store import DownloadHistoryStore
    from overload.settings.store import SettingsStore
    from overload.ui.desktop import create_main_window

    app = _make_app()
    settings_store = SettingsStore(tmp_path / "settings.json")
    with (
        DownloadHistoryStore(tmp_path / "library.db") as history,
        DownloadManager(
            tmp_path / "downloads",
            history=history,
            state_file=tmp_path / "queue.json",
            allow_private_hosts=True,
        ) as manager,
    ):
        win = create_main_window(manager, history, settings_store, data_dir=tmp_path)
        win.show()
        app.processEvents()

        snap = manager.enqueue(f"{server}/ok.bin")
        assert snap is not None
        assert manager.wait_all(timeout=10)
        win.refresh_all()
        app.processEvents()

        assert snap.id in win._cards
        assert win._cards[snap.id].name.text() == snap.filename

        win.go_to("library")
        app.processEvents()
        assert win.stack.currentWidget() is win._pages["library"]
        assert win.library_page.refresh_items(force=True) >= 1

        # L'ouverture d'un fichier depuis la bibliothèque vers l'analyseur ou les sous-titres
        # fonctionne
        first_entry = win.library_page.scan_local_files()[0]
        win.open_file_in_analyzer(first_entry.path)
        app.processEvents()
        assert win.stack.currentWidget() is win._pages["creators"]
        assert win.creators_widget.analyzer_widget.findChild(
            QtWidgets.QLineEdit, "analyzerPath"
        ).text() == str(first_entry.path)

        win.open_file_in_tracks(first_entry.path)
        app.processEvents()
        assert win.creators_widget.findChild(
            QtWidgets.QLineEdit, "creatorsTracksPath"
        ).text() == str(first_entry.path)

        win.go_to("downloads")
        app.processEvents()
        assert win.stack.currentWidget() is win._pages["downloads"]

        win.go_to("history")
        app.processEvents()
        assert win.stack.currentWidget() is win._pages["history"]

        win.go_to("settings")
        app.processEvents()
        assert win.stack.currentWidget() is win._pages["settings"]

        win.go_to("help")
        app.processEvents()
        assert win.stack.currentWidget() is win._pages["help"]
        assert (
            "Diagnostic" in win.help_page.log_output.toPlainText()
            or win.help_page.log_output.toPlainText() != ""
        )

        win.close()
        win.deleteLater()
        app.processEvents()


def test_desktop_navigation_onboarding_and_theme_switch(tmp_path):
    from overload.downloads.manager import DownloadManager
    from overload.history.store import DownloadHistoryStore
    from overload.settings.store import SettingsStore
    from overload.ui.desktop import create_main_window
    from overload.ui.theme import OVERX_BG, palette

    app = _make_app()
    settings_store = SettingsStore(tmp_path / "settings.json")
    with (
        DownloadHistoryStore(tmp_path / "library.db") as history,
        DownloadManager(tmp_path / "downloads", history=history) as manager,
    ):
        win = create_main_window(manager, history, settings_store, data_dir=tmp_path)
        win.show()
        app.processEvents()

        assert set(win._pages) == {
            "home",
            "downloads",
            "library",
            "creators",
            "history",
            "settings",
            "help",
        }
        assert win.tokens.canvas == OVERX_BG == "#101713"
        assert not win.welcome_card.isHidden()

        # Le masquage du guide de premier lancement est persisté dans settings.json
        win._dismiss_welcome()
        assert settings_store.get().onboarding_dismissed is True
        assert win.welcome_card.isHidden()

        # L'alias historique "analyzer" redirige proprement vers l'onglet Analyse de Créateurs
        win.go_to("analyzer")
        app.processEvents()
        assert win.stack.currentWidget() is win._pages["creators"]

        # Redimensionnement adaptatif (mode rail compact < 960 px puis retour normal)
        win.resize(940, 660)
        app.processEvents()
        assert win._compact is True
        win.resize(1280, 860)
        app.processEvents()
        assert win._compact is False

        win.go_to("home")
        app.processEvents()
        assert win.stack.currentWidget() is win._pages["home"]

        win.toggle_theme()
        app.processEvents()
        assert settings_store.get().theme == "light"
        assert win.tokens.text == palette("light", "forest").text

        win.set_appearance(accent="blue", ui_scale="large")
        app.processEvents()
        prefs = settings_store.get()
        assert prefs.accent == "blue"
        assert prefs.ui_scale == "large"
        assert win.tokens.accent_key == "blue"

        win.toggle_theme()
        app.processEvents()
        assert settings_store.get().theme == "dark"

        win.close()
        win.deleteLater()
        app.processEvents()


def test_desktop_download_from_composer_and_custom_name(server, tmp_path):
    from overload.downloads.manager import DownloadManager
    from overload.history.store import DownloadHistoryStore
    from overload.settings.store import SettingsStore
    from overload.ui.desktop import create_main_window

    app = _make_app()
    settings_store = SettingsStore(tmp_path / "settings.json")
    with (
        DownloadHistoryStore(tmp_path / "library.db") as history,
        DownloadManager(
            tmp_path / "downloads", history=history, allow_private_hosts=True
        ) as manager,
    ):
        win = create_main_window(manager, history, settings_store, data_dir=tmp_path)
        win.show()
        app.processEvents()

        win.go_to("downloads")
        win.dl_url_edit.setText(f"{server}/ok.bin")
        win.name_edit.setText("mon-rush.bin")
        app.processEvents()
        assert win.url_edit.text() == f"{server}/ok.bin"
        win.download_from_composer()
        app.processEvents()

        assert win.url_edit.text() == ""
        assert win.dl_url_edit.text() == ""
        assert len(manager.list_tasks()) == 1
        assert manager.list_tasks()[0].filename == "mon-rush.bin"
        assert manager.wait_all(timeout=10)
        assert (tmp_path / "downloads" / "mon-rush.bin").is_file()
        win.refresh_all()
        app.processEvents()
        win.close()
        win.deleteLater()
        app.processEvents()


def test_desktop_failure_is_explained_in_french_with_recovery_button(tmp_path):
    from overload.downloads.manager import DownloadManager
    from overload.history.store import DownloadHistoryStore
    from overload.settings.store import SettingsStore
    from overload.ui.components import DownloadCard
    from overload.ui.desktop import create_main_window

    app = _make_app()
    settings_store = SettingsStore(tmp_path / "settings.json")
    with (
        DownloadHistoryStore(tmp_path / "library.db") as history,
        DownloadManager(tmp_path / "downloads", history=history) as manager,
    ):
        manager._allow_private_hosts = False
        win = create_main_window(manager, history, settings_store, data_dir=tmp_path)
        win.show()
        app.processEvents()

        snap = manager.enqueue("https://exemple.invalid/video.mp4")
        assert snap is not None
        assert manager.wait_all(timeout=20)
        win.refresh_all()
        app.processEvents()

        card = win._cards[snap.id]
        assert isinstance(card, DownloadCard)
        assert not card.failure.isHidden()
        assert not card.failure.recover_btn.isHidden()
        assert "Échec" not in card.failure.title.text()
        assert card.failure._info is not None
        assert card.failure._info.action
        win.close()
        win.deleteLater()
        app.processEvents()


def test_exe_entry_self_test_mode(tmp_path):
    from overload.exe_entry import main as exe_main

    report = tmp_path / "selftest.json"
    code = exe_main(["--self-test", "--self-test-out", str(report)])
    assert code == 0
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["status"] == "ok"


def test_analyzer_widget_background_result(tmp_path, monkeypatch):
    import time

    from overload.media.analyzer import Report
    from overload.ui import analyzer

    sample = tmp_path / "film.mp4"
    sample.write_bytes(b"test")
    monkeypatch.setattr(
        analyzer,
        "analyze",
        lambda path, deep: Report(
            path,
            {
                "streams": [
                    {
                        "index": 0,
                        "codec_type": "video",
                        "codec_name": "h264",
                        "width": 1920,
                        "height": 1080,
                        "avg_frame_rate": "25/1",
                    }
                ]
            },
            "Lecture test terminée",
        ),
    )
    app = _make_app()
    widget = analyzer.create_analyzer_widget()
    widget.findChild(QtWidgets.QLineEdit, "analyzerPath").setText(str(sample))
    button = widget.findChild(QtWidgets.QPushButton, "analyzerStart")
    button.click()
    assert not button.isEnabled()
    deadline = time.monotonic() + 5
    while not button.isEnabled() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert button.isEnabled()
    text = widget.findChild(QtWidgets.QPlainTextEdit, "analyzerOutput").toPlainText()
    assert "1920 × 1080" in text
    assert "25.000" in text
    assert "h264" in text
    widget.close()


def test_queue_state_persists_and_resumes_across_manager_restart(server, tmp_path):
    from overload.downloads.manager import DownloadManager
    from overload.downloads.state import TaskState
    from overload.history.store import DownloadHistoryStore

    dest = tmp_path / "downloads"
    dest.mkdir()
    state_file = tmp_path / "queue.json"
    history_db = tmp_path / "library.db"

    with DownloadHistoryStore(history_db) as history:
        with DownloadManager(
            dest,
            history=history,
            state_file=state_file,
            allow_private_hosts=True,
            speed_limit_bps=8192,
        ) as m1:
            snap = m1.enqueue(f"{server}/ok.bin", filename="reprise.bin")
            assert snap is not None
            m1.pause_task(snap.id)
        assert state_file.is_file()

        with DownloadManager(
            dest,
            history=history,
            state_file=state_file,
            allow_private_hosts=True,
        ) as m2:
            tasks = m2.list_tasks()
            assert len(tasks) == 1
            restored = tasks[0]
            assert restored.id == snap.id
            assert restored.state is TaskState.PAUSED
            m2.resume_task(restored.id)
            assert m2.wait_all(timeout=15)
            assert (dest / "reprise.bin").is_file()
