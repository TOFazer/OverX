"""Guide de premier lancement, aide contextuelle, raccourcis et journaux de diagnostic."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from overload import __version__
from overload.core.diagnostics import (
    format_diagnostic_report,
    inspect_environment,
    log_file_path,
    read_recent_logs,
)
from overload.core.paths import open_folder
from overload.ui.components import GlyphBadge, InfoBanner
from overload.ui.theme import Palette

SHORTCUTS_REFERENCE: list[tuple[str, str]] = [
    ("Ctrl+N / Ctrl+L", "Nouveau téléchargement (placer le curseur dans le champ de lien)"),
    ("Ctrl+Shift+V", "Coller immédiatement le lien du presse-papiers"),
    ("Ctrl+B", "Ouvrir l'ajout de plusieurs liens en lot"),
    ("Ctrl+F", "Rechercher dans les téléchargements, la bibliothèque ou l'historique"),
    ("Ctrl+O", "Ouvrir le dossier de destination dans l'Explorateur Windows"),
    ("Ctrl+1 … Ctrl+7", "Accéder aux 7 sections de la barre latérale"),
    ("Ctrl+,", "Ouvrir les Paramètres d'OverLoad"),
    ("F5", "Rafraîchir l'état des transferts, la bibliothèque et les diagnostics"),
    ("F1", "Ouvrir l'Aide et les raccourcis clavier"),
]

ONBOARDING_STEPS: list[tuple[str, str, str, str]] = [
    (
        "download",
        "1. Télécharger simplement et en sécurité",
        "Collez un lien direct HTTP(S) ou une vidéo YouTube publique. OverLoad vérifie l'adresse, "
        "estime ou récupère les métadonnées, gère la pause et reprend automatiquement un fichier "
        "partiel (.part) après une coupure réseau. Un téléchargement n'est annoncé « Terminé » "
        "qu'après finalisation et vérification réelle sur le disque.",
        "Astuce : appuyez sur Ctrl+N à tout moment pour saisir un nouveau lien.",
    ),
    (
        "library",
        "2. Retrouver tous vos fichiers en un clic",
        "La section Bibliothèque recense directement les médias présents dans votre dossier "
        "OverLoad et l'Historique conserve la trace de tous vos transferts après redémarrage, "
        "en indiquant si chaque fichier est toujours présent sur votre PC.",
        "Astuce : le bouton Dossier révèle et sélectionne le fichier exact "
        "dans l'Explorateur Windows.",
    ),
    (
        "film",
        "3. Préparer vos montages sans toucher aux originaux",
        "L'Espace Créateurs regroupe quatre familles d'outils : préparation d'arborescences "
        "de projets, analyse technique & points d'attention Premiere Pro / DaVinci Resolve, "
        "gestion des sous-titres (.srt) et renommage par lots avec aperçu.",
        "Garantie : aucun fichier source n'est jamais modifié, déplacé ou écrasé silencieusement.",
    ),
    (
        "sliders",
        "4. Garder la maîtrise et diagnostiquer facilement",
        "Ajustez la limite de vitesse, le nombre de transferts simultanés, le thème OverX ou "
        "la taille d'interface dans Paramètres. En cas de souci réseau ou média, chaque message "
        "indique la cause probable, l'action conseillée et l'accès au journal de diagnostic.",
        "Astuce : appuyez sur F1 à tout moment pour retrouver cette aide et vos raccourcis.",
    ),
]


class WelcomeGuideCard(QFrame):
    """Carte d'accueil de premier lancement, claire et repliable d'un clic."""

    def __init__(
        self,
        palette: Palette,
        *,
        on_start_download,
        on_open_tour,
        on_dismiss,
    ) -> None:
        super().__init__()
        self.setObjectName("guideCard")
        self._palette = palette
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(10)
        self.badge = GlyphBadge(
            "compass",
            palette,
            size=34,
            color=palette.accent,
            background=palette.accent_soft,
            icon_size=18,
        )
        head.addWidget(self.badge)
        titles = QVBoxLayout()
        titles.setSpacing(1)
        eyebrow = QLabel("BIENVENUE DANS OVERLOAD · PREMIERS PAS")
        eyebrow.setObjectName("eyebrowLabel")
        title = QLabel("Trois repères pour prendre l'application en main immédiatement")
        title.setObjectName("sectionTitle")
        titles.addWidget(eyebrow)
        titles.addWidget(title)
        head.addLayout(titles, 1)

        tour_btn = QPushButton("Guide détaillé")
        tour_btn.setObjectName("ghostBtn")
        tour_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        tour_btn.setToolTip("Parcourir la présentation guidée en 4 étapes")
        tour_btn.clicked.connect(on_open_tour)
        head.addWidget(tour_btn)

        dismiss_btn = QPushButton("Masquer")
        dismiss_btn.setObjectName("ghostBtn")
        dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dismiss_btn.setToolTip(
            "Masquer cet encart de premier lancement (réaffichable à tout moment depuis Aide)"
        )
        dismiss_btn.clicked.connect(on_dismiss)
        head.addWidget(dismiss_btn)
        layout.addLayout(head)

        steps_grid = QGridLayout()
        steps_grid.setHorizontalSpacing(12)
        steps_grid.setVerticalSpacing(8)
        steps = [
            (
                "01 · Télécharger",
                "Collez un lien YouTube ou direct ci-dessous, choisissez la "
                "destination et suivez la vitesse réelle.",
            ),
            (
                "02 · Retrouver",
                "Accédez à vos fichiers via Bibliothèque ou Historique et révélez-les "
                "dans l'Explorateur.",
            ),
            (
                "03 · Préparer le montage",
                "Inspectez codecs et durée, préparez vos dossiers Premiere / Resolve "
                "et vos sous-titres sans modifier les sources.",
            ),
        ]
        for col, (st_title, st_body) in enumerate(steps):
            box = QFrame()
            box.setObjectName("innerCard")
            b_lay = QVBoxLayout(box)
            b_lay.setContentsMargins(12, 9, 12, 9)
            b_lay.setSpacing(3)
            lbl_t = QLabel(st_title)
            lbl_t.setObjectName("cardTitle")
            lbl_b = QLabel(st_body)
            lbl_b.setObjectName("mutedLabel")
            lbl_b.setWordWrap(True)
            b_lay.addWidget(lbl_t)
            b_lay.addWidget(lbl_b)
            steps_grid.addWidget(box, 0, col)
            steps_grid.setColumnStretch(col, 1)
        layout.addLayout(steps_grid)

        actions = QHBoxLayout()
        start_btn = QPushButton("Saisir un premier lien")
        start_btn.setObjectName("secondaryBtn")
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.clicked.connect(on_start_download)
        actions.addWidget(start_btn)
        note = QLabel(
            "Raccourcis rapides : Ctrl+N nouveau lien · Ctrl+F rechercher · F1 aide et diagnostic"
        )
        note.setObjectName("tinyLabel")
        actions.addWidget(note, 1)
        layout.addLayout(actions)

    def refresh_theme(self, palette: Palette) -> None:
        self._palette = palette
        self.badge.refresh_theme(palette, palette.accent, palette.accent_soft)


class OnboardingDialog(QDialog):
    """Dialogue interactif de découverte d'OverLoad en 4 étapes."""

    def __init__(self, parent: QWidget, palette: Palette) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Découvrir OverLoad {__version__}")
        self.resize(620, 380)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        self.stack = QStackedWidget()
        for icon_name, title_txt, body_txt, tip_txt in ONBOARDING_STEPS:
            slide = QFrame()
            slide.setObjectName("panelCard")
            s_lay = QVBoxLayout(slide)
            s_lay.setContentsMargins(20, 18, 20, 18)
            s_lay.setSpacing(10)
            badge = GlyphBadge(
                icon_name,
                palette,
                size=44,
                color=palette.accent,
                background=palette.accent_soft,
                icon_size=22,
            )
            s_lay.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
            h_lbl = QLabel(title_txt)
            h_lbl.setObjectName("pageTitle")
            h_lbl.setWordWrap(True)
            s_lay.addWidget(h_lbl)
            p_lbl = QLabel(body_txt)
            p_lbl.setObjectName("mutedLabel")
            p_lbl.setWordWrap(True)
            s_lay.addWidget(p_lbl)
            s_lay.addStretch()
            tip = QLabel(tip_txt)
            tip.setObjectName("tinyLabel")
            tip.setWordWrap(True)
            s_lay.addWidget(tip)
            self.stack.addWidget(slide)
        layout.addWidget(self.stack, 1)

        nav = QHBoxLayout()
        self.step_label = QLabel("")
        self.step_label.setObjectName("mutedLabel")
        self.prev_btn = QPushButton("Précédent")
        self.prev_btn.setObjectName("ghostBtn")
        self.next_btn = QPushButton("Suivant")
        self.next_btn.setObjectName("primaryBtn")
        nav.addWidget(self.step_label)
        nav.addStretch()
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.next_btn)
        layout.addLayout(nav)

        self.prev_btn.clicked.connect(self._prev)
        self.next_btn.clicked.connect(self._next)
        self._sync_nav()

    def _prev(self) -> None:
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
            self._sync_nav()

    def _next(self) -> None:
        idx = self.stack.currentIndex()
        if idx + 1 < self.stack.count():
            self.stack.setCurrentIndex(idx + 1)
            self._sync_nav()
        else:
            self.accept()

    def _sync_nav(self) -> None:
        idx = self.stack.currentIndex()
        total = self.stack.count()
        self.step_label.setText(f"Étape {idx + 1} sur {total}")
        self.prev_btn.setEnabled(idx > 0)
        self.next_btn.setText("Terminer" if idx + 1 == total else "Suivant")


