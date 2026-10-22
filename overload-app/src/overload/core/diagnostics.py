"""Journal de diagnostic local et rapport d'état système d'OverLoad.

Aucun envoi réseau : les journaux restent exclusivement dans le dossier de
données local (`logs/overload.log`) avec rotation automatique afin de ne jamais
encombrer le disque.
"""

from __future__ import annotations

import logging
import platform
import shutil
import sys
import threading
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from overload import __version__
from overload.core.formatting import format_bytes
from overload.core.paths import default_data_dir

LOG_FILENAME = "overload.log"
MAX_LOG_BYTES = 512 * 1024
BACKUP_COUNT = 2

_LOCK = threading.RLock()
_CONFIGURED_PATH: Path | None = None


def log_file_path(data_dir: Path | str | None = None) -> Path:
    base = Path(data_dir) if data_dir is not None else default_data_dir()
    logs_dir = base / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / LOG_FILENAME


def get_logger(data_dir: Path | str | None = None) -> logging.Logger:
    """Retourne le journal applicatif configuré sur `data_dir/logs/overload.log`."""
    global _CONFIGURED_PATH
    logger = logging.getLogger("overload")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    target = log_file_path(data_dir)
    with _LOCK:
        if _CONFIGURED_PATH != target or not logger.handlers:
            for handler in list(logger.handlers):
                try:
                    handler.close()
                except Exception:  # noqa: BLE001
                    pass
                logger.removeHandler(handler)
            try:
                file_handler = RotatingFileHandler(
                    target,
                    maxBytes=MAX_LOG_BYTES,
                    backupCount=BACKUP_COUNT,
                    encoding="utf-8",
                )
                formatter = logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
                _CONFIGURED_PATH = target
            except OSError:
                logger.addHandler(logging.NullHandler())
    return logger


def log_event(message: str, *, level: str = "info", data_dir: Path | str | None = None) -> None:
    """Enregistre un événement lisible dans le journal de diagnostic."""
    logger = get_logger(data_dir)
    method = getattr(logger, level.lower(), logger.info)
    method(message)


def read_recent_logs(data_dir: Path | str | None = None, *, max_lines: int = 120) -> str:
    """Lit les dernières lignes du journal local sans jamais lever d'exception."""
    path = log_file_path(data_dir)
    if not path.is_file():
        return "Aucun événement enregistré pour l'instant."
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return f"Lecture du journal impossible : {exc}"
    tail = lines[-max(1, max_lines) :]
    return "\n".join(tail) if tail else "Aucun événement enregistré pour l'instant."


def inspect_environment(
    *,
    data_dir: Path | str | None = None,
    destination_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Vérifie l'état réel des composants locaux (FFmpeg, FFprobe, yt-dlp, disque)."""
    from overload.media.analyzer import tool_path

    checks: list[dict[str, Any]] = []

    for label, binary in (
        ("FFprobe (analyse média)", "ffprobe"),
        ("FFmpeg (audio/vidéo)", "ffmpeg"),
    ):
        try:
            resolved = tool_path(binary)
            checks.append({"label": label, "ok": True, "detail": resolved})
        except RuntimeError as exc:
            checks.append({"label": label, "ok": False, "detail": str(exc)})

    try:
        import yt_dlp

        version = getattr(yt_dlp.version, "__version__", "installé")
        checks.append({"label": "Extracteur YouTube (yt-dlp)", "ok": True, "detail": f"v{version}"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"label": "Extracteur YouTube (yt-dlp)", "ok": False, "detail": str(exc)})

    if destination_dir is not None:
        dest = Path(destination_dir)
        exists = dest.is_dir()
        free_txt = "—"
        if exists:
            try:
                free_txt = f"{format_bytes(shutil.disk_usage(dest).free)} libres"
            except OSError:
                free_txt = "espace inconnu"
        checks.append(
            {
                "label": "Dossier de téléchargements",
                "ok": exists,
                "detail": f"{dest} ({free_txt})" if exists else f"Introuvable : {dest}",
            }
        )

    base = Path(data_dir) if data_dir is not None else default_data_dir()
    db_file = base / "library.db"
    checks.append(
        {
            "label": "Données & historique SQLite",
            "ok": base.is_dir(),
            "detail": f"{db_file} ({'présent' if db_file.is_file() else 'prêt à créer'})",
        }
    )
    return checks


def format_diagnostic_report(
    *,
    data_dir: Path | str | None = None,
    destination_dir: Path | str | None = None,
) -> str:
    """Produit un rapport texte complet prêt à copier pour le diagnostic."""
    base = Path(data_dir) if data_dir is not None else default_data_dir()
    header = [
        f"OverLoad {__version__} — Rapport de diagnostic local",
        f"Généré le : {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Système : {platform.system()} {platform.release()} ({platform.machine()})",
        "Python : "
        f"{sys.version.split()[0]} "
        f"({'exécutable compilé' if getattr(sys, 'frozen', False) else 'environnement Python'})",
        f"Dossier de données : {base}",
        "",
        "COMPOSANTS VÉRIFIÉS",
    ]
    for item in inspect_environment(data_dir=base, destination_dir=destination_dir):
        prefix = "[OK]" if item["ok"] else "[ATTENTION]"
        header.append(f"  {prefix} {item['label']} : {item['detail']}")
    header.extend(
        [
            "",
            "JOURNAL RÉCENT",
            read_recent_logs(base, max_lines=60),
        ]
    )
    return "\n".join(header)
