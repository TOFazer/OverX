"""Page « Bibliothèque » : retrouver, filtrer et ouvrir facilement les médias locaux."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from overload.core.formatting import format_bytes
from overload.core.paths import open_folder
from overload.creators.fsutil import classify_file, iter_media_files
from overload.creators.models import MediaKind
from overload.ui import icons
from overload.ui.components import (
    ElidedLabel,
    EmptyState,
    IconButton,
    SegmentedControl,
    Thumbnail,
    ThumbnailService,
    host_of,
    human_time_ago,
    kind_of,
)
from overload.ui.theme import Palette


@dataclass(frozen=True)
class LibraryEntry:
    path: Path
    kind: MediaKind
    size_bytes: int
    modified_iso: str
    source_url: str = ""


class LibraryRow(QFrame):
    """Carte compacte d'un fichier présent dans la bibliothèque locale."""

    def __init__(
        self,
        item: LibraryEntry,
        palette: Palette,
        thumbnails: ThumbnailService,
        *,
        on_open_explorer,
        on_analyze,
        on_tracks,
        on_prepare,
        scale: float = 1.0,
    ) -> None:
        super().__init__()
        self.item = item
        self._palette = palette
        self._thumbnails = thumbnails
        self.setObjectName("libraryCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            round(13 * scale), round(10 * scale), round(13 * scale), round(10 * scale)
        )
        layout.setSpacing(round(12 * scale))

        self.thumb = Thumbnail(palette, width=round(68 * scale), height=round(48 * scale))
        self.thumb.set_source(item.path.name, item.path)
        layout.addWidget(self.thumb, 0, Qt.AlignmentFlag.AlignVCenter)

        info = QVBoxLayout()
        info.setSpacing(3)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.name = ElidedLabel(item.path.name)
        self.name.setObjectName("cardTitle")
        top.addWidget(self.name, 1)

        self.kind_badge = QLabel(item.kind.label)
        self.kind_badge.setObjectName("formatChip")
        top.addWidget(self.kind_badge, 0)
        info.addLayout(top)

        parts = [
            format_bytes(item.size_bytes),
            human_time_ago(item.modified_iso) or "local",
            item.path.parent.name or str(item.path.parent),
        ]
        if item.source_url:
            src_host = host_of(item.source_url)
            if src_host:
                parts.append(f"source : {src_host}")
        self.meta = ElidedLabel("  ·  ".join(parts))
        self.meta.setObjectName("mutedLabel")
        self.meta.setToolTip(str(item.path))
        info.addWidget(self.meta)
        layout.addLayout(info, 1)

        actions = QHBoxLayout()
        actions.setSpacing(6)

        self.analyze_btn = QPushButton("Analyser")
        self.analyze_btn.setObjectName("ghostBtn")
        self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analyze_btn.setToolTip(
            "Inspecter le format, la résolution, la durée et la compatibilité montage"
        )
        self.analyze_btn.clicked.connect(lambda: on_analyze(item.path))
        actions.addWidget(self.analyze_btn)

        self.project_btn = QPushButton("Projet")
        self.project_btn.setObjectName("ghostBtn")
        self.project_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.project_btn.setToolTip(
            "Envoyer vers « Préparer mon projet » (copie triée sans modifier l'original)"
        )
        self.project_btn.clicked.connect(lambda: on_prepare(item.path))
        actions.addWidget(self.project_btn)

        self.tracks_btn = IconButton(
            "subtitles",
            "Gérer ou extraire les sous-titres et pistes audio",
            palette,
        )
        self.tracks_btn.clicked.connect(lambda: on_tracks(item.path))
        actions.addWidget(self.tracks_btn)

        self.open_btn = IconButton(
            "folder",
            "Afficher le fichier dans l'Explorateur Windows",
            palette,
        )
        self.open_btn.clicked.connect(lambda: on_open_explorer(item.path))
        actions.addWidget(self.open_btn)

        layout.addLayout(actions)

        if kind_of(item.path.name) in {"image", "video"} and self.thumb.mark_requested():
            self._thumbnails.request(item.path, self.thumb.set_pixmap)

    def refresh_theme(self, palette: Palette) -> None:
        self._palette = palette
        self.thumb.refresh_theme(palette)
        self.tracks_btn.refresh_theme(palette)
        self.open_btn.refresh_theme(palette)


