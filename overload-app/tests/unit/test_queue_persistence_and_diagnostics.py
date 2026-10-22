from __future__ import annotations

import json

from overload.core.diagnostics import (
    format_diagnostic_report,
    inspect_environment,
    log_event,
    log_file_path,
    read_recent_logs,
)
from overload.downloads.manager import DownloadManager
from overload.downloads.state import TaskState


def test_queue_state_reads_partial_bytes_from_disk(tmp_path):
    dest = tmp_path / "downloads"
    dest.mkdir()
    state_file = tmp_path / "queue.json"
    (dest / "rush-4k.mp4.part").write_bytes(b"x" * 4096)
    state_file.write_text(
        json.dumps(
            {
                "version": 1,
                "tasks": [
                    {
                        "id": "task-persist-1",
                        "url": "https://cdn.exemple.fr/rush-4k.mp4",
                        "filename": "rush-4k.mp4",
                        "destination_dir": str(dest),
                        "provider": "http",
                        "quality": "best",
                        "state": "running",
                        "total_bytes": 16384,
                        "downloaded_bytes": 2048,
                        "created_at": "2026-10-22T10:00:00+00:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with DownloadManager(dest, state_file=state_file) as manager:
        tasks = manager.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].state is TaskState.PAUSED
        assert tasks[0].downloaded_bytes == 4096


def test_corrupted_queue_file_never_crashes_startup(tmp_path):
    dest = tmp_path / "downloads"
    state_file = tmp_path / "queue.json"
    state_file.write_text("{json invalide...", encoding="utf-8")

    with DownloadManager(dest, state_file=state_file) as manager:
        assert manager.list_tasks() == []


def test_diagnostics_logging_and_environment_report(tmp_path):
    data_dir = tmp_path / "data"
    dest_dir = tmp_path / "downloads"
    dest_dir.mkdir(parents=True)

    log_event("Démarrage du test de diagnostic", data_dir=data_dir)
    assert log_file_path(data_dir).is_file()
    recent = read_recent_logs(data_dir)
    assert "Démarrage du test de diagnostic" in recent

    checks = inspect_environment(data_dir=data_dir, destination_dir=dest_dir)
    labels = {c["label"] for c in checks}
    assert "Dossier de téléchargements" in labels
    assert "Extracteur YouTube (yt-dlp)" in labels

    report = format_diagnostic_report(data_dir=data_dir, destination_dir=dest_dir)
    assert "Rapport de diagnostic local" in report
    assert "Démarrage du test de diagnostic" in report
