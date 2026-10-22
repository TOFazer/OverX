"""Outil d'analyse multimédia locale : exécution hors du fil graphique et diagnostic montage."""

from __future__ import annotations

import queue
import threading
from pathlib import Path

from overload.core.formatting import format_bytes, format_duration
from overload.media.analyzer import Report, analyze, fps, number
from overload.ui.components import LoadingStrip, ToolIntroCard
from overload.ui.filedialogs import choose_open_file
from overload.ui.theme import palette as build_palette


def _premiere_assessment(metadata: dict, issues: list[str]) -> tuple[str, str]:
    """Synthèse prudente et factuelle pour l'import en montage (Premiere Pro / Resolve)."""
    streams = metadata.get("streams", [])
    fmt_names = str(metadata.get("format", {}).get("format_name", "")).lower().split(",")
    has_media = any(s.get("codec_type") in {"video", "audio"} for s in streams)
    if not metadata or not has_media:
        return (
            "À vérifier",
            "Métadonnées incomplètes : lancez l'analyse pour inspecter les codecs réels.",
        )
    flagged_containers = {"matroska", "webm", "ogg", "flv"}
    if any(c in flagged_containers for c in fmt_names):
        return (
            "Remuxage conseillé",
            "Conteneur MKV/WebM/OGG : certains monteurs (dont Premiere Pro) le "
            "refusent même si les codecs internes sont standards.",
        )
    real_warnings = [item for item in issues if not item.startswith("Même une lecture sans erreur")]
    if real_warnings:
        return (
            f"{len(real_warnings)} point(s) d'attention",
            real_warnings[0].splitlines()[0],
        )
    return (
        "Standards courants détectés",
        "Conteneur et codecs usuels (sous réserve de la version exacte de Premiere Pro / Resolve).",
    )