class LibraryPage(QWidget):
    """Explorateur rapide des fichiers téléchargés dans le dossier actif d'OverLoad."""

    def __init__(self, window: Any) -> None:
        super().__init__()
        self.window = window
        self._kind_filter = "all"
        self._sort_by = "recent"
        self._query = ""
        self._rows: list[LibraryRow] = []
        self._sig: tuple[Any, ...] | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(26, 18, 26, 22)
        outer.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.filters = SegmentedControl(
            [
                ("all", "Tous"),
                (MediaKind.VIDEO.value, "Vidéos"),
                (MediaKind.AUDIO.value, "Audio"),
                (MediaKind.IMAGE.value, "Images"),
                (MediaKind.SUBTITLE.value, "Sous-titres"),
                (MediaKind.OTHER.value, "Autres"),
            ],
            window.tokens,
        )
        self.filters.value_changed.connect(self._on_filter)
        toolbar.addWidget(self.filters)
        toolbar.addStretch()

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Plus récents d'abord", "recent")
        self.sort_combo.addItem("Nom (A → Z)", "name")
        self.sort_combo.addItem("Taille décroissante", "size")
        self.sort_combo.setToolTip("Ordre d'affichage des fichiers de la bibliothèque")
        self.sort_combo.currentIndexChanged.connect(self._on_sort)
        toolbar.addWidget(self.sort_combo)

        self.refresh_btn = IconButton(
            "refresh", "Actualiser la lecture du dossier (F5)", window.tokens
        )
        self.refresh_btn.clicked.connect(lambda: self.refresh_items(force=True))
        toolbar.addWidget(self.refresh_btn)

        self.open_dir_btn = QPushButton("Ouvrir le dossier")
        self.open_dir_btn.setObjectName("secondaryBtn")
        self.open_dir_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_dir_btn.setIcon(icons.icon("folder", window.tokens.accent, 16))
        self.open_dir_btn.setToolTip(
            "Ouvrir le dossier des téléchargements dans l'Explorateur (Ctrl+O)"
        )
        self.open_dir_btn.clicked.connect(
            lambda: window.safe_call(window.manager.open_downloads_folder)
        )
        toolbar.addWidget(self.open_dir_btn)
        outer.addLayout(toolbar)

        summary_bar = QHBoxLayout()
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("mutedLabel")
        self.folder_label = ElidedLabel("")
        self.folder_label.setObjectName("tinyLabel")
        summary_bar.addWidget(self.summary_label)
        summary_bar.addStretch()
        summary_bar.addWidget(self.folder_label, 1)
        outer.addLayout(summary_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        scroll.setWidget(host)
        self.list_layout = QVBoxLayout(host)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(8)

        self.empty_state = EmptyState(
            window.tokens,
            "library",
            "Aucun fichier dans votre bibliothèque",
            "Les médias présents dans votre dossier OverLoad apparaissent automatiquement ici, "
            "prêts à être ouverts, analysés ou rangés dans un projet.",
            action_text="Nouveau téléchargement",
            on_action=window.focus_composer,
        )
        self.list_layout.addWidget(self.empty_state)
        self.list_layout.addStretch()
        outer.addWidget(scroll, 1)

    def set_search_query(self, query: str) -> None:
        self._query = query.strip()
        self.refresh_items(force=True)

    def _on_filter(self, key: str) -> None:
        self._kind_filter = key
        self.refresh_items(force=True)

    def _on_sort(self, _index: int) -> None:
        self._sort_by = str(self.sort_combo.currentData() or "recent")
        self.refresh_items(force=True)

    def scan_local_files(self) -> list[LibraryEntry]:
        dest = Path(self.window.manager.settings().destination_dir)
        if not dest.is_dir():
            return []
        source_map: dict[Path, str] = {}
        for h in self.window._history_all:
            if h.url:
                try:
                    source_map.setdefault(Path(h.destination_path).resolve(), h.url)
                except OSError:
                    continue
        entries: list[LibraryEntry] = []
        for path in iter_media_files(dest, recursive=True):
            try:
                st = path.stat()
                resolved = path.resolve()
            except OSError:
                continue
            modified_iso = datetime.fromtimestamp(st.st_mtime, tz=UTC).isoformat()
            entries.append(
                LibraryEntry(
                    path=path,
                    kind=classify_file(path),
                    size_bytes=st.st_size,
                    modified_iso=modified_iso,
                    source_url=source_map.get(resolved, ""),
                )
            )
        return entries

    def refresh_items(self, *, force: bool = False) -> int:
        dest = Path(self.window.manager.settings().destination_dir)
        self.folder_label.setText(f"Dossier surveillé : {dest}")
        all_items = self.scan_local_files()
        needle = self._query.casefold()
        filtered = [
            item
            for item in all_items
            if (self._kind_filter == "all" or item.kind.value == self._kind_filter)
            and (
                not needle
                or needle in item.path.name.casefold()
                or needle in item.source_url.casefold()
            )
        ]
        if self._sort_by == "name":
            filtered.sort(key=lambda x: x.path.name.casefold())
        elif self._sort_by == "size":
            filtered.sort(key=lambda x: x.size_bytes, reverse=True)
        else:
            filtered.sort(key=lambda x: x.modified_iso, reverse=True)

        visible = filtered[:200]
        sig = (
            tuple((str(i.path), i.size_bytes, i.modified_iso) for i in visible),
            len(all_items),
            self._kind_filter,
            self._sort_by,
            needle,
        )
        if not force and sig == self._sig:
            return len(all_items)
        self._sig = sig

        for old in self._rows:
            self.list_layout.removeWidget(old)
            old.hide()
            old.setParent(None)
            old.deleteLater()
        self._rows.clear()

        for idx, item in enumerate(visible):
            row = LibraryRow(
                item,
                self.window.tokens,
                self.window.thumbnails,
                on_open_explorer=lambda p: self.window.safe_call(lambda: open_folder(p)),
                on_analyze=self.window.open_file_in_analyzer,
                on_tracks=self.window.open_file_in_tracks,
                on_prepare=self.window.open_file_in_prepare,
                scale=self.window.scale,
            )
            self.list_layout.insertWidget(idx + 1, row)
            self._rows.append(row)

        total_bytes = sum(i.size_bytes for i in all_items)
        if all_items:
            self.summary_label.setText(
                f"{len(filtered)} affiché(s) sur {len(all_items)} fichier(s) · "
                f"{format_bytes(total_bytes)} au total"
            )
        else:
            self.summary_label.setText("0 fichier dans le dossier de téléchargements")

        self.empty_state.setVisible(not visible)
        if all_items and not visible:
            self.empty_state.set_texts(
                "Aucun fichier correspondant",
                "Aucun média de votre bibliothèque ne correspond à ce filtre ou à cette recherche.",
                "Réinitialiser le filtre",
            )
        else:
            self.empty_state.set_texts(
                "Aucun fichier dans votre bibliothèque",
                "Les médias téléchargés dans votre dossier OverLoad apparaissent automatiquement "
                "ici pour être ouverts dans l'Explorateur, analysés ou rangés dans un projet.",
                "Nouveau téléchargement",
            )
        return len(all_items)

    def refresh_theme(self, palette: Palette) -> None:
        self.filters.refresh_theme(palette)
        self.refresh_btn.refresh_theme(palette)
        self.open_dir_btn.setIcon(icons.icon("folder", palette.accent, 16))
        self.empty_state.badge.refresh_theme(palette, palette.accent, palette.accent_soft)
        for row in self._rows:
            row.refresh_theme(palette)