class HelpPage(QWidget):
    """Page « Aide » : repères d'usage, raccourcis clavier et diagnostic complet."""

    def __init__(self, window: Any) -> None:
        super().__init__()
        self.window = window

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(26, 20, 26, 26)
        layout.setSpacing(16)

        # 1. Guide rapide & premier lancement
        top_card = QFrame()
        top_card.setObjectName("panelCard")
        top_layout = QVBoxLayout(top_card)
        top_layout.setContentsMargins(20, 18, 20, 18)
        top_layout.setSpacing(10)
        head_row = QHBoxLayout()
        head_col = QVBoxLayout()
        head_col.setSpacing(2)
        h_title = QLabel("Prise en main rapide d'OverLoad")
        h_title.setObjectName("sectionTitle")
        h_sub = QLabel(
            "Tout ce qu'il faut savoir sur les liens acceptés, la reprise réseau, "
            "l'Espace Créateurs et les vérifications de diagnostic."
        )
        h_sub.setObjectName("mutedLabel")
        h_sub.setWordWrap(True)
        head_col.addWidget(h_title)
        head_col.addWidget(h_sub)
        head_row.addLayout(head_col, 1)

        replay_btn = QPushButton("Ouvrir le guide de premier lancement")
        replay_btn.setObjectName("primaryBtn")
        replay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        replay_btn.setToolTip(
            "Afficher la visite guidée en 4 étapes et réactiver la carte d'accueil"
        )
        replay_btn.clicked.connect(self.window.open_onboarding_guide)
        head_row.addWidget(replay_btn)
        top_layout.addLayout(head_row)

        faq_grid = QGridLayout()
        faq_grid.setHorizontalSpacing(12)
        faq_grid.setVerticalSpacing(12)
        guides = [
            (
                "Liens pris en charge & sécurité",
                "OverLoad accepte les fichiers HTTP/HTTPS directs et les vidéos YouTube publiques "
                "(MP4 via yt-dlp et FFmpeg). Il bloque les schémas dangereux "
                "(file://, javascript:), "
                "les adresses locales non autorisées et ne contourne ni DRM ni accès restreint.",
            ),
            (
                "Pause, reprise & fichiers incomplets",
                "Les octets en cours sont écrits dans un fichier temporaire .part. Un transfert "
                "n'est validé « Terminé » qu'une fois la taille vérifiée (et la piste "
                "vidéo contrôlée "
                "pour YouTube). Après redémarrage, les transferts interrompus sont "
                "restaurés en pause.",
            ),
            (
                "Espace Créateurs & Premiere Pro",
                "Les outils Créateurs opèrent par copie ou après aperçu explicite "
                "sans modifier vos "
                "originaux. L'analyse signale les conteneurs (MKV/WebM), codecs "
                "(HEVC/AV1) ou cadences "
                "variables susceptibles de gêner Premiere Pro, sans certifier l'import à sa place.",
            ),
            (
                "Données locales & mises à jour",
                "Vos réglages (settings.json), la file (queue.json), vos projets créateurs et "
                "l'historique SQLite (library.db) sont conservés dans votre dossier utilisateur ou "
                "dans OverLoad-data/ en mode portable, y compris lors d'une mise à jour.",
            ),
        ]
        for idx, (g_title, g_body) in enumerate(guides):
            card = QFrame()
            card.setObjectName("innerCard")
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(13, 11, 13, 11)
            c_lay.setSpacing(4)
            gt = QLabel(g_title)
            gt.setObjectName("cardTitle")
            gb = QLabel(g_body)
            gb.setObjectName("mutedLabel")
            gb.setWordWrap(True)
            c_lay.addWidget(gt)
            c_lay.addWidget(gb)
            faq_grid.addWidget(card, idx // 2, idx % 2)
            faq_grid.setColumnStretch(0, 1)
            faq_grid.setColumnStretch(1, 1)
        top_layout.addLayout(faq_grid)
        layout.addWidget(top_card)

        # 2. Raccourcis clavier
        sc_card = QFrame()
        sc_card.setObjectName("panelCard")
        sc_layout = QVBoxLayout(sc_card)
        sc_layout.setContentsMargins(20, 16, 20, 16)
        sc_layout.setSpacing(8)
        sc_title = QLabel("Raccourcis clavier")
        sc_title.setObjectName("sectionTitle")
        sc_layout.addWidget(sc_title)
        sc_grid = QGridLayout()
        sc_grid.setHorizontalSpacing(16)
        sc_grid.setVerticalSpacing(7)
        for row_idx, (keys, desc) in enumerate(SHORTCUTS_REFERENCE):
            key_lbl = QLabel(keys)
            key_lbl.setObjectName("kbdBadge")
            desc_lbl = QLabel(desc)
            desc_lbl.setObjectName("mutedLabel")
            desc_lbl.setWordWrap(True)
            sc_grid.addWidget(key_lbl, row_idx, 0, Qt.AlignmentFlag.AlignLeft)
            sc_grid.addWidget(desc_lbl, row_idx, 1)
        sc_grid.setColumnStretch(1, 1)
        sc_layout.addLayout(sc_grid)
        layout.addWidget(sc_card)

        # 3. Diagnostic système & journaux
        diag_card = QFrame()
        diag_card.setObjectName("panelCard")
        diag_layout = QVBoxLayout(diag_card)
        diag_layout.setContentsMargins(20, 18, 20, 18)
        diag_layout.setSpacing(10)

        diag_head = QHBoxLayout()
        diag_titles = QVBoxLayout()
        diag_titles.setSpacing(2)
        d_title = QLabel("Diagnostic local & journaux")
        d_title.setObjectName("sectionTitle")
        d_sub = QLabel(
            "Vérifiez la disponibilité des outils multimédias et consultez le "
            "journal local en cas d'erreur."
        )
        d_sub.setObjectName("mutedLabel")
        diag_titles.addWidget(d_title)
        diag_titles.addWidget(d_sub)
        diag_head.addLayout(diag_titles, 1)

        refresh_btn = QPushButton("Actualiser")
        refresh_btn.setObjectName("ghostBtn")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh_diagnostics)

        copy_btn = QPushButton("Copier le diagnostic")
        copy_btn.setObjectName("secondaryBtn")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setToolTip(
            "Copier l'état des outils et les dernières lignes du journal dans le presse-papiers"
        )
        copy_btn.clicked.connect(self._copy_diagnostic)

        open_logs_btn = QPushButton("Dossier des journaux")
        open_logs_btn.setObjectName("ghostBtn")
        open_logs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_logs_btn.setToolTip("Ouvrir le dossier contenant overload.log dans l'Explorateur")
        open_logs_btn.clicked.connect(
            lambda: self.window.safe_call(
                lambda: open_folder(log_file_path(self.window.data_dir).parent)
            )
        )

        diag_head.addWidget(refresh_btn)
        diag_head.addWidget(copy_btn)
        diag_head.addWidget(open_logs_btn)
        diag_layout.addLayout(diag_head)

        self.checks_host = QWidget()
        self.checks_layout = QVBoxLayout(self.checks_host)
        self.checks_layout.setContentsMargins(0, 0, 0, 0)
        self.checks_layout.setSpacing(6)
        diag_layout.addWidget(self.checks_host)

        self.log_output = QPlainTextEdit()
        self.log_output.setObjectName("diagLogOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(170)
        diag_layout.addWidget(self.log_output)

        privacy_note = InfoBanner(
            self.window.tokens,
            "info",
            "Confidentialité : aucune télémétrie externe n'est transmise. Le journal overload.log "
            "reste stocké uniquement sur cet ordinateur.",
            kind="info",
        )
        diag_layout.addWidget(privacy_note)
        layout.addWidget(diag_card)
        layout.addStretch()
        self.refresh_diagnostics()

    def refresh_diagnostics(self) -> None:
        while self.checks_layout.count():
            item = self.checks_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        checks = inspect_environment(
            data_dir=self.window.data_dir,
            destination_dir=self.window.manager.settings().destination_dir,
        )
        for entry in checks:
            row = QFrame()
            row.setObjectName("innerCard")
            r_lay = QHBoxLayout(row)
            r_lay.setContentsMargins(12, 8, 12, 8)
            r_lay.setSpacing(10)
            lbl = QLabel(entry["label"])
            lbl.setObjectName("cardTitle")
            pill = QLabel("Opérationnel" if entry["ok"] else "À vérifier")
            pill.setObjectName("statePill")
            pill.setProperty("state", "completed" if entry["ok"] else "warning")
            det = QLabel(entry["detail"])
            det.setObjectName("mutedLabel")
            det.setWordWrap(True)
            r_lay.addWidget(lbl)
            r_lay.addWidget(pill)
            r_lay.addWidget(det, 1)
            self.checks_layout.addWidget(row)

        self.log_output.setPlainText(read_recent_logs(self.window.data_dir, max_lines=100))

    def _copy_diagnostic(self) -> None:
        report = format_diagnostic_report(
            data_dir=self.window.data_dir,
            destination_dir=self.window.manager.settings().destination_dir,
        )
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(report)
        self.window.toast("Rapport de diagnostic copié dans le presse-papiers.")