def create_analyzer_widget(*, fallback_dir: Path | None = None):
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import (
        QCheckBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

    tokens = build_palette()
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(6, 6, 6, 6)
    layout.setSpacing(10)

    intro = ToolIntroCard(
        "Analyser un fichier & vérifier pour Premiere Pro / le montage",
        "Inspecte localement le conteneur, la résolution, la cadence, la durée, les pistes audio "
        "et sous-titres, puis signale les incompatibilités fréquentes avant l'import au montage.",
        accepted="Vidéos et audios locaux (.mp4, .mov, .mkv, .webm, .wav, .mp3, .flac, .aac…)",
        effect=(
            "Lecture seule hors ligne via FFprobe (et test de décodage complet "
            "optionnel via FFmpeg)"
        ),
        limits=(
            "Le fichier source n'est jamais modifié. Les indications Premiere Pro "
            "sont basées sur les codecs mesurés, sans jamais certifier l'import à "
            "la place du logiciel."
        ),
    )
    layout.addWidget(intro)

    form_card = QFrame()
    form_card.setObjectName("panelCard")
    form_layout = QVBoxLayout(form_card)
    form_layout.setContentsMargins(14, 12, 14, 12)
    form_layout.setSpacing(8)

    row = QHBoxLayout()
    row.setSpacing(8)
    path = QLineEdit()
    path.setPlaceholderText("Choisissez un fichier vidéo ou audio sur votre ordinateur…")
    path.setObjectName("analyzerPath")
    path.setToolTip("Chemin complet du fichier multimédia local à inspecter")
    browse = QPushButton("Parcourir…")
    browse.setObjectName("ghostBtn")
    browse.setToolTip("Sélectionner un fichier vidéo ou audio local")
    start = QPushButton("Analyser le fichier")
    start.setObjectName("analyzerStart")
    start.setProperty("primary", True)
    start.setToolTip("Lancer l'inspection technique sans modifier le fichier source")
    row.addWidget(path, 1)
    row.addWidget(browse)
    row.addWidget(start)
    form_layout.addLayout(row)

    opts_row = QHBoxLayout()
    deep = QCheckBox(
        "Vérifier la lecture complète audio/vidéo (détecte les fichiers tronqués, plus lent)"
    )
    deep.setChecked(True)
    deep.setToolTip(
        "Décode l'intégralité des flux audio et vidéo vers une sortie nulle "
        "pour repérer les passages corrompus."
    )
    opts_row.addWidget(deep)
    opts_row.addStretch()
    status = QLabel("Prêt à analyser un fichier.")
    status.setObjectName("analyzerStatus")
    status.setTextFormat(Qt.TextFormat.PlainText)
    opts_row.addWidget(status)
    form_layout.addLayout(opts_row)
    layout.addWidget(form_card)

    loading = LoadingStrip(tokens, "Analyse en cours… L'interface reste entièrement disponible.")
    layout.addWidget(loading)

    summary_frame = QFrame()
    summary_frame.setObjectName("innerCard")
    summary_grid = QGridLayout(summary_frame)
    summary_grid.setContentsMargins(12, 10, 12, 10)
    summary_grid.setHorizontalSpacing(14)
    summary_grid.setVerticalSpacing(4)

    summary_values: dict[str, QLabel] = {}
    for col, (key, caption) in enumerate(
        (
            ("format", "FORMAT & DURÉE"),
            ("video", "RÉSOLUTION & CADENCE"),
            ("audio", "PISTES & AUDIO"),
            ("nle", "BILAN MONTAGE / PREMIERE PRO"),
        )
    ):
        cap = QLabel(caption)
        cap.setObjectName("statCaption")
        val = QLabel("—")
        val.setObjectName("cardTitle")
        val.setWordWrap(True)
        summary_grid.addWidget(cap, 0, col)
        summary_grid.addWidget(val, 1, col)
        summary_grid.setColumnStretch(col, 1)
        summary_values[key] = val
    layout.addWidget(summary_frame)

    output = QPlainTextEdit()
    output.setReadOnly(True)
    output.setObjectName("analyzerOutput")
    output.setPlaceholderText(
        "Le rapport détaillé (conteneur, pistes vidéo/audio/sous-titres, "
        "débits et points de vigilance pour le montage) s'affichera ici."
    )
    layout.addWidget(output, 1)

    footer = QHBoxLayout()
    why = QPushButton("Pourquoi ce fichier pose-t-il problème ?")
    why.setObjectName("secondaryBtn")
    why.setEnabled(False)
    why.setToolTip("Afficher l'explication complète des alertes détectées")
    footer.addStretch()
    footer.addWidget(why)
    layout.addLayout(footer)

    results: queue.Queue = queue.Queue()
    report: Report | None = None

    def choose():
        filename = choose_open_file(
            widget,
            "Choisir un média à analyser",
            preferred=path.text().strip() or None,
            fallback=fallback_dir,
        )
        if filename:
            path.setText(filename)

    def work(filename, full):
        try:
            results.put(analyze(Path(filename), deep=full))
        except Exception as exc:  # noqa: BLE001
            results.put(str(exc))

    def launch():
        nonlocal report
        if not path.text().strip():
            status.setText("Choisissez d'abord un fichier.")
            return
        report = None
        why.setEnabled(False)
        for control in (start, browse, path, deep):
            control.setEnabled(False)
        output.clear()
        status.setText("Analyse en cours… L'interface reste disponible.")
        loading.start("Inspection FFprobe / FFmpeg en cours — le fichier source reste intact…")
        threading.Thread(target=work, args=(path.text(), deep.isChecked()), daemon=True).start()
        timer.start()

    def collect():
        nonlocal report
        try:
            result = results.get_nowait()
        except queue.Empty:
            return
        timer.stop()
        loading.stop()
        for control in (start, browse, path, deep):
            control.setEnabled(True)
        if not isinstance(result, Report):
            status.setText("Analyse impossible : " + result)
            return
        report = result
        status.setText(result.integrity)
        fmt = result.metadata.get("format", {})
        streams = result.metadata.get("streams", [])
        dur_num = number(fmt.get("duration"))
        size_txt = format_bytes(result.path.stat().st_size) if result.path.is_file() else "—"
        summary_values["format"].setText(
            f"{result.path.suffix.lstrip('.').upper() or fmt.get('format_name', 'Média')} · "
            f"{format_duration(dur_num) if dur_num else 'durée inconnue'} ({size_txt})"
        )
        v_streams = [s for s in streams if s.get("codec_type") == "video"]
        a_streams = [s for s in streams if s.get("codec_type") == "audio"]
        s_streams = [s for s in streams if s.get("codec_type") == "subtitle"]
        if v_streams:
            v0 = v_streams[0]
            cad = fps(v0.get("avg_frame_rate"))
            summary_values["video"].setText(
                f"{v0.get('width', '?')} × {v0.get('height', '?')} · "
                f"{v0.get('codec_name', '?').upper()}" + (f" · {cad:.2f} i/s" if cad else "")
            )
        else:
            summary_values["video"].setText("Aucune piste vidéo")
        audio_info = (
            f"{len(a_streams)} audio ({a_streams[0].get('codec_name', '?').upper()})"
            if a_streams
            else "0 audio"
        )
        summary_values["audio"].setText(f"{audio_info} · {len(s_streams)} sous-titres")
        verdict, detail_short = _premiere_assessment(result.metadata, result.issues)
        summary_values["nle"].setText(verdict)
        summary_values["nle"].setToolTip(detail_short)

        lines = [
            str(result.path),
            f"Conteneur : {fmt.get('format_long_name', 'Inconnu')}",
            f"Durée : {fmt.get('duration', 'Inconnue')} s",
            f"Débit global : {_bitrate(fmt.get('bit_rate'))}",
            f"Bilan montage : {verdict} — {detail_short}",
            "",
            "PISTES DISPONIBLES",
        ]
        for stream in streams:
            tags = stream.get("tags", {})
            disposition = stream.get("disposition", {})
            lines.append(
                f"\n#{stream.get('index', '?')} — {stream.get('codec_type', '?')} — "
                f"{stream.get('codec_long_name', stream.get('codec_name', 'Inconnu'))}"
            )
            lines.append(
                f"Langue : {tags.get('language', 'non précisée')} | "
                f"Titre : {tags.get('title', '—')} | "
                f"Par défaut : {'oui' if disposition.get('default') else 'non'} | "
                f"Forcée : {'oui' if disposition.get('forced') else 'non'}"
            )
            if stream.get("codec_type") == "video":
                cadence = fps(stream.get("avg_frame_rate"))
                lines.append(
                    f"Résolution : {stream.get('width', '?')} × {stream.get('height', '?')} | "
                    f"FPS moyens : {f'{cadence:.3f}' if cadence else 'inconnus'} | "
                    f"Couleur : {stream.get('pix_fmt', '?')}"
                )
            if stream.get("codec_type") == "audio":
                lines.append(
                    f"Canaux : {stream.get('channels', '?')} "
                    f"({stream.get('channel_layout', '?')}) | "
                    f"Échantillonnage : {stream.get('sample_rate', '?')} Hz"
                )
            lines.append(f"Débit piste : {_bitrate(stream.get('bit_rate'))}")
        output.setPlainText("\n".join(lines) + "\n\nDIAGNOSTIC\n" + result.explanation())
        why.setEnabled(True)

    def explain():
        if report:
            dialog = QMessageBox(widget)
            dialog.setWindowTitle("Comprendre le diagnostic")
            dialog.setTextFormat(Qt.TextFormat.PlainText)
            dialog.setText(report.explanation())
            dialog.exec()

    def load_media_file(target: str | Path, *, auto_start: bool = False) -> None:
        path.setText(str(target))
        if auto_start:
            launch()

    timer = QTimer(widget)
    timer.setInterval(100)
    timer.timeout.connect(collect)
    browse.clicked.connect(choose)
    start.clicked.connect(launch)
    why.clicked.connect(explain)
    widget.load_media_file = load_media_file  # type: ignore[attr-defined]
    return widget


def _bitrate(value):
    rate = number(value)
    return f"{rate / 1000:,.0f} kbit/s" if rate else "Non renseigné"
