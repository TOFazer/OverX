#!/usr/bin/env python3
"""Build OverX's dependency-free, crawlable static website.

Project-oriented static build: applications and bots get indexable pages; each tracked
platform gets a long-tail landing page, and the head of every page carries
canonical / OpenGraph / Twitter / JSON-LD metadata. A sitemap.xml plus a
robots.txt with a Sitemap directive are written when `siteUrl` is configured
in `assets/site-config.js`.
"""
from __future__ import annotations

import json
import re
from datetime import date
from html import escape
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Public project data. OverLoad's presentation follows its public README;
# bot commands, permissions and platforms follow the FreeGameDropDev README.
# Release downloads intentionally use GitHub's stable /latest/ redirect:
# no API request, version pin, hosted binary or application updater is needed.
# ---------------------------------------------------------------------------

OVERLOAD = {
    "name": "OverLoad",
    "page": "overload/index.html",
    "short": "Télécharge des fichiers depuis des liens directs HTTP(S), analyse tes médias et prépare tes projets vidéo dans une application native Windows.",
    "source_url": "https://github.com/TOFazer/OverLoad",
    "release_url": "https://github.com/TOFazer/OverLoad/releases/latest",
    "installer_url": "https://github.com/TOFazer/OverLoad/releases/latest/download/OverLoad-Setup.exe",
    "portable_url": "https://github.com/TOFazer/OverLoad/releases/latest/download/OverLoad-Portable-win64.zip",
}

OVERLOAD_SCREENS: list[dict[str, str]] = [
    {
        "id": "accueil",
        "label": "Accueil",
        "badge": "TABLEAU DE BORD",
        "image": "assets/overload/accueil.png",
        "title": "Un accueil actionnable dès l'ouverture",
        "caption": "Colle un lien direct HTTP(S) avec validation instantanée, surveille le débit global (1,23 Mo/s), la file active, l'espace disque et tes téléchargements récents avec vignettes.",
    },
    {
        "id": "telechargements",
        "label": "Téléchargements",
        "badge": "FILE ACTIVE & REPRISE",
        "image": "assets/overload/telechargements.png",
        "title": "Suivi en temps réel et reprise HTTP Range",
        "caption": "Chaque transfert affiche sa barre de progression animée, sa vitesse glissante, le temps restant et les actions Pause, Reprendre, Relancer ou Ouvrir dans l'Explorateur.",
    },
    {
        "id": "createurs",
        "label": "Espace Créateurs",
        "badge": "MONTAGE VIDÉO",
        "image": "assets/overload/createurs.png",
        "title": "Prépare tes projets sans jamais toucher aux originaux",
        "caption": "Arborescence de montage en un clic (Premiere Pro, DaVinci Resolve, Final Cut, CapCut), renommage par lots avec aperçu, extraction de sous-titres .srt et export CSV.",
    },
    {
        "id": "historique",
        "label": "Historique",
        "badge": "DIAGNOSTIC CLAIR",
        "image": "assets/overload/historique.png",
        "title": "Présence vérifiée sur le disque et erreurs expliquées",
        "caption": "Filtre tes téléchargements passés, vérifie si chaque fichier est toujours présent sur ton PC et profite d'explications en français clair en cas d'interruption réseau.",
    },
    {
        "id": "parametres",
        "label": "Paramètres",
        "badge": "PERSONNALISATION",
        "image": "assets/overload/parametres.png",
        "title": "Thèmes, 6 couleurs d'accent et contrôle du débit",
        "caption": "Bascule entre le thème Sombre et le thème Clair, choisis parmi 6 couleurs d'accent (violet, bleu électrique, cyan, émeraude, ambre, rose) et ajuste la limite de vitesse globale.",
    },
    {
        "id": "theme-clair",
        "label": "Thème clair",
        "badge": "ACCENT BLEU ÉLECTRIQUE",
        "image": "assets/overload/theme-clair.png",
        "title": "Une interface lumineuse et contrastée pour la journée",
        "caption": "Le thème clair conserve toute la lisibilité d'OverLoad avec des surfaces blanches, des bordures douces et un accent bleu électrique commutable sans redémarrer.",
    },
]

FGD_PLATFORMS: list[dict[str, str]] = [
    {
        "slug": "steam",
        "name": "Steam",
        "icon": "🔵",
        "color": "platform-steam",
        "source": "API GamerPower",
        "channel": "#jeux-steam",
        "role": "Steam",
        "title": "Jeux gratuits Steam sur Discord — le bot FreeGameDrop | OverX",
        "description": "FreeGameDrop annonce les jeux gratuits Steam sur Discord : salon dédié #jeux-steam, rôle à la demande, prix barré et compte à rebours de fin d'offre.",
        "intro": "Steam distribue régulièrement des week-ends gratuits et des promotions limitées. FreeGameDrop les repère via l'agrégation GamerPower, puis les publie uniquement dans le salon de la plateforme, pour les membres qui ont choisi de la suivre.",
        "facts": [
            "Le rôle 🔵 Steam s'obtient en un clic sur le panneau de #choisir-ses-roles, et se retire de la même façon.",
            "Chaque annonce mentionne le rôle concerné, le prix barré, la valeur et le compte à rebours de fin d'offre.",
            "L'urgence se lit en un coup d'œil : 🟢 plus de 24 h, 🟡 moins de 24 h, 🟠 moins de 6 h, 🔴 moins d'1 h.",
            "Un jeu déjà annoncé n'est jamais publié deux fois ; /historique et /recherche retrouvent les offres passées.",
        ],
    },
    {
        "slug": "epic-games",
        "name": "Epic Games Store",
        "icon": "⚪",
        "color": "platform-epic",
        "source": "API officielle Epic + GamerPower",
        "channel": "#jeux-epic",
        "role": "Epic Games Store",
        "title": "Jeux gratuits Epic Games Store sur Discord — FreeGameDrop | OverX",
        "description": "FreeGameDrop surveille l'API officielle de l'Epic Games Store et annonce chaque jeu gratuit dans un salon Discord dédié, avec favoris et rappels d'expiration.",
        "intro": "L'Epic Games Store offre des jeux complets chaque semaine. FreeGameDrop interroge l'API officielle de la boutique en plus de GamerPower : une source en panne ne bloque jamais l'autre, et l'état de chacune reste visible avec /sante.",
        "facts": [
            "Double source : l'API officielle Epic et l'agrégation GamerPower, interrogées en parallèle à chaque vérification.",
            "Le salon #jeux-epic n'est visible qu'avec le rôle ⚪ Epic Games Store, attribué par le panneau de boutons.",
            "Un jeu complet d'au moins 19,99 € offert temporairement passe en « 🔥 Offre exceptionnelle », avec la valeur affichée par la source.",
            "Le rappel de fin d'offre (« ton jeu favori expire dans 6 heures ») s'active par membre avec /alertes.",
        ],
    },
    {
        "slug": "gog",
        "name": "GOG",
        "icon": "🟣",
        "color": "platform-gog",
        "source": "API GamerPower",
        "channel": "#jeux-gog",
        "role": "GOG",
        "title": "Jeux gratuits GOG sur Discord — FreeGameDrop | OverX",
        "description": "FreeGameDrop annonce les jeux gratuits GOG sur Discord : rôle 🟣 GOG à la demande, salon dédié en lecture seule et alertes personnelles optionnelles.",
        "intro": "Les offres GOG (jeux gratuits ponctuels et promotions) sont détectées par l'agrégation GamerPower. Comme pour les autres plateformes, la plateforme d'une offre est reconnue par mots-clés, jamais devinée.",
        "facts": [
            "Le rôle 🟣 GOG débloque le salon #jeux-gog ; sans lui, le salon reste invisible pour les membres.",
            "Les salons du bot se lisent, ils ne s'écrivent pas : lecture seule pour tout le monde, annonces signées FreeGameDrop.",
            "/preferences permet de filtrer par plateforme, type d'offre, valeur minimale et genre, pour /free et les alertes.",
            "Les offres publiques non favorites quittent le catalogue après 90 jours sans nouvelle observation.",
        ],
    },
    {
        "slug": "ubisoft",
        "name": "Ubisoft",
        "icon": "🔷",
        "color": "platform-ubisoft",
        "source": "API GamerPower",
        "channel": "#jeux-ubisoft",
        "role": "Ubisoft",
        "title": "Jeux gratuits Ubisoft sur Discord — FreeGameDrop | OverX",
        "description": "FreeGameDrop relaie les jeux gratuits et offres Ubisoft sur Discord : rôle 🔷 Ubisoft, salon dédié et rappels de fin d'offre pour ne rien manquer.",
        "intro": "Ubisoft organise régulièrement des week-ends gratuits et des offres limitées. FreeGameDrop les repère via GamerPower et les publie dans le salon de la plateforme, avec la même lisibilité que partout ailleurs.",
        "facts": [
            "Le rôle 🔷 Ubisoft s'ajoute et se retire depuis le même panneau de boutons que les autres plateformes.",
            "Chaque annonce indique la plateforme, la durée restante et un bouton « Récupérer le jeu ».",
            "/rappel-salon permet de désigner un salon qui reçoit un rappel le jour où une offre suivie se termine.",
            "Une plateforme peut être décochée dans /setup-auto : son salon est masqué, son rôle conservé, et tout reste réactivable.",
        ],
    },
]

FGD_COMMANDS: list[tuple[str, str, str]] = [
    ("/setup-auto", "Admin", "Crée ou répare catégorie, rôles, salons et panneau de sélection ; lance une première vérification."),
    ("/config", "Admin", "Rouvre le panneau de configuration de /setup-auto."),
    ("/acces-salon-roles", "Admin", "Restreint ou ouvre la visibilité de #choisir-ses-roles à des rôles précis."),
    ("/rappel-salon", "Admin", "Choisit le salon qui reçoit les rappels de fin d'offre du jour."),
    ("/test-jeux", "Admin", "Force une vérification immédiate des jeux gratuits."),
    ("/reset-jeux", "Admin", "Vide l'historique des envois : les jeux récents peuvent être réannoncés."),
    ("/reset-all", "Admin", "Supprime tout ce que le bot a créé, après confirmation."),
    ("/free", "Membres", "Parcourt les offres agrégées avec filtres (plateforme, type, échéance) et bouton favori."),
    ("/favoris", "Membres", "Consulte et gère ses offres favorites, en message privé."),
    ("/historique", "Membres", "Revoit les dernières offres connues du bot, avec les mêmes filtres que /free."),
    ("/recherche", "Membres", "Retrouve une offre déjà connue par titre ou description."),
    ("/preferences", "Membres", "Filtre plateformes, types d'offre, prix minimum et genres pour /free et les alertes."),
    ("/alertes", "Membres", "Active des alertes privées : nouvelle offre correspondante ou favori qui se termine."),
    ("/stats", "Membres", "Chiffres publics mesurés : offres détectées, actives, valeur connue, dernière vérification."),
    ("/sante", "Membres", "État mesuré du bot, de Discord, de la base et de chaque source (🟢 / 🟠 / 🔴)."),
    ("/mes-donnees", "Membres", "Supprime les favoris associés au compte Discord, après confirmation."),
    ("/info", "Membres", "Latence, nombre de serveurs et lien d'invitation construit automatiquement."),
    ("/ping", "Membres", "Vérifie que le bot répond et affiche sa latence."),
]

FGD_FAQ: list[tuple[str, str]] = [
    ("Le bot est-il vraiment gratuit ?", "Oui. Le code de FreeGameDrop est publié sous licence MIT : l'auto-hébergement est libre, et l'instance publique, quand elle est ouverte, s'ajoute sans abonnement. Le site n'invente ni tarif ni offre."),
    ("Quelles plateformes sont suivies ?", "Steam, l'Epic Games Store (via son API officielle et GamerPower), GOG et Ubisoft. La liste est extensible : ajouter une plateforme tient en une ligne de configuration côté bot."),
    ("Est-ce que tout le serveur reçoit toutes les annonces ?", "Non. Chaque plateforme a son rôle et son salon : un membre ne voit que ce qu'il a choisi. Les alertes personnelles (/alertes) partent en message privé, jamais en spam public."),
    ("Le bot lit-il les messages des membres ?", "Non. La documentation du dépôt indique que le contenu des messages n'est jamais stocké ni journalisé ; seules des données de configuration, d'offres publiques et de préférences sont conservées."),
    ("Une source tombe, que se passe-t-il ?", "Les sources sont interrogées en parallèle et une panne est isolée : les autres continuent d'alimenter les annonces. /sante affiche l'état mesuré de chacune et des alertes automatiques préviennent le propriétaire."),
    ("Comment vérifier que l'instance est en ligne ?", "Sur un serveur où le bot est installé, /sante donne son état mesuré. Le tableau de bord optionnel expose aussi /api/health, que la page Statut du site peut brancher dès qu'une URL publique est fournie."),
]

BOTS: list[dict[str, str]] = [
    {
        "slug": "freegamedrop",
        "name": "FreeGameDrop",
        "mark": "FG",
        "mark_accent": "D",
        "category": "gaming",
        "status": "Disponibilité publique à confirmer",
        "short": "Les jeux gratuits de Steam, Epic, GOG et Ubisoft annoncés automatiquement sur Discord, plateforme par plateforme.",
        "page": "discord-bots/freegamedrop/index.html",
        "og_image": "freegamedrop.png",
        "source_url": "https://github.com/TOFazer/FreeGameDropDev",
    },
]

NOINDEX = {"privacy/index.html", "terms/index.html", "legal/index.html"}


# ---------------------------------------------------------------------------
# Configuration readers
# ---------------------------------------------------------------------------

def config_source() -> str:
    path = ROOT / "assets/site-config.js"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def config_value(name: str) -> str:
    match = re.search(rf'^\s*{name}:\s*"([^"]*)"', config_source(), re.MULTILINE)
    return match.group(1).strip() if match else ""


def site_url() -> str:
    return config_value("siteUrl").rstrip("/")


def configured_install_url() -> str | None:
    """Read the public install target so generated anchors work without JavaScript too."""
    source = config_source()
    if not source:
        return None
    supplied = re.search(r'^\s*discordInstallUrl:\s*"([^"]*)"', source, re.MULTILINE)
    if supplied and supplied.group(1).strip():
        candidate = supplied.group(1).strip()
        parsed = urlsplit(candidate)
        if (
            parsed.scheme == "https"
            and parsed.hostname == "discord.com"
            and parsed.path.startswith("/oauth2/authorize")
            and parse_qs(parsed.query).get("client_id")
        ):
            return candidate

    app_id = re.search(r'^\s*discordApplicationId:\s*"(\d{17,20})"', source, re.MULTILINE)
    if not app_id:
        return None
    permissions = re.search(r'^\s*installPermissions:\s*"(\d+)"', source, re.MULTILINE)
    query = urlencode({
        "client_id": app_id.group(1),
        "permissions": permissions.group(1) if permissions else "268454928",
        "scope": "bot applications.commands",
    })
    return f"https://discord.com/oauth2/authorize?{query}"


def asset_root(path: str) -> str:
    depth = len(PurePosixPath(path).parent.parts)
    return "../" * depth


# ---------------------------------------------------------------------------
# SEO helpers
# ---------------------------------------------------------------------------

def jsonld_block(payload: dict) -> str:
    return ('<script type="application/ld+json">'
            + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            + "</script>")


def org_ld() -> dict:
    return {"@type": "Organization", "@id": "#org", "name": "OverX",
            "url": site_url() or None,
            "slogan": "Des applications, des projets et un même univers."}


def breadcrumb_ld(path: str, root: str) -> dict:
    labels = {"overload": "OverLoad", "discord-bots": "Bots", "freegamedrop": "FreeGameDrop", "auto-hebergement": "Auto-hébergement",
              "steam": "Steam", "epic-games": "Epic Games Store", "gog": "GOG", "ubisoft": "Ubisoft"}
    parts = [part for part in PurePosixPath(path).parent.parts if part != "."]
    items = [{"@type": "ListItem", "position": 1, "name": "Accueil", "item": f"{root}index.html"}]
    for position, _ in enumerate(parts, start=2):
        segment = "/".join(parts[: position - 1])
        items.append({"@type": "ListItem", "position": position, "name": labels.get(parts[position - 2], parts[position - 2].capitalize()),
                      "item": f"{root}{segment}/index.html"})
    return {"@type": "BreadcrumbList", "itemListElement": items}


def faq_ld(faqs: list[tuple[str, str]]) -> dict:
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": question,
                            "acceptedAnswer": {"@type": "Answer", "text": answer}}
                           for question, answer in faqs]}


def software_ld(bot: dict) -> dict:
    url = f"{site_url()}/{bot['page']}" if site_url() else bot["page"]
    return {"@context": "https://schema.org", "@type": "SoftwareApplication",
            "name": bot["name"], "applicationCategory": "UtilitiesApplication",
            "operatingSystem": "Discord", "url": url, "description": bot["short"],
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
            "author": {"@id": "#org"},
            "featureList": ["Alertes de jeux gratuits par plateforme",
                            "Favoris, recherche et rappels d'expiration",
                            "Permissions minimales et salons en lecture seule",
                            "Statistiques mesurées (/stats, /sante)"]}


def seo_head(page: dict) -> str:
    base = site_url()
    canonical_url = f"{base}/{PurePosixPath(page['path'])}" if base else ""
    og_image = page.get("og_image", "overx.png")
    lines = []
    if canonical_url:
        lines.append(f'  <link rel="canonical" href="{escape(canonical_url, quote=True)}">')
    lines.append('  <meta property="og:type" content="website">')
    lines.append('  <meta property="og:site_name" content="OverX">')
    lines.append('  <meta property="og:locale" content="fr_FR">')
    lines.append(f'  <meta property="og:title" content="{escape(page["title"], quote=True)}">')
    lines.append(f'  <meta property="og:description" content="{escape(page["description"], quote=True)}">')
    if canonical_url:
        lines.append(f'  <meta property="og:url" content="{escape(canonical_url, quote=True)}">')
        lines.append(f'  <meta property="og:image" content="{escape(f"{base}/assets/og/{og_image}", quote=True)}">')
        lines.append('  <meta property="og:image:width" content="1200">')
        lines.append('  <meta property="og:image:height" content="630">')
    lines.append('  <meta name="twitter:card" content="summary_large_image">')
    lines.append(f'  <meta name="twitter:title" content="{escape(page["title"], quote=True)}">')
    lines.append(f'  <meta name="twitter:description" content="{escape(page["description"], quote=True)}">')
    if base:
        lines.append(f'  <meta name="twitter:image" content="{escape(f"{base}/assets/og/{og_image}", quote=True)}">')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Shared body fragments (all links use the {{ROOT}} token, replaced per page)
# ---------------------------------------------------------------------------

def overload_downloads(show_details: bool = False) -> str:
    """Real HTML anchors keep stable-release downloads usable without JavaScript."""
    details = (
        '\n        <a class="button button-secondary" href="{{ROOT}}overload/index.html">'
        'Découvrir OverLoad <span aria-hidden="true">→</span></a>'
        if show_details else ""
    )
    return f"""<div class="overload-downloads" id="telecharger" role="group" aria-label="Télécharger OverLoad pour Windows">
      <div class="hero-actions">
        <a class="button button-primary" data-overload-download="installer" href="{escape(OVERLOAD['installer_url'], quote=True)}" aria-describedby="overload-download-note">Télécharger pour Windows <span aria-hidden="true">↓</span></a>{details}
      </div>
      <div class="overload-download-links">
        <a class="text-link" data-overload-download="portable" href="{escape(OVERLOAD['portable_url'], quote=True)}">Version portable (.zip) <span aria-hidden="true">↓</span></a>
        <a class="text-link" href="{escape(OVERLOAD['release_url'], quote=True)}" target="_blank" rel="noopener noreferrer">Notes de la dernière version <span aria-hidden="true">↗</span></a>
      </div>
      <p class="overload-download-note" id="overload-download-note">Dernière version stable publiée sur GitHub · Windows 11, 64 bits.<br>Télécharge <code>OverLoad-Setup.exe</code>, puis lance l'installateur sur ton PC.</p>
    </div>"""


def overload_art() -> str:
    """Real application window composition showcasing OverLoad v1.1 on Windows."""
    return """<div class="bot-card-art overload-card-art overload-visual-stage">
        <div class="art-halo" aria-hidden="true"></div>
        <div class="app-window app-window-primary">
          <div class="app-window-bar" aria-hidden="true">
            <div class="window-controls"><i></i><i></i><i></i></div>
            <span class="app-window-title">OverLoad.exe — Media Suite v1.1</span>
            <span class="app-window-badge">WINDOWS 11 · 64 BITS</span>
          </div>
          <div class="app-window-viewport">
            <img src="{{ROOT}}assets/overload/accueil.png" alt="Capture de l'interface principale d'OverLoad sur Windows : téléchargement direct, débit global et file d'attente" width="1200" height="840" loading="lazy">
          </div>
        </div>
        <div class="app-window app-window-secondary" aria-hidden="true">
          <div class="app-window-bar">
            <div class="window-controls"><i></i><i></i><i></i></div>
            <span class="app-window-title">Espace Créateurs &amp; Téléchargements</span>
          </div>
          <div class="app-window-viewport">
            <img src="{{ROOT}}assets/overload/telechargements.png" alt="" width="1200" height="840" loading="lazy">
          </div>
        </div>
        <div class="app-floating-pill pill-speed" aria-hidden="true"><span class="art-caption-dot"></span> 1,23 Mo/s · Reprise HTTP Range</div>
        <div class="app-floating-pill pill-creators" aria-hidden="true"><span class="pill-accent">⚡</span> Espace Créateurs &amp; FFprobe</div>
      </div>"""


def overload_showcase_section() -> str:
    """Interactive multi-screen gallery of real OverLoad v1.1 application captures."""
    tabs = []
    panels = []
    for idx, screen in enumerate(OVERLOAD_SCREENS):
        is_active = idx == 0
        active_class = " is-active" if is_active else ""
        aria_selected = "true" if is_active else "false"
        hidden_attr = "" if is_active else " hidden"
        tabs.append(
            f'<button class="showcase-tab{active_class}" type="button" role="tab" '
            f'aria-selected="{aria_selected}" aria-controls="panel-{screen["id"]}" '
            f'id="tab-{screen["id"]}" data-showcase-tab="{screen["id"]}">'
            f'<span class="showcase-tab-badge">{escape(screen["badge"])}</span>'
            f'<strong>{escape(screen["label"])}</strong></button>'
        )
        panels.append(
            f'<div class="showcase-screen-panel{active_class}" id="panel-{screen["id"]}" '
            f'role="tabpanel" aria-labelledby="tab-{screen["id"]}" data-showcase-panel="{screen["id"]}"{hidden_attr}>'
            f'<div class="showcase-window-frame">'
            f'<div class="app-window-bar" aria-hidden="true">'
            f'<div class="window-controls"><i></i><i></i><i></i></div>'
            f'<span class="app-window-title">OverLoad.exe — {escape(screen["label"])}</span>'
            f'<span class="app-window-badge">{escape(screen["badge"])}</span>'
            f'</div>'
            f'<div class="showcase-window-body">'
            f'<img src="{{{{ROOT}}}}{screen["image"]}" alt="{escape(screen["title"])} — {escape(screen["caption"])}" width="1200" height="840" loading="lazy">'
            f'</div>'
            f'<div class="showcase-window-caption">'
            f'<div><span class="eyebrow">{escape(screen["badge"])}</span><h3>{escape(screen["title"])}</h3><p>{escape(screen["caption"])}</p></div>'
            f'<a class="button button-primary" href="{escape(OVERLOAD["installer_url"], quote=True)}">Télécharger OverLoad <span aria-hidden="true">↓</span></a>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
    tabs_html = "\n        ".join(tabs)
    panels_html = "\n      ".join(panels)
    return f"""<section class="section container overload-gallery-section" id="apercu" aria-labelledby="overload-gallery-heading" data-reveal>
    <div class="section-heading section-heading-split">
      <div><p class="eyebrow"><span class="eyebrow-dot"></span> L'APPLICATION EN IMAGES · V1.1</p><h2 id="overload-gallery-heading">De vraies captures.<br><span>Une interface taillée pour Windows.</span></h2></div>
      <p class="section-intro">Parcours les différentes vues d'OverLoad : tableau de bord de téléchargement, suivi en direct, Espace Créateurs, historique avec diagnostic et personnalisation des thèmes.</p>
    </div>
    <div class="overload-interactive-showcase" data-app-showcase>
      <div class="showcase-tabs" role="tablist" aria-label="Vues de l'application OverLoad">
        {tabs_html}
      </div>
      <div class="showcase-panels">
        {panels_html}
      </div>
    </div>
  </section>"""


def fgd_art() -> str:
    """Rich floating Discord window preview for FreeGameDrop on the home page."""
    return """<div class="bot-card-art fgd-visual-stage" aria-hidden="true">
        <div class="art-halo"></div>
        <div class="discord-app-window">
          <div class="app-window-bar">
            <div class="window-controls"><i></i><i></i><i></i></div>
            <span class="app-window-title">Discord — Serveur Communauté</span>
            <span class="app-window-badge">BOT ACTIF</span>
          </div>
          <div class="discord-app-layout">
            <div class="discord-sidebar-mini">
              <div class="sidebar-cat">JEUX GRATUITS</div>
              <div class="sidebar-chan"><span class="hash">#</span> choisir-ses-roles</div>
              <div class="sidebar-chan is-active"><span class="hash">#</span> jeux-epic <span class="chan-badge">1</span></div>
              <div class="sidebar-chan"><span class="hash">#</span> jeux-steam</div>
              <div class="sidebar-chan"><span class="hash">#</span> jeux-gog</div>
              <div class="sidebar-chan"><span class="hash">#</span> jeux-ubisoft</div>
            </div>
            <div class="discord-chat-mini">
              <div class="preview-message">
                <div class="preview-avatar">FG</div>
                <div class="preview-message-body">
                  <div class="preview-author">FreeGameDrop <span class="bot-tag">APP</span> <time>Aujourd'hui à 18:00</time></div>
                  <div class="preview-embed">
                    <div class="embed-kicker"><span class="embed-dot"></span> 🔥 OFFRE EXCEPTIONNELLE · EPIC GAMES</div>
                    <div class="embed-game-title">Cyberpunk 2077 — Édition Complète</div>
                    <p><s>59,99 €</s> ➜ <strong>GRATUIT</strong> · 🟢 Expire dans 23 heures</p>
                    <div class="embed-meta"><span>⚪ Rôle Epic Games</span><span>·</span><span>Vérifié via API officielle</span></div>
                    <div class="embed-actions-row">
                      <span class="embed-button">🎁 Récupérer le jeu <span>↗</span></span>
                      <span class="embed-button embed-button-ghost">❤️ Favori</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="app-floating-pill pill-discord"><span class="art-caption-dot"></span> 4 boutiques · Salons dédiés sans spam</div>
      </div>"""


def stats_band() -> str:
    """Numbers stay « — » until a measured public API is configured."""
    return """<section class="section-alt stats-band" aria-label="Chiffres publics FreeGameDrop" data-reveal>
    <div class="container stats-band-inner">
      <div class="stats-band-copy">
        <p class="eyebrow">FREEGAMEDROP EN CHIFFRES</p>
        <h2>Des chiffres réels,<br><span>ou pas de chiffres.</span></h2>
        <p class="stats-band-note" data-stats-note>Aucune API publique n'est encore reliée : chaque compteur reste à « — » plutôt que d'être inventé. Renseigne <code>statsApiUrl</code> et <code>healthApiUrl</code> dans la configuration pour publier les mesures du bot.</p>
      </div>
      <dl class="stats-grid">
        <div class="stat-cell" data-spotlight><dt>Serveurs</dt><dd data-stat="guilds">—</dd></div>
        <div class="stat-cell" data-spotlight><dt>Offres détectées</dt><dd data-stat="offers">—</dd></div>
        <div class="stat-cell" data-spotlight><dt>Offres actives</dt><dd data-stat="active_offers">—</dd></div>
        <div class="stat-cell" data-spotlight><dt>Disponibilité</dt><dd data-stat="uptime">—</dd></div>
      </dl>
    </div>
  </section>"""


def why_overx() -> str:
    return """<div class="principles-grid">
        <article class="principle-card" data-spotlight data-reveal data-reveal-delay="0"><div class="principle-index">01</div><div class="principle-icon icon-violet" aria-hidden="true">⌕</div><h3>Un espace pour chaque projet</h3><p>Une présentation claire avec de vrais aperçus pour comprendre chaque logiciel avant de le télécharger ou de l'ajouter à Discord.</p></article>
        <article class="principle-card" data-spotlight data-reveal data-reveal-delay="80"><div class="principle-index">02</div><div class="principle-icon icon-cyan" aria-hidden="true">↓</div><h3>Des téléchargements officiels</h3><p>OverLoad se télécharge directement depuis ses releases GitHub. Le lien suit la dernière version stable, sans intermédiaire.</p></article>
        <article class="principle-card" data-spotlight data-reveal data-reveal-delay="160"><div class="principle-index">03</div><div class="principle-icon icon-lime" aria-hidden="true">＋</div><h3>De la place pour la suite</h3><p>Les nouvelles applications et les futurs projets rejoindront OverX. Pas de fausse date ni de disponibilité inventée.</p></article>
      </div>"""


def platform_strip() -> str:
    tiles = "\n        ".join(
        f'<a class="platform-tile {p["color"]}" data-spotlight data-reveal href="{{{{ROOT}}}}discord-bots/freegamedrop/{p["slug"]}/index.html"><span class="platform-tile-icon" aria-hidden="true">{p["icon"]}</span><strong>{escape(p["name"])}</strong><small>{escape(p["source"])}</small></a>'
        for p in FGD_PLATFORMS)
    return f"""<section class="section section-alt" data-reveal>
    <div class="container">
      <div class="section-heading section-heading-split"><div><p class="eyebrow">PLATEFORMES SUIVIES</p><h2>Quatre boutiques.<br><span>Un salon par plateforme.</span></h2></div><p class="section-intro">Chaque plateforme a son rôle, son salon et ses annonces. Les membres ne reçoivent que ce qu'ils choisissent.</p></div>
      <div class="platform-grid">
        {tiles}
      </div>
    </div>
  </section>"""


def community_cta() -> str:
    return """<section class="section container" data-community-cta hidden>
    <div class="community-panel" data-community-cta hidden>
      <div><p class="eyebrow">COMMUNAUTÉ OVERX</p><h2>Un serveur pour en parler.</h2><p>Annonces, suggestions, support et showcase : rejoins le serveur communautaire OverX sur Discord.</p></div>
      <a class="button button-light" data-community-cta href="#" hidden>Rejoindre le Discord <span aria-hidden="true">→</span></a>
    </div>
  </section>"""


def other_bots(current_slug: str) -> str:
    others = [bot for bot in BOTS if bot["slug"] != current_slug]
    cards = "\n        ".join(
        f'<a class="other-bot-card" data-spotlight href="{{{{ROOT}}}}{bot["page"]}"><span class="product-mark">{bot["mark"]}<span>{bot["mark_accent"]}</span></span><div><strong>{escape(bot["name"])}</strong><p>{escape(bot["short"])}</p></div><span aria-hidden="true">→</span></a>'
        for bot in others)
    soon = ('<div class="other-bot-card other-bot-soon" data-spotlight><span class="product-mark product-mark-dim">＋<span></span></span>'
            '<div><strong>Les prochains bots</strong><p>Annoncés quand leur développement et leur disponibilité seront confirmés.</p></div>'
            '<a class="text-link" href="{{ROOT}}roadmap/index.html">Roadmap <span aria-hidden="true">→</span></a></div>')
    overload = ('<a class="other-bot-card" data-spotlight href="{{ROOT}}overload/index.html">'
                '<span class="product-mark overload-mark" aria-hidden="true">OL</span>'
                '<div><strong>OverLoad · Windows</strong><p>Télécharge, analyse et organise tes médias dans une application de bureau.</p></div>'
                '<span aria-hidden="true">→</span></a>')
    inner = "\n        ".join([overload, *([cards] if cards else []), soon])
    return f"""<section class="section section-alt" data-reveal>
    <div class="container">
      <div class="section-heading"><p class="eyebrow">L'ÉCOSYSTÈME OVERX</p><h2>D’autres usages.<br><span>Le même univers.</span></h2><p class="section-intro">OverX rassemble aussi des applications Windows et les futurs projets. Découvre les autres outils de la collection.</p></div>
      <div class="other-bots-grid">
        {inner}
      </div>
    </div>
  </section>"""


def faq_block(faqs: list[tuple[str, str]]) -> str:
    items = "\n        ".join(
        f'<details class="faq-item"><summary>{escape(question)}</summary><p>{escape(answer)}</p></details>'
        for question, answer in faqs)
    return f'<div class="install-help-list">\n        {items}\n      </div>'


def command_table(commands: list[tuple[str, str, str]]) -> str:
    rows = "\n        ".join(
        f'<tr><td><code>{escape(name)}</code></td><td>{escape(access)}</td><td>{escape(effect)}</td></tr>'
        for name, access, effect in commands)
    return (f'<div class="table-wrap"><table class="command-table"><thead><tr><th>Commande</th><th>Accès</th>'
            f'<th>À quoi elle sert</th></tr></thead><tbody>\n        {rows}\n      </tbody></table></div>')


def platform_page(platform: dict) -> dict:
    other_tiles = "\n      ".join(
        f'<a class="platform-tile {p["color"]}" data-spotlight href="{{{{ROOT}}}}discord-bots/freegamedrop/{p["slug"]}/index.html"><span class="platform-tile-icon" aria-hidden="true">{p["icon"]}</span><strong>{escape(p["name"])}</strong><small>{escape(p["source"])}</small></a>'
        for p in FGD_PLATFORMS if p["slug"] != platform["slug"])
    facts = "\n      ".join(
        f'<article class="platform-fact" data-spotlight><span aria-hidden="true">✓</span><p>{escape(fact)}</p></article>'
        for fact in platform["facts"])
    body = f"""
<main id="main-content">
  <section class="page-hero container" data-reveal>
    <p class="eyebrow"><a href="{{{{ROOT}}}}discord-bots/freegamedrop/index.html">FREEGAMEDROP</a> <span class="crumb-slash">/</span> {escape(platform["name"]).upper()}</p>
    <h1>Les jeux gratuits {escape(platform["name"])}<br><span>dans ton salon Discord.</span></h1>
    <p class="hero-lead narrow">{escape(platform["intro"])}</p>
    <div class="catalogue-meta"><span class="platform-meta-icon {platform["color"]}" aria-hidden="true">{platform["icon"]}</span> {escape(platform["name"])} <span class="meta-divider"></span> Source : {escape(platform["source"])} <span class="meta-divider"></span> Salon {escape(platform["channel"])}</div>
  </section>

  <section class="section container section-compact" data-reveal>
    <div class="section-heading"><p class="eyebrow">CE QUE FAIT LE BOT</p><h2>{escape(platform["name"])}, sans effort<br><span>et sans spam.</span></h2></div>
    <div class="platform-facts">
      {facts}
    </div>
    <div class="platform-cta-row"><a class="button button-primary" data-install-cta href="{{{{ROOT}}}}install/index.html#ajouter">Ajouter FreeGameDrop <span aria-hidden="true">↗</span></a><a class="button button-secondary" href="{{{{ROOT}}}}discord-bots/freegamedrop/index.html">Toutes les fonctionnalités <span aria-hidden="true">→</span></a></div>
  </section>

  <section class="section section-alt" data-reveal>
    <div class="container two-column-section">
      <div><p class="eyebrow">EN PRATIQUE</p><h2>Un rôle,<br><span>un salon.</span></h2><p class="section-intro">Après /setup-auto, la plateforme {escape(platform["name"])} existe comme les autres : un rôle {platform["icon"]} {escape(platform["role"])} obtenu par le panneau de boutons, un salon {escape(platform["channel"])} en lecture seule, des annonces avec prix barré et compte à rebours.</p><a class="text-link" href="{{{{ROOT}}}}docs/index.html#configuration">Configurer les salons <span aria-hidden="true">→</span></a></div>
      <div class="command-pills"><span data-spotlight><code>/setup-auto</code><small>crée rôle et salon {escape(platform["name"])}</small></span><span data-spotlight><code>/preferences</code><small>filtrer plateformes et genres</small></span><span data-spotlight><code>/alertes</code><small>alertes privées {escape(platform["name"])}</small></span><span data-spotlight><code>/rappel-salon</code><small>rappel de fin d'offre</small></span></div>
    </div>
  </section>

  <section class="section container" data-reveal>
    <div class="section-heading section-heading-split"><div><p class="eyebrow">LES AUTRES PLATEFORMES</p><h2>Et si tu suis<br><span>plusieurs boutiques ?</span></h2></div><p class="section-intro">Chaque plateforme a sa propre page : compare les sources et les salons créés par le bot.</p></div>
    <div class="platform-grid">
      {other_tiles}
      <a class="platform-tile platform-tile-more" data-spotlight href="{{{{ROOT}}}}discord-bots/freegamedrop/index.html"><span class="platform-tile-icon" aria-hidden="true">＋</span><strong>FreeGameDrop</strong><small>la fiche complète du bot</small></a>
    </div>
  </section>
</main>
"""
    return {
        "path": f"discord-bots/freegamedrop/{platform['slug']}/index.html",
        "title": platform["title"],
        "description": platform["description"],
        "active": "bots",
        "og_image": "freegamedrop.png",
        "body": body,
    }


# ---------------------------------------------------------------------------
# Pages (bodies may contain the tokens below, replaced at build time)
# ---------------------------------------------------------------------------

PAGES: list[dict] = []  # filled below, then extended with platform pages

_HOME_BODY = r"""
<main id="main-content">
  <section class="hero hero-spectacular container">
    <div class="hero-ambient" aria-hidden="true">
      <div class="ambient-glow glow-violet"></div>
      <div class="ambient-glow glow-blue"></div>
      <div class="overx-sigil"></div>
    </div>
    <div class="hero-copy hero-copy-spectacular" data-reveal>
      <div class="hero-brand-badge">
        <img src="{{ROOT}}assets/brand-mark.svg" alt="" width="40" height="40">
        <p class="eyebrow"><span class="eyebrow-dot"></span> OVERX · APPLICATIONS &amp; PROJETS</p>
      </div>
      <h1>Des outils utiles.<br><span>Un même univers.</span></h1>
      <p class="hero-lead">OverX rassemble mes applications et mes futurs projets. Avec <strong>OverLoad</strong> pour télécharger, analyser et organiser tes médias sur Windows et <strong>FreeGameDrop</strong> pour ta communauté Discord, retrouve chaque logiciel et ses liens officiels au même endroit.</p>
      <div class="hero-actions">
        <a class="button button-primary button-lg" href="#projets">Découvrir les projets <span aria-hidden="true">↓</span></a>
        <a class="button button-secondary button-lg" href="#overload">Explorer OverLoad <span aria-hidden="true">→</span></a>
      </div>
      <div class="hero-caption"><span class="caption-check" aria-hidden="true">✓</span> Un site pour découvrir. Des applications natives à utiliser.</div>
    </div>

    <div class="hero-visual project-showcase hero-stage" data-reveal data-reveal-delay="140">
      <div class="visual-grid" aria-hidden="true"></div>
      <div class="visual-orbit orbit-one" aria-hidden="true"></div>
      <div class="visual-orbit orbit-two" aria-hidden="true"></div>

      <div class="hero-stage-centerpiece">
        <div class="app-window hero-main-window" data-spotlight>
          <div class="app-window-bar">
            <div class="window-controls" aria-hidden="true"><i></i><i></i><i></i></div>
            <span class="app-window-title">OverLoad.exe — Media Suite v1.1 (Windows 11 · 64 bits)</span>
            <span class="app-window-badge"><span class="live-dot"></span> NATIVE</span>
          </div>
          <div class="app-window-viewport">
            <img src="{{ROOT}}assets/overload/accueil.png" alt="Aperçu de l'application Windows OverLoad v1.1 : téléchargement direct, débit en temps réel et organisation multimédia" width="1200" height="840" fetchpriority="high">
          </div>
        </div>

        <div class="project-showcase-panel hero-floating-dock" data-spotlight>
          <div class="showcase-heading"><img src="{{ROOT}}assets/brand-mark.svg" alt="" width="42" height="42"><div><strong>OverX</strong><span>Le point de départ de tes logiciels.</span></div></div>
          <a class="showcase-project" href="{{ROOT}}overload/index.html"><span class="showcase-mark overload-mark" aria-hidden="true">OL</span><div><strong>OverLoad</strong><span>Tes médias, à ta façon.</span></div><span class="showcase-platform">WINDOWS</span><span aria-hidden="true">↗</span></a>
          <a class="showcase-project" href="{{ROOT}}discord-bots/freegamedrop/index.html"><span class="showcase-mark" aria-hidden="true">FG</span><div><strong>FreeGameDrop</strong><span>Les jeux gratuits, sur ton serveur.</span></div><span class="showcase-platform">DISCORD</span><span aria-hidden="true">↗</span></a>
          <div class="showcase-future"><span aria-hidden="true">＋</span> Et les projets à venir.</div>
        </div>

        <a class="hero-floating-discord" href="{{ROOT}}discord-bots/freegamedrop/index.html" aria-label="Découvrir FreeGameDrop pour Discord" data-spotlight>
          <div class="floating-discord-top">
            <span class="preview-avatar" aria-hidden="true">FG</span>
            <div><strong>FreeGameDrop</strong> <span class="bot-tag">BOT</span><small>#jeux-epic · Alerte automatique</small></div>
          </div>
          <div class="floating-discord-embed">
            <span class="embed-kicker"><span class="embed-dot"></span> 🔥 OFFRE EXCEPTIONNELLE</span>
            <strong>Jeu complet offert · <s>59,99 €</s> ➜ GRATUIT</strong>
            <div class="floating-discord-tags"><span>🔵 Steam</span><span>⚪ Epic</span><span>🟣 GOG</span><span>🔷 Ubisoft</span></div>
          </div>
        </a>
      </div>
    </div>
  </section>

  <section class="truth-band" aria-label="Les liens officiels des projets" data-reveal>
    <div class="container truth-band-inner">
      <div class="truth-icon" aria-hidden="true">↗</div>
      <div><p class="truth-title">Les bons liens. Au bon endroit.</p><p class="truth-copy">Les téléchargements OverLoad mènent directement à la dernière release stable sur GitHub, sans version figée.</p></div>
      <a class="text-link" href="{{ROOT}}overload/index.html#installation">Comment l'installer ? <span aria-hidden="true">→</span></a>
    </div>
  </section>

  <section class="section container" id="projets" aria-labelledby="projects-heading">
    <div class="section-heading section-heading-split" data-reveal>
      <div><p class="eyebrow"><span class="eyebrow-dot"></span> LA COLLECTION OVERX</p><h2 id="projects-heading">Les projets OverX.<br><span>À chacun son usage.</span></h2></div>
      <p class="section-intro">Une application Windows native avec de vrais outils médias, un bot Discord de veille automatique et de la place pour la suite. Chaque logiciel possède son propre univers ; OverX les réunit.</p>
    </div>

    <article class="featured-bot-card overload-card" id="overload" aria-labelledby="overload-heading" data-spotlight data-reveal>
      <div class="bot-card-main">
        <div class="bot-card-topline"><span class="product-mark overload-mark" aria-hidden="true">OL</span><span class="status-pill status-current"><span></span> Application Windows · v1.1</span></div>
        <p class="eyebrow bot-category">TÉLÉCHARGEMENT · ANALYSE · ORGANISATION</p>
        <h3 id="overload-heading">OverLoad</h3>
        <p class="bot-description">Télécharge des fichiers depuis des liens directs HTTP(S) avec reprise automatique, analyse tes vidéos, musiques et images via FFprobe, puis prépare tes projets de montage dans l'Espace Créateurs d'une application native Windows.</p>
        <div class="chip-row"><span class="chip">Liens directs HTTP(S)</span><span class="chip">Reprise HTTP Range</span><span class="chip">Analyse multimédia</span><span class="chip">Espace Créateurs</span><span class="chip">Thèmes Sombre &amp; Clair</span></div>
        {{OVERLOAD_DOWNLOADS_HOME}}
      </div>
      {{OVERLOAD_ART}}
    </article>

    <article class="featured-bot-card" id="bots" data-spotlight data-reveal>
      <div class="bot-card-main">
        <div class="bot-card-topline"><span class="product-mark" aria-hidden="true">FG<span>D</span></span><span class="status-pill status-neutral"><span></span> Disponibilité publique à confirmer</span></div>
        <p class="eyebrow bot-category">JEUX GRATUITS · STEAM · EPIC · GOG · UBISOFT</p>
        <h3>FreeGameDrop</h3>
        <p class="bot-description">Chaque heure, le bot vérifie les offres de jeux gratuits et les annonce dans ton serveur. Rôles et salons par plateforme, favoris, alertes privées et rappels de fin d'offre.</p>
        <div class="chip-row"><span class="chip">🔵 Steam</span><span class="chip">⚪ Epic Games Store</span><span class="chip">🟣 GOG</span><span class="chip">🔷 Ubisoft</span><span class="chip">Licence MIT</span></div>
        <div class="card-actions">
          <a class="button button-primary" href="{{ROOT}}discord-bots/freegamedrop/index.html">Voir FreeGameDrop <span aria-hidden="true">↗</span></a>
          <a class="button button-outline" data-install-cta href="{{ROOT}}install/index.html#ajouter">Guide d'installation <span aria-hidden="true">↗</span></a>
        </div>
        <p class="micro-note" data-install-status>Le lien d'invitation Discord n'a pas encore été communiqué.</p>
      </div>
      {{FGD_ART}}
    </article>
    <div class="coming-soon-row" data-spotlight data-reveal><span class="coming-icon" aria-hidden="true">＋</span><div><strong>Les prochains projets ?</strong><p>Ils seront présentés ici au fil de leur développement, avec de vraies captures et leur disponibilité clairement indiquée.</p></div><span class="coming-badge">À VENIR</span></div>
  </section>

  <section class="section section-alt">
    <div class="container">
      <div class="section-heading" data-reveal><p class="eyebrow">UN POINT D'ENTRÉE COMMUN</p><h2>Découvrir. Choisir.<br><span>Passer à l'action.</span></h2><p class="section-intro">OverX est la vitrine des projets, pas un installateur intermédiaire. Chaque logiciel conserve son parcours direct et transparent.</p></div>
      {{WHY_OVERX}}
    </div>
  </section>

  {{STATS_BAND}}

  {{COMMUNITY_CTA}}
</main>
"""

PAGES.append({
    "path": "index.html",
    "title": "OverX — Applications & projets",
    "description": "OverX réunit mes applications et mes futurs projets : OverLoad pour télécharger et organiser tes médias sur Windows, FreeGameDrop pour les jeux gratuits sur Discord.",
    "active": "home",
    "og_image": "overx.png",
    "body": _HOME_BODY,
    "ld_extra": lambda: [
        {"@type": "WebSite", "@id": "#website", "name": "OverX", "inLanguage": "fr-FR", "publisher": {"@id": "#org"}},
        {"@type": "ItemList", "name": "Applications et projets OverX",
         "itemListElement": [{"@type": "ListItem", "position": index + 1, "name": project["name"], "url": project["page"]}
                             for index, project in enumerate([OVERLOAD, *BOTS])]},
    ],
})

_OVERLOAD_BODY = r"""
<main id="main-content" class="overload-page">
  <section class="product-hero container overload-hero">
    <div class="product-copy" data-reveal>
      <p class="eyebrow"><a href="{{ROOT}}index.html#projets">PROJETS OVERX</a> <span class="crumb-slash">/</span> OVERLOAD</p>
      <div class="product-heading"><span class="product-mark product-mark-large overload-mark" aria-hidden="true">OL</span><span class="status-pill status-current"><span></span> Application Windows · v1.1</span></div>
      <h1>Tes médias.<br><span>Prêts pour la suite.</span></h1>
      <p class="hero-lead">OverLoad télécharge des fichiers depuis des liens directs HTTP(S), analyse tes médias et t'aide à préparer tes projets vidéo. Une application de bureau native Windows (`OverLoad.exe`), avec un espace dédié aux créateurs et une interface sombre ou claire.</p>
      {{OVERLOAD_DOWNLOADS}}
    </div>
    <div data-reveal data-reveal-delay="120">
      {{OVERLOAD_ART}}
    </div>
  </section>

  {{OVERLOAD_SHOWCASE_SECTION}}

  <section class="section section-alt">
    <div class="container">
      <div class="section-heading" data-reveal><p class="eyebrow">TÉLÉCHARGER · ANALYSER · ORGANISER</p><h2>De tes fichiers<br><span>à ton prochain projet.</span></h2><p class="section-intro">Les fonctionnalités présentées ici sont intégrées dans l'exécutable Windows natif et documentées dans le dépôt officiel OverLoad.</p></div>
      <div class="feature-grid overload-features">
        <article class="feature-card" data-spotlight data-reveal data-reveal-delay="0"><div class="feature-icon icon-violet" aria-hidden="true">↓</div><h3>Gérer tes téléchargements</h3><p>Ajoute des liens directs HTTP(S), télécharge par lots (1 à 16 simultanés), règle la limite de vitesse globale et profite de la reprise HTTP Range automatique après coupure.</p></article>
        <article class="feature-card" data-spotlight data-reveal data-reveal-delay="80"><div class="feature-icon icon-cyan" aria-hidden="true">⌕</div><h3>Comprendre tes médias</h3><p>Consulte les codecs, la résolution, le débit et les pistes audio, vidéo ou sous-titres de tes fichiers locaux grâce à FFprobe embarqué. Les alertes de compatibilité t'aident avant le montage.</p></article>
        <article class="feature-card" data-spotlight data-reveal data-reveal-delay="160"><div class="feature-icon icon-lime" aria-hidden="true">▤</div><h3>Préparer ton projet vidéo</h3><p>L'Espace Créateurs prépare l'arborescence de dossiers (Premiere Pro, DaVinci Resolve, CapCut), renomme par lots et exporte un inventaire CSV sans jamais modifier tes originaux.</p></article>
      </div>
      <div class="notice" data-reveal><strong>Des sources directes, sans contournement.</strong><p>OverLoad prend en charge les adresses HTTP(S) qui pointent directement vers un fichier. Il ne contourne ni les protections d'accès, ni les DRM, ni les restrictions d'une plateforme. Utilise uniquement les médias que tu es autorisé à télécharger.</p></div>
    </div>
  </section>

  <section class="section container overload-install" id="installation" aria-labelledby="overload-install-heading" data-reveal>
    <div class="section-heading"><p class="eyebrow">INSTALLATION WINDOWS</p><h2 id="overload-install-heading">Télécharge ici.<br><span>Installe sur ton PC.</span></h2><p class="section-intro">Le site fournit le fichier ; c'est toi qui lances l'installation. Aucune installation ni mise à jour n'est déclenchée dans ton ordinateur par OverX.</p></div>
    <ol class="overload-steps">
      <li><span class="overload-step-number" aria-hidden="true">01</span><div><h3>Télécharge l'installateur</h3><p>Le bouton « Télécharger pour Windows » récupère <code>OverLoad-Setup.exe</code> depuis la dernière release stable publiée sur GitHub.</p></div></li>
      <li><span class="overload-step-number" aria-hidden="true">02</span><div><h3>Lance le fichier sur ton PC</h3><p>Ouvre le fichier téléchargé sous Windows 11 (64 bits), puis suis les étapes de l'installateur.</p></div></li>
      <li><span class="overload-step-number" aria-hidden="true">03</span><div><h3>Ouvre OverLoad</h3><p>Lance l'application depuis Windows pour télécharger, analyser et organiser tes médias. Pour une prochaine version, retrouve le même bouton sur OverX.</p></div></li>
    </ol>
    <div class="notice"><strong>Tu préfères une version sans installation ?</strong><p>Choisis « Version portable (.zip) », extrais l'archive dans un dossier puis lance <code>OverLoad.exe</code>. Les notes de version restent disponibles sur GitHub si tu souhaites consulter les changements ou les fichiers publiés.</p></div>
  </section>

  <section class="section section-alt" data-reveal>
    <div class="container install-help-layout">
      <div><p class="eyebrow">QUESTIONS FRÉQUENTES</p><h2>Avant le<br><span>téléchargement.</span></h2><p class="section-intro">OverX présente l'application. Le code et les releases restent dans le dépôt OverLoad.</p></div>
      {{FAQ_BLOCK}}
    </div>
  </section>

  <section class="section container" data-reveal>
    <div class="install-bottom-cta" data-spotlight><div><p class="eyebrow">LE PROJET OVERLOAD</p><h2>Le code, les versions, les échanges.</h2><p>Consulte le README, les releases et les problèmes signalés dans le dépôt officiel de l'application.</p></div><div class="install-bottom-actions"><a class="button button-secondary" href="{{OVERLOAD_SOURCE_URL}}" target="_blank" rel="noopener noreferrer">Dépôt OverLoad <span aria-hidden="true">↗</span></a><a class="text-link" href="{{ROOT}}index.html#projets">Tous les projets OverX <span aria-hidden="true">→</span></a></div></div>
  </section>
</main>
"""

OVERLOAD_FAQ = [
    ("Le bouton suit-il les nouvelles versions ?", "Oui. Le lien permanent GitHub releases/latest/download/OverLoad-Setup.exe pointe vers l'installateur de la dernière release stable. Aucun numéro de version n'est figé dans le site. Les brouillons et préversions ne sont pas ciblés."),
    ("OverX installe-t-il ou met-il à jour l'application ?", "Non. OverX fournit uniquement le lien de téléchargement. Tu télécharges l'installateur puis tu le lances toi-même sur ton PC. Le site n'ajoute aucun système de mise à jour automatique dans OverLoad."),
    ("Installateur ou version portable ?", "L'installateur OverLoad-Setup.exe te guide pour installer l'application sous Windows. La version portable OverLoad-Portable-win64.zip s'extrait dans un dossier avant de lancer OverLoad.exe, sans passer par l'installateur."),
]

PAGES.append({
    "path": OVERLOAD["page"],
    "title": "OverLoad — Téléchargement Windows & médias | OverX",
    "description": OVERLOAD["short"],
    "active": "overload",
    "og_image": "overload.png",
    "body": _OVERLOAD_BODY,
    "faqs": OVERLOAD_FAQ,
    "ld_extra": lambda: [{
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": OVERLOAD["name"],
        "applicationCategory": "MultimediaApplication",
        "operatingSystem": "Windows 11 (64 bits)",
        "url": f"{site_url()}/{OVERLOAD['page']}" if site_url() else "index.html",
        "description": OVERLOAD["short"],
        "downloadUrl": OVERLOAD["installer_url"],
        "releaseNotes": OVERLOAD["release_url"],
    }],
})

_CATALOGUE_BODY = r"""
<main id="main-content">
  <section class="page-hero container" data-reveal>
    <p class="eyebrow"><a href="{{ROOT}}index.html">OVERX</a> <span class="crumb-slash">/</span> CATALOGUE</p>
    <h1>Des bots utiles.<br><span>Pas une liste de promesses.</span></h1>
    <p class="hero-lead narrow">Voici les applications réellement documentées aujourd'hui. Les prochains bots seront annoncés quand ils auront un nom, des fonctionnalités et une disponibilité confirmés.</p>
    <div class="catalogue-meta"><span class="catalogue-dot"></span> <span data-bot-count>1</span> bot présenté <span class="meta-divider"></span> Catalogue en construction</div>
  </section>

  <section class="section container section-compact" data-reveal>
    <div class="catalogue-toolbar">
      <label class="catalogue-search"><span aria-hidden="true">⌕</span><input type="search" data-catalogue-search placeholder="Rechercher un bot…" aria-label="Rechercher un bot dans le catalogue"></label>
      <div class="catalogue-filters" role="group" aria-label="Filtrer par catégorie">
        <button class="filter-chip is-active" type="button" data-catalogue-filter="all">Tous</button>
        <button class="filter-chip" type="button" data-catalogue-filter="gaming">Gaming</button>
        <button class="filter-chip" type="button" data-catalogue-filter="moderation">Modération</button>
        <button class="filter-chip" type="button" data-catalogue-filter="utility">Utilitaire</button>
        <button class="filter-chip" type="button" data-catalogue-filter="fun">Fun</button>
      </div>
    </div>
    <div class="catalogue-grid" data-catalogue-grid>
      <article class="catalogue-card catalogue-card-compact" data-bot-card data-category="gaming" data-search="freegamedrop jeux gratuits steam epic games store gog ubisoft alertes offres gaming" data-spotlight>
        <div class="catalogue-visual"><div class="catalogue-visual-grid"></div><div class="catalogue-logo">FG<span>D</span></div><div class="catalogue-stamp">FREE<br>GAME<br>DROP</div><div class="catalogue-orbit"></div><span class="catalogue-tag">01 · GAMING</span></div>
        <div class="catalogue-content">
          <div class="catalogue-top"><span class="eyebrow">JEUX GRATUITS · ALERTES DISCORD</span><span class="status-pill status-neutral"><span></span> Instance publique à confirmer</span></div>
          <h2>FreeGameDrop</h2>
          <p>Repère les jeux gratuits sur Steam, l'Epic Games Store, GOG et Ubisoft, puis aide chaque membre à suivre uniquement les plateformes et offres qui l'intéressent.</p>
          <ul class="check-list"><li>Veille automatique toutes les heures, multi-sources résiliente</li><li>Rôles, salons et panneau de sélection créés par /setup-auto</li><li>Favoris, recherche, préférences et rappels d'expiration</li></ul>
          <div class="catalogue-actions"><a class="button button-primary" href="{{ROOT}}discord-bots/freegamedrop/index.html">Voir la fiche complète <span aria-hidden="true">↗</span></a><a class="button button-outline" data-install-cta href="{{ROOT}}install/index.html#ajouter">Guide d'installation <span aria-hidden="true">↗</span></a></div>
          <p class="micro-note" data-install-status>Application ID / invitation publique à renseigner dans la configuration du site.</p>
        </div>
      </article>
      <p class="catalogue-empty" data-catalogue-empty hidden>Aucun bot ne correspond à cette recherche pour le moment.</p>
    </div>

    <div class="future-panel" data-spotlight><div class="future-lock" aria-hidden="true">⌑</div><div><p class="eyebrow">LA SUITE DE L'ÉCOSYSTÈME</p><h2>Les autres bots arrivent<br><span>quand ils seront prêts.</span></h2><p>Aucun bot fictif ni compteur de lancement : cette page s'enrichira au fil des projets réellement publiés.</p></div><a class="text-link" href="{{ROOT}}roadmap/index.html">Voir la feuille de route <span aria-hidden="true">→</span></a></div>
  </section>
</main>
"""

PAGES.append({
    "path": "discord-bots/index.html",
    "title": "Catalogue de bots Discord — OverX",
    "description": "Parcourez le catalogue OverX : recherchez par nom ou catégorie, découvrez FreeGameDrop et les prochaines applications Discord lorsqu'elles seront prêtes.",
    "active": "bots",
    "body": _CATALOGUE_BODY,
})

_BOT_BODY = r"""
<main id="main-content">
  <section class="product-hero container" id="installation">
    <div class="product-copy" data-reveal>
      <p class="eyebrow"><a href="{{ROOT}}discord-bots/index.html">BOTS</a> <span class="crumb-slash">/</span> FREEGAMEDROP</p>
      <div class="product-heading"><span class="product-mark product-mark-large" aria-hidden="true">FG<span>D</span></span><span class="status-pill status-neutral"><span></span> Disponibilité publique à confirmer</span></div>
      <h1>Ne rate plus<br><span>les jeux gratuits.</span></h1>
      <p class="hero-lead">Toutes les heures, FreeGameDrop vérifie Steam, l'Epic Games Store, GOG et Ubisoft, puis annonce chaque offre dans le salon de sa plateforme. Chaque membre choisit exactement ce qu'il veut suivre.</p>
      <div class="hero-actions">
        <a class="button button-primary" data-install-cta href="{{ROOT}}install/index.html#ajouter">Ajouter à Discord <span aria-hidden="true">↗</span></a>
        <a class="button button-secondary" href="https://github.com/TOFazer/FreeGameDropDev" target="_blank" rel="noopener noreferrer">Voir le code source</a>
        <button class="button button-secondary" type="button" data-share>Copier le lien</button>
      </div>
      <p class="micro-note" data-install-status>L'invitation publique n'est pas encore renseignée. Le bouton d'installation restera inactif jusque-là.</p>
    </div>
    <div class="product-preview-card" aria-label="Exemple illustratif du panneau d'offres FreeGameDrop" data-spotlight data-reveal data-reveal-delay="120">
      <div class="product-preview-top"><span class="preview-led"></span><span>FREEGAMEDROP</span><span class="preview-top-right">APERÇU</span></div>
      <div class="product-preview-body">
        <div class="offer-type"><span>✦</span> EXEMPLE D'ANNONCE</div>
        <h2>🔥 Offre exceptionnelle</h2>
        <p>Cyberpunk 2077 · <s>59,99 €</s> ➜ GRATUIT · 🔵 Steam ·  dans 23 heures. Un jeu complet d'une valeur d'au moins 19,99 € offert temporairement.</p>
        <div class="offer-platforms"><span class="platform-icon platform-epic">E</span><span>Epic Games Store</span><span class="platform-separator">·</span><span>🔵 Steam</span><span class="platform-separator">·</span><span>🟣 GOG</span><span class="platform-separator">·</span><span>🔷 Ubisoft</span></div>
        <div class="preview-cta-line"><span>🎁 Récupérer le jeu</span><span aria-hidden="true">→</span></div>
      </div>
      <div class="preview-disclaimer">Maquette de présentation · pas une annonce en direct</div>
    </div>
  </section>

  {{PLATFORM_STRIP}}

  <section class="section section-alt">
    <div class="container">
      <div class="section-heading" data-reveal><p class="eyebrow">FONCTIONNALITÉS DOCUMENTÉES</p><h2>Tout ce qu'il faut<br><span>pour trouver sa prochaine offre.</span></h2><p class="section-intro">Les fonctionnalités ci-dessous sont tirées de la documentation du dépôt FreeGameDropDev. L'état de l'instance publique n'est pas vérifié par ce site.</p></div>
      <div class="feature-grid">
        <article class="feature-card" data-spotlight data-reveal><div class="feature-icon icon-violet">⌁</div><h3>Multi-sources résilientes</h3><p>GamerPower et l'API officielle Epic agrégées en parallèle : une source en panne ne bloque jamais les autres.</p><span class="feature-index">01</span></article>
        <article class="feature-card" data-spotlight data-reveal><div class="feature-icon icon-orange">🔥</div><h3>Offres exceptionnelles</h3><p>Un jeu complet d'au moins 19,99 € offert temporairement est mis en avant, avec la valeur affichée par la source.</p><span class="feature-index">02</span></article>
        <article class="feature-card" data-spotlight data-reveal><div class="feature-icon icon-cyan">◉</div><h3>Un salon par plateforme</h3><p>/setup-auto crée catégorie, rôles, salons en lecture seule et panneau de boutons ; chaque membre choisit ses plateformes.</p><span class="feature-index">03</span></article>
        <article class="feature-card" data-spotlight data-reveal><div class="feature-icon icon-pink">♡</div><h3>Favoris & rappels</h3><p>Bouton ❤️, /favoris, alertes privées et « ton jeu favori expire dans 6 heures » : rien ne passe à la trappe.</p><span class="feature-index">04</span></article>
        <article class="feature-card" data-spotlight data-reveal><div class="feature-icon icon-lime">⌕</div><h3>Catalogue & préférences</h3><p>/free, /historique, /recherche et /preferences : filtres par plateforme, type, valeur minimale et genre.</p><span class="feature-index">05</span></article>
        <article class="feature-card" data-spotlight data-reveal><div class="feature-icon icon-blue">◎</div><h3>Santé & statistiques</h3><p>/sante mesure le bot, Discord, la base et chaque source ; /stats n'affiche que des valeurs réellement mesurées.</p><span class="feature-index">06</span></article>
      </div>
    </div>
  </section>

  <section class="section container" data-reveal>
    <div class="privacy-callout" data-spotlight><div class="callout-icon" aria-hidden="true">➕</div><div><p class="eyebrow">BOUCLE DE DÉCOUVERTE</p><h2>Chaque annonce présente le bot.</h2><p>Chaque message se termine par le pied « 🎁 FreeGameDrop » et un bouton « ➕ Ajouter FreeGameDrop » : un serveur alerté devient une vitrine, sans spam. La commande /info construit aussi le lien d'invitation de l'instance.</p><a class="text-link" href="{{ROOT}}install/index.html#ajouter">Comment se passe l'ajout ? <span aria-hidden="true">→</span></a></div></div>
  </section>

  <section class="section container two-column-section" data-reveal>
    <div><p class="eyebrow">COMMANDES</p><h2>À portée<br><span>de slash.</span></h2><p class="section-intro">Les commandes de configuration sont réservées aux administrateurs ; les commandes personnelles répondent en privé quand c'est pertinent.</p><a class="text-link" href="{{ROOT}}docs/index.html#commandes">Le guide complet <span aria-hidden="true">→</span></a></div>
    {{COMMAND_TABLE}}
  </section>

  <section class="section section-alt" data-reveal>
    <div class="container install-help-layout">
      <div><p class="eyebrow">QUESTIONS FRÉQUENTES</p><h2>Avant de<br><span>te décider.</span></h2><p class="section-intro">Les réponses viennent de la documentation du dépôt, pas d'arguments marketing.</p></div>
      {{FAQ_BLOCK}}
    </div>
  </section>

  <section class="section container" data-reveal>
    <div class="privacy-callout" data-spotlight><div class="callout-icon" aria-hidden="true">⌑</div><div><p class="eyebrow">DONNÉES & CONFIDENTIALITÉ</p><h2>Pas de collecte de messages.</h2><p>Le bot ne stocke ni le contenu des messages ni la preuve qu'un jeu a été réclamé. Il conserve la configuration des serveurs, les offres publiques, les favoris et préférences liés à un identifiant Discord ; /mes-donnees les supprime.</p><a class="text-link" href="{{ROOT}}privacy/index.html">Lire la politique de confidentialité <span aria-hidden="true">→</span></a></div></div>
  </section>

  {{OTHER_BOTS}}

  <section class="section container" data-reveal>
    <div class="cta-panel" data-spotlight>
      <div class="cta-glow" aria-hidden="true"></div>
      <div><p class="eyebrow">PRÊT À ESSAYER ?</p><h2>Sur ton serveur.<br><span>En quelques étapes.</span></h2><p>Invite le bot, lance /setup-auto, choisis tes plateformes. Le guide d'installation détaille chaque étape et les permissions.</p></div>
      <div class="cta-actions"><a class="button button-light" data-install-cta href="{{ROOT}}install/index.html#ajouter">Ajouter FreeGameDrop <span aria-hidden="true">↗</span></a><a class="text-link" href="{{ROOT}}discord-bots/freegamedrop/auto-hebergement/index.html">Auto-héberger le bot <span aria-hidden="true">→</span></a></div>
    </div>
  </section>
</main>
"""

PAGES.append({
    "path": "discord-bots/freegamedrop/index.html",
    "title": "FreeGameDrop — bot Discord jeux gratuits (Steam, Epic, GOG, Ubisoft) | OverX",
    "description": "FreeGameDrop annonce les jeux gratuits de Steam, Epic Games Store, GOG et Ubisoft sur Discord : salons par plateforme, alertes personnalisées, favoris, rappels et statistiques mesurées. Open source (MIT).",
    "active": "bots",
    "og_image": "freegamedrop.png",
    "body": _BOT_BODY,
    "faqs": FGD_FAQ,
    "ld_extra": lambda: [software_ld(BOTS[0])],
})

_SELFHOST_BODY = r"""
<main id="main-content">
  <section class="page-hero container" data-reveal>
    <p class="eyebrow"><a href="{{ROOT}}discord-bots/freegamedrop/index.html">FREEGAMEDROP</a> <span class="crumb-slash">/</span> AUTO-HÉBERGEMENT</p>
    <h1>Ton instance.<br><span>Ton bot.</span></h1>
    <p class="hero-lead narrow">FreeGameDrop est publié sous licence MIT : le code se lit, se vérifie et s'héberge librement, en Python ou avec Docker. Cette page résume le guide du dépôt FreeGameDropDev.</p>
  </section>
  <section class="section container section-compact docs-layout" data-reveal>
    <aside class="docs-toc"><p class="eyebrow">DANS CE GUIDE</p><a href="#demarrage">Démarrage express</a><a href="#docker">Docker & PaaS</a><a href="#env">DEV / PROD</a><a href="#dashboard">Tableau de bord web</a><a href="#api">Relier ce site</a></aside>
    <div class="docs-content">
      <section class="doc-section" id="demarrage"><p class="eyebrow">01 · DÉMARRER</p><h2>Installation express</h2><p>Prérequis : Python 3.10 ou plus. Le dépôt contient <code>requirements.txt</code>, un modèle <code>.env.example</code> et la commande <code>/setup-auto</code> qui crée salons, rôles et panneau dès la première exécution.</p><div class="code-block"><pre><code>git clone https://github.com/TOFazer/FreeGameDropDev.git
cd FreeGameDropDev
python -m venv .venv &amp;&amp; source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # puis colle ton token Discord
python main.py</code></pre></div><p>Aucun intent privilégié n'est nécessaire. La vérification des offres démarre immédiatement, puis continue toutes les heures.</p></section>
      <section class="doc-section" id="docker"><p class="eyebrow">02 · HÉBERGER EN CONTINU</p><h2>Docker ou PaaS</h2><p>Un bot doit tourner en permanence. Le dépôt fournit un <code>Dockerfile</code> (base SQLite dans <code>/app/data</code>, à monter sur un volume) et un <code>docker-compose.dev.yml</code> pour l'environnement de développement. Les PaaS type Railway, Render ou Fly.io détectent le Dockerfile automatiquement.</p><div class="code-block"><pre><code>docker build -t freegamedrop .
docker run -d --env-file .env \
  -v freegamedrop-prod-data:/app/data \
  --restart unless-stopped freegamedrop</code></pre></div></section>
      <section class="doc-section" id="env"><p class="eyebrow">03 · BONNES PRATIQUES</p><h2>DEV et PROD séparés</h2><p>Le même code, jamais les mêmes ressources : application Discord, token et base SQLite distincts. Au démarrage, le bot refuse de se lancer si le jeton, l'application ou la base ne correspondent pas à l'environnement déclaré — impossible de connecter un token DEV sur la base de production.</p><div class="notice notice-warn"><strong>Secrets</strong><p><code>DISCORD_TOKEN</code>, <code>DISCORD_CLIENT_SECRET</code> et <code>DATABASE_URL</code> restent côté serveur. Ce site statique ne doit jamais les contenir.</p></div></section>
      <section class="doc-section" id="dashboard"><p class="eyebrow">04 · OPTIONNEL</p><h2>Tableau de bord web</h2><p>Un serveur web optionnel (aiohttp, déjà dans les dépendances) ajoute « Se connecter avec Discord » (scopes <code>identify guilds</code> uniquement), la configuration des serveurs gérables, les statistiques publiques et l'état mesuré. Le jeton OAuth du membre n'est jamais stocké.</p></section>
      <section class="doc-section" id="api"><p class="eyebrow">05 · RELIER CE SITE</p><h2>Publier tes vrais chiffres</h2><p>Le tableau de bord expose <code>GET /api/stats</code> et <code>GET /api/health</code> en JSON, sans aucun secret. Renseigne <code>statsApiUrl</code> et <code>healthApiUrl</code> dans <code>assets/site-config.js</code> : les compteurs de l'accueil et la page Statut afficheront les mesures réelles de ton instance — jamais de valeur inventée en attendant.</p><a class="button button-secondary" href="https://github.com/TOFazer/FreeGameDropDev" target="_blank" rel="noopener noreferrer">Lire le README du bot <span aria-hidden="true">↗</span></a></section>
    </div>
  </section>
</main>
"""

PAGES.append({
    "path": "discord-bots/freegamedrop/auto-hebergement/index.html",
    "title": "Auto-héberger FreeGameDrop — bot Discord open source (MIT) | OverX",
    "description": "FreeGameDrop est open source sous licence MIT : installation Python ou Docker, variables d'environnement, séparation DEV/PROD, tableau de bord web et endpoints /api/health et /api/stats documentés.",
    "active": "bots",
    "og_image": "freegamedrop.png",
    "body": _SELFHOST_BODY,
})

for _platform in FGD_PLATFORMS:
    PAGES.append(platform_page(_platform))

_INSTALL_BODY = r"""
<main id="main-content">
  <section class="install-hero container">
    <div class="install-copy" data-reveal>
      <p class="eyebrow"><a href="{{ROOT}}discord-bots/freegamedrop/index.html">FREEGAMEDROP</a> <span class="crumb-slash">/</span> INSTALLATION</p>
      <span class="status-pill status-neutral install-state" data-install-state><span></span> Lien de production à configurer</span>
      <h1>Sur ton serveur.<br><span>En quelques étapes.</span></h1>
      <p class="hero-lead">Le parcours est celui de Discord : autoriser le bot, choisir un serveur, puis lancer son assistant de configuration. Pas de compte OverX à créer.</p>
      <div class="install-copy-actions"><a class="button button-primary install-main-cta" data-discord-install href="#ajouter" aria-disabled="true">Invitation Discord à configurer <span aria-hidden="true">↗</span></a><button class="button button-secondary copy-admin-button" data-copy-admin type="button" hidden>Copier un message pour mon admin</button></div>
      <p class="install-live-note" data-install-status>Le lien officiel de l'application PROD n'a pas encore été renseigné.</p>
    </div>
    <div class="install-flow-card" aria-label="Les trois étapes de l'installation" data-spotlight data-reveal data-reveal-delay="120">
      <div class="install-flow-header"><span class="flow-logo">FG<span>D</span></span><div><strong>Installation FreeGameDrop</strong><small>Parcours dans Discord</small></div><span class="flow-lock" aria-hidden="true">⌑</span></div>
      <div class="flow-step"><span class="flow-number">01</span><span class="flow-icon">↗</span><div><strong>Autoriser l'application</strong><small>Discord affiche les permissions demandées</small></div><span class="flow-check">✓</span></div>
      <div class="flow-connector"></div>
      <div class="flow-step"><span class="flow-number">02</span><span class="flow-icon icon-cyan">⌂</span><div><strong>Choisir ton serveur</strong><small>Il faut pouvoir gérer le serveur</small></div><span class="flow-check">✓</span></div>
      <div class="flow-connector"></div>
      <div class="flow-step"><span class="flow-number">03</span><span class="flow-icon icon-lime">⚙</span><div><strong>Lancer <code>/setup-auto</code></strong><small>Choisis les plateformes à suivre</small></div><span class="flow-check">✓</span></div>
      <div class="install-flow-footer"><span class="tiny-pulse"></span> Tu restes sur le parcours officiel Discord</div>
    </div>
  </section>

  <section class="section section-alt" id="ajouter" data-reveal>
    <div class="container">
      <div class="section-heading"><p class="eyebrow">INSTALLATION, PAS À PAS</p><h2>Tu sais déjà utiliser Discord ?<br><span>Tu peux installer le bot.</span></h2><p class="section-intro">Suis ces étapes dans l'ordre. Si tu bloques à l'étape 2, ce n'est probablement pas toi : Discord réserve l'ajout d'applications aux membres qui peuvent gérer le serveur.</p></div>
      <div class="install-steps-grid">
        <article class="install-step-card" data-spotlight><span class="install-step-index">ÉTAPE 01</span><div class="install-step-icon">↗</div><h3>Clique sur Ajouter à Discord</h3><p>Le bouton ouvre la page d'autorisation officielle de Discord avec les scopes <strong>bot</strong> et <strong>applications.commands</strong>. Connecte-toi au compte qui gère ton serveur si Discord te le demande.</p></article>
        <article class="install-step-card" data-spotlight><span class="install-step-index">ÉTAPE 02</span><div class="install-step-icon icon-cyan">⌂</div><h3>Sélectionne ton serveur</h3><p>Choisis le serveur dans la liste. Il faut la permission <strong>Gérer le serveur</strong> ou <strong>Administrateur</strong>. Si le serveur n'apparaît pas, demande à un admin de faire l'installation.</p></article>
        <article class="install-step-card" data-spotlight><span class="install-step-index">ÉTAPE 03</span><div class="install-step-icon icon-lime">✓</div><h3>Autorise puis configure</h3><p>Vérifie les permissions affichées par Discord, clique sur <strong>Autoriser</strong>, puis lance <code>/setup-auto</code> dans le serveur pour créer les salons de jeux.</p></article>
      </div>
    </div>
  </section>

  <section class="section container" data-reveal>
    <div class="install-permissions-layout">
      <div><p class="eyebrow">PERMISSIONS AFFICHÉES PAR DISCORD</p><h2>Le minimum utile<br><span>pour faire fonctionner le bot.</span></h2><p class="section-intro">FreeGameDrop doit pouvoir créer les espaces de jeux et publier les offres. Discord t'affichera la demande avant l'ajout. Pas d'Administrateur.</p></div>
      <div class="install-permissions-card" data-spotlight><div class="permission-heading"><span class="permission-discord-icon">◉</span><div><strong>Permissions du serveur</strong><small>Demandées lors de l'ajout</small></div></div><div class="permission-check-row"><span>✓</span> Gérer les salons</div><div class="permission-check-row"><span>✓</span> Gérer les rôles</div><div class="permission-check-row"><span>✓</span> Voir les salons</div><div class="permission-check-row"><span>✓</span> Envoyer des messages</div><div class="permission-check-row"><span>✓</span> Intégrer des liens</div><div class="permission-check-row"><span>✓</span> Lire l'historique des messages</div><div class="permission-check-row"><span>✓</span> Gérer les messages</div><div class="permission-optional"><strong>Deux permissions facultatives incluses :</strong><p>Lire l'historique et gérer les messages servent au nettoyage d'anciens panneaux dans #choisir-ses-roles ; elles ne sont pas nécessaires pour recevoir les alertes.</p></div><p class="permission-footnote">Discord affiche la demande exacte avant l'ajout. Tu peux annuler si les permissions ne te conviennent pas.</p></div>
    </div>
  </section>

  <section class="section section-alt" data-reveal>
    <div class="container install-help-layout">
      <div><p class="eyebrow">ÇA NE MARCHE PAS ?</p><h2>Les blocages<br><span>les plus fréquents.</span></h2><p class="section-intro">Une aide directe plutôt qu'un écran d'erreur incompréhensible.</p></div>
      <div class="install-help-list">
        <details class="faq-item"><summary>Mon serveur n'apparaît pas dans Discord.</summary><p>Ton compte n'a probablement pas la permission de gérer ce serveur. Demande à un administrateur ou à un membre ayant « Gérer le serveur » de lancer l'invitation.</p></details>
        <details class="faq-item"><summary>Le bot est ajouté, mais aucun salon n'a été créé.</summary><p>L'installation ajoute l'application au serveur ; la configuration des salons se lance ensuite avec <code>/setup-auto</code>. Le bot doit être en ligne et conserver les permissions nécessaires.</p></details>
        <details class="faq-item"><summary>Les commandes n'apparaissent pas.</summary><p>Le bot a besoin du scope <code>applications.commands</code> ; sinon attends quelques minutes ou redémarre Discord.</p></details>
        <details class="faq-item"><summary>Discord refuse une permission ou l'invitation semble incorrecte.</summary><p>Vérifie que l'invitation correspond à l'application de production. Le lien affiché sur OverX est celui fourni par l'équipe ; si Discord montre un serveur ou des permissions inattendus, annule et contacte le support.</p></details>
        <details class="faq-item"><summary>Je suis sur téléphone.</summary><p>Le même bouton ouvre Discord ou son navigateur. Connecte-toi au bon compte, choisis le serveur, puis confirme l'autorisation. Si tu ne peux pas gérer le serveur, demande à son administrateur.</p></details>
      </div>
    </div>
  </section>

  <section class="section container" data-reveal>
    <div class="install-bottom-cta" data-spotlight><div><p class="eyebrow">BESOIN D'UN COUP DE MAIN ?</p><h2>On t'accompagne.</h2><p>Consulte le guide complet ou signale un problème dans le dépôt du bot. Ne publie jamais de token Discord.</p></div><div class="install-bottom-actions"><a class="button button-primary" href="{{ROOT}}docs/index.html#installation">Lire le guide complet <span aria-hidden="true">→</span></a><a class="text-link" href="{{ROOT}}support/index.html">Contacter le support <span aria-hidden="true">→</span></a></div></div>
  </section>
</main>
"""

PAGES.append({
    "path": "install/index.html",
    "title": "Installer FreeGameDrop sur Discord — OverX",
    "description": "Guide pas à pas pour ajouter FreeGameDrop à un serveur Discord : autoriser l'application avec les bons scopes et permissions, sélectionner son serveur et lancer /setup-auto.",
    "active": "install",
    "body": _INSTALL_BODY,
})

_DOCS_BODY = r"""
<main id="main-content">
  <section class="page-hero container docs-hero" data-reveal>
    <p class="eyebrow">GUIDES OVERX <span class="crumb-slash">/</span> FREEGAMEDROP</p>
    <h1>La documentation<br><span>sans chercher partout.</span></h1>
    <p class="hero-lead narrow">Les étapes ci-dessous suivent les commandes et comportements décrits dans le dépôt FreeGameDropDev. Le lien d'invitation public reste à configurer.</p>
    <div class="docs-search-note"><span aria-hidden="true">⌕</span><span>Une question précise ? Utilise la recherche de ton navigateur avec <kbd>Ctrl</kbd> <span>+</span> <kbd>F</kbd>.</span></div>
  </section>

  <section class="section container docs-layout" data-reveal>
    <aside class="docs-toc"><p class="eyebrow">DANS CE GUIDE</p><a href="#installation">Installation</a><a href="#configuration">Configuration</a><a href="#commandes">Commandes</a><a href="#permissions">Permissions</a><a href="#faq">FAQ</a><a href="#auto-hebergement">Auto-hébergement</a></aside>
    <div class="docs-content">
      <section class="doc-section" id="installation"><p class="eyebrow">01 · DÉMARRER</p><h2>Installer le bot</h2><ol class="numbered-steps"><li><strong>Ajoute FreeGameDrop à ton serveur.</strong><p>L'invitation publique n'est pas encore configurée sur ce site. Elle sera activée dès que l'Application ID de l'instance sera fourni.</p></li><li><strong>Choisis un serveur où tu peux gérer les applications.</strong><p>Discord demande la permission de gérer le serveur pour autoriser l'installation d'un bot.</p></li><li><strong>Vérifie les permissions puis autorise.</strong><p>Le bot a besoin des permissions documentées ci-dessous pour créer les salons, rôles et annonces.</p></li><li><strong>Lance <code>/setup-auto</code> dans ton serveur.</strong><p>Sélectionne les plateformes souhaitées, puis valide la création ou la mise à jour de la configuration.</p></li></ol><div class="notice notice-warn"><strong>À savoir</strong><p>La disponibilité de l'instance et son URL d'invitation ne sont pas encore connectées au site. Le code source reste consultable sur GitHub.</p><a class="text-link" href="https://github.com/TOFazer/FreeGameDropDev" target="_blank" rel="noopener noreferrer">Ouvrir FreeGameDropDev <span aria-hidden="true">↗</span></a></div></section>

      <section class="doc-section" id="configuration"><p class="eyebrow">02 · CONFIGURATION</p><h2>Configurer les notifications</h2><p><code>/setup-auto</code> crée ou met à jour la catégorie de jeux, les rôles de plateforme, les salons dédiés et le panneau de sélection. Les membres peuvent cliquer sur les boutons pour obtenir ou retirer un rôle de plateforme.</p><ul class="doc-bullets"><li>Les salons de jeux sont organisés par plateforme (🔵 Steam, ⚪ Epic,  GOG, 🔷 Ubisoft) et configurés en lecture seule pour les membres.</li><li>Les commandes <code>/config</code> et <code>/acces-salon-roles</code> permettent aux administrateurs d'ajuster la configuration décrite par le bot.</li><li><code>/rappel-salon</code> permet de choisir le salon qui reçoit les rappels de fin d'offre.</li><li>Le bot est documenté comme vérifiant les offres toutes les heures ; l'état réel de l'instance se vérifie avec <code>/sante</code>.</li></ul></section>

      <section class="doc-section" id="commandes"><p class="eyebrow">03 · RÉFÉRENCE</p><h2>Commandes principales</h2>{{COMMAND_TABLE}}<p class="fine-print">La liste complète des commandes, leurs options exactes et les notes de version sont maintenues dans le dépôt du bot.</p></section>

      <section class="doc-section" id="permissions"><p class="eyebrow">04 · AUTORISATIONS</p><h2>Permissions nécessaires</h2><p>La documentation du dépôt recommande les permissions Discord utiles à la création des espaces de jeux et à l'envoi des annonces :</p><div class="permission-grid"><span>Gérer les salons</span><span>Gérer les rôles</span><span>Voir les salons</span><span>Envoyer des messages</span><span>Intégrer des liens</span></div><div class="notice"><strong>Rôles de plateforme</strong><p>Place le rôle du bot au-dessus des rôles qu'il doit attribuer. Discord empêchera sinon le bot de les gérer.</p></div></section>

      <section class="doc-section" id="faq"><p class="eyebrow">05 · QUESTIONS FRÉQUENTES</p><h2>FAQ</h2>{{FAQ_BLOCK}}<a class="text-link" href="{{ROOT}}support/index.html">Ouvrir la page Support <span aria-hidden="true">→</span></a></section>

      <section class="doc-section" id="auto-hebergement"><p class="eyebrow">06 · POUR LES DÉVELOPPEURS</p><h2>Auto-hébergement</h2><p>Le dépôt FreeGameDropDev contient les instructions détaillées sur Python, Docker, les variables d'environnement, les environnements DEV/PROD et les tests. Les secrets doivent rester côté serveur, jamais dans le site.</p><a class="button button-secondary" href="{{ROOT}}discord-bots/freegamedrop/auto-hebergement/index.html">Guide d'auto-hébergement OverX <span aria-hidden="true">→</span></a></section>
    </div>
  </section>
</main>
"""

PAGES.append({
    "path": "docs/index.html",
    "title": "Documentation FreeGameDrop — OverX",
    "description": "Guide d'installation, de configuration, commandes et permissions pour FreeGameDrop, le bot Discord de jeux gratuits d'OverX (Steam, Epic, GOG, Ubisoft).",
    "active": "docs",
    "body": _DOCS_BODY,
    "faqs": FGD_FAQ,
})

_STATUS_BODY = r"""
<main id="main-content">
  <section class="page-hero container status-hero" data-reveal>
    <p class="eyebrow">OVERX <span class="crumb-slash">/</span> STATUS</p>
    <h1>Un statut clair.<br><span>Même quand il manque des données.</span></h1>
    <p class="hero-lead narrow">Nous n'affichons pas de pastilles vertes sans vérification. Quand <code>healthApiUrl</code> est renseigné, ce panneau lit <code>/api/health</code> du bot ; sinon tout reste « non mesuré ».</p>
  </section>
  <section class="section container section-compact" data-reveal>
    <div class="status-summary" data-spotlight><div class="status-summary-icon">—</div><div><p class="eyebrow">ÉTAT ACTUEL DE LA PAGE</p><h2 data-health-title>Non mesuré en temps réel</h2><p>Dernière vérification automatique : <strong data-health-updated>aucune sonde configurée</strong>.</p></div><span class="status-pill status-neutral"><span></span> Données non connectées</span></div>
    <div class="health-panel" data-health-panel hidden>
      <div class="health-row"><span class="health-dot" data-health-dot="bot">?</span><div><strong>Bot</strong><small data-health-text="bot">—</small></div></div>
      <div class="health-row"><span class="health-dot" data-health-dot="discord">?</span><div><strong>Discord</strong><small data-health-text="discord">—</small></div></div>
      <div class="health-row"><span class="health-dot" data-health-dot="database">?</span><div><strong>Base de données</strong><small data-health-text="database">—</small></div></div>
      <div class="health-row"><span class="health-dot" data-health-dot="sources">?</span><div><strong>Sources d'offres</strong><small data-health-text="sources">—</small></div></div>
      <p class="permission-footnote" data-health-footnote>Source : l'endpoint /api/health public du bot, sans secret.</p>
    </div>
    <div class="service-list">
      <article class="service-row"><div class="service-indicator indicator-unknown">?</div><div><h3>FreeGameDrop · bot Discord</h3><p>Aucun endpoint public de santé n'a été fourni. Sur un serveur où le bot est installé, <code>/sante</code> est la commande documentée pour vérifier ses composants.</p></div><span class="service-state">NON MESURÉ</span></article>
      <article class="service-row"><div class="service-indicator indicator-unknown">?</div><div><h3>Site OverX</h3><p>Page de statut statique. Elle n'effectue pas de contrôle de disponibilité de l'hébergement.</p></div><span class="service-state">NON MESURÉ</span></article>
      <article class="service-row"><div class="service-indicator indicator-muted">—</div><div><h3>Dashboard & API OverX</h3><p>Le tableau de bord du bot expose <code>/api/health</code> et <code>/api/stats</code> : ce site sait les lire dès que l'URL publique est configurée.</p></div><span class="service-state">PRÊT À BRANCHER</span></article>
    </div>
    <div class="notice notice-warn status-note"><strong>Pourquoi pas d'uptime ?</strong><p>Un pourcentage comme « 99,9 % » doit venir d'une mesure horodatée et reproductible. Il sera affiché lorsqu'une sonde et une source de données auront été mises en place.</p></div>
    <div class="status-links"><a class="text-link" href="https://github.com/TOFazer/FreeGameDropDev" target="_blank" rel="noopener noreferrer">Dépôt FreeGameDropDev <span aria-hidden="true">↗</span></a><a class="text-link" href="{{ROOT}}support/index.html">Signaler un problème <span aria-hidden="true">→</span></a></div>
  </section>
</main>
"""

PAGES.append({
    "path": "status/index.html",
    "title": "Statut des services — OverX",
    "description": "État de transparence OverX : le panneau de santé se branche sur /api/health du bot dès qu'une URL publique est configurée ; aucune valeur inventée en attendant.",
    "active": "status",
    "body": _STATUS_BODY,
})

_CHANGELOG_BODY = r"""
<main id="main-content">
  <section class="page-hero container" data-reveal>
    <p class="eyebrow">OVERX <span class="crumb-slash">/</span> CHANGELOG</p>
    <h1>Ce qui change.<br><span>Quand ça change vraiment.</span></h1>
    <p class="hero-lead narrow">Les versions et changements publics seront consignés ici. Aucune version ni date de lancement n'a été inventée pour remplir la page.</p>
  </section>
  <section class="section container section-compact" data-reveal>
    <div class="empty-state" data-spotlight><div class="empty-orbit" aria-hidden="true"><span>✦</span></div><p class="eyebrow">JOURNAL DES VERSIONS</p><h2>Aucune note de version publiée pour le moment.</h2><p>Le code et les évolutions de FreeGameDrop sont consultables dans son dépôt GitHub. Les prochaines notes visibles ici devront correspondre à des changements réellement publiés.</p><a class="button button-primary" href="https://github.com/TOFazer/FreeGameDropDev" target="_blank" rel="noopener noreferrer">Suivre le dépôt du bot <span aria-hidden="true">↗</span></a></div>
    <div class="changelog-how"><span class="timeline-mark"></span><div><p class="eyebrow">À VENIR</p><h3>Notes de version OverX</h3><p>Cette page pourra accueillir les nouvelles fonctionnalités, améliorations et corrections, avec leur date et leur version vérifiées.</p></div></div>
  </section>
</main>
"""

PAGES.append({
    "path": "changelog/index.html",
    "title": "Changelog — OverX",
    "description": "Notes de version et évolutions des bots OverX.",
    "active": "changelog",
    "body": _CHANGELOG_BODY,
})

_ROADMAP_BODY = r"""
<main id="main-content">
  <section class="page-hero container" data-reveal>
    <p class="eyebrow">OVERX <span class="crumb-slash">/</span> ROADMAP</p>
    <h1>Une étape à la fois.<br><span>Sans brûler les étapes.</span></h1>
    <p class="hero-lead narrow">La priorité est de rendre le premier bot compréhensible, testable et transparent avant de multiplier les applications ou de créer un dashboard.</p>
  </section>
  <section class="section container section-compact" data-reveal>
    <div class="roadmap-list">
      <article class="roadmap-item roadmap-now"><div class="roadmap-marker"><span>01</span></div><div class="roadmap-copy"><div class="roadmap-top"><span class="eyebrow">FONDATIONS</span><span class="status-pill status-current"><span></span> PUBLIÉ</span></div><h2>FreeGameDrop & OverX v1</h2><p>Site indexable, fiches par bot et par plateforme, pages d'installation, de support, de statut et légales ; sitemap, métadonnées de partage et données structurées pour la découverte.</p><div class="roadmap-tags"><span>Site responsive</span><span>SEO & sitemap</span><span>Pages plateformes</span><span>Transparence</span></div></div></article>
      <article class="roadmap-item"><div class="roadmap-marker"><span>02</span></div><div class="roadmap-copy"><div class="roadmap-top"><span class="eyebrow">MESURE</span><span class="status-pill status-neutral"><span></span> À BRANCHER</span></div><h2>Statistiques réelles & statut live</h2><p>Relier <code>statsApiUrl</code> et <code>healthApiUrl</code> au tableau de bord du bot pour publier serveurs, offres et disponibilité mesurés — jamais estimés.</p><div class="roadmap-tags"><span>/api/stats</span><span>/api/health</span><span>Compteurs réels</span></div></div></article>
      <article class="roadmap-item"><div class="roadmap-marker"><span>03</span></div><div class="roadmap-copy"><div class="roadmap-top"><span class="eyebrow">APRÈS VALIDATION</span><span class="status-pill status-neutral"><span></span> À PLANIFIER</span></div><h2>Connexion Discord & dashboard</h2><p>OAuth2 (<code>identify guilds</code> côté dashboard, jamais dans le lien d'invitation du bot), liste des serveurs gérables et configuration web de FreeGameDrop. Nécessitera un backend, des secrets serveur et une politique de confidentialité finalisée.</p><div class="roadmap-tags"><span>OAuth2</span><span>Sessions sécurisées</span><span>API</span></div></div></article>
      <article class="roadmap-item"><div class="roadmap-marker"><span>04</span></div><div class="roadmap-copy"><div class="roadmap-top"><span class="eyebrow">DÉCOUVERTE</span><span class="status-pill status-neutral"><span></span> À PRÉPARER</span></div><h2>App Directory & communauté</h2><p>Application vérifiée, description, tags, serveur de support public et URL d'installation : les prérequis du répertoire d'applications Discord, puis l'internationalisation et de nouveaux bots.</p><div class="roadmap-tags"><span>App Directory</span><span>Serveur communautaire</span><span>Anglais</span></div></div></article>
    </div>
    <div class="notice"><strong>La roadmap peut évoluer.</strong><p>Les idées ne sont pas des engagements de livraison. Les changements réellement publiés apparaîtront dans le <a class="inline-link" href="{{ROOT}}changelog/index.html">changelog</a>.</p></div>
  </section>
</main>
"""

PAGES.append({
    "path": "roadmap/index.html",
    "title": "Feuille de route — OverX",
    "description": "Les étapes prévues pour faire évoluer OverX : FreeGameDrop, le site, les statistiques réelles, la connexion Discord et l'écosystème de bots.",
    "active": "roadmap",
    "body": _ROADMAP_BODY,
})

_SUPPORT_BODY = r"""
<main id="main-content">
  <section class="page-hero container" data-reveal>
    <p class="eyebrow">OVERX <span class="crumb-slash">/</span> SUPPORT</p>
    <h1>On peut t'aider.<br><span>Voici le bon endroit.</span></h1>
    <p class="hero-lead narrow">La communauté Discord OverX n'a pas encore de lien public renseigné. En attendant, le dépôt du bot permet de consulter le code et de signaler un problème.</p>
  </section>
  <section class="section container section-compact" data-reveal>
    <div class="support-grid">
      <article class="support-card support-card-primary" data-spotlight><div class="support-icon">?</div><p class="eyebrow">UNE QUESTION OU UN BUG ?</p><h2>Ouvrir une discussion GitHub</h2><p>Décris le problème, la commande concernée et ce que tu as essayé. Ne publie jamais de token, mot de passe ou donnée privée.</p><a class="button button-primary" href="https://github.com/TOFazer/FreeGameDropDev/issues" target="_blank" rel="noopener noreferrer">Aller au support FreeGameDrop <span aria-hidden="true">↗</span></a></article>
      <article class="support-card" data-spotlight><div class="support-icon icon-cyan">⌕</div><p class="eyebrow">AVANT DE SIGNALER</p><h2>Vérifier le guide</h2><p>Les étapes de configuration, les commandes principales et les permissions nécessaires sont regroupées dans la documentation OverX.</p><a class="text-link" href="{{ROOT}}docs/index.html">Ouvrir la documentation <span aria-hidden="true">→</span></a></article>
      <article class="support-card" data-spotlight><div class="support-icon icon-lime">⌘</div><p class="eyebrow">CODE & CONTRIBUTIONS</p><h2>Explorer le projet</h2><p>Le dépôt fourni pour FreeGameDrop est un dépôt de développement. Consulte son README pour les consignes d'installation, d'environnement et de contribution.</p><a class="text-link" href="https://github.com/TOFazer/FreeGameDropDev" target="_blank" rel="noopener noreferrer">Voir le dépôt GitHub <span aria-hidden="true">↗</span></a></article>
    </div>
    <div class="community-panel community-panel-compact" data-community-cta hidden>
      <div><p class="eyebrow">COMMUNAUTÉ OVERX</p><h2>Le serveur Discord</h2><p>Quand l'invitation publique existera, elle apparaîtra ici automatiquement via <code>communityInviteUrl</code>.</p></div>
      <a class="button button-light" data-community-cta href="#" hidden>Rejoindre <span aria-hidden="true">→</span></a>
    </div>
    <div class="notice notice-warn"><strong>Discord support</strong><p>Un lien d'invitation au serveur de communauté n'a pas été fourni. Il pourra être ajouté dans <code>assets/site-config.js</code> dès qu'il existera.</p></div>
  </section>
</main>
"""

PAGES.append({
    "path": "support/index.html",
    "title": "Support — OverX & FreeGameDrop",
    "description": "Besoin d'aide avec FreeGameDrop ? Consultez la documentation, rejoignez le serveur communautaire (quand il existe) ou signalez un problème dans le dépôt officiel.",
    "active": "support",
    "body": _SUPPORT_BODY,
})

_PRIVACY_BODY = r"""
<main id="main-content">
  <section class="page-hero container legal-hero" data-reveal>
    <p class="eyebrow">INFORMATIONS LÉGALES <span class="crumb-slash">/</span> CONFIDENTIALITÉ</p>
    <h1>Ta vie privée<br><span>n'est pas une option.</span></h1>
    <p class="hero-lead narrow">Cette page décrit la version statique actuelle du site et les données mentionnées dans la documentation de FreeGameDrop.</p>
  </section>
  <section class="section container legal-layout" data-reveal>
    <div class="draft-warning"><span aria-hidden="true">!</span><div><strong>Brouillon à compléter avant publication publique</strong><p>L'identité légale de l'éditeur, l'adresse de contact, l'hébergeur et certaines durées de conservation n'ont pas été communiqués. Ne présente pas ce texte comme une politique finalisée sans validation.</p></div></div>
    <article class="legal-content">
      <p class="legal-updated">État : version de travail · 7 octobre 2026</p>
      <h2>1. Responsable du traitement</h2><p>Éditeur / responsable du traitement : <strong>[À COMPLÉTER : nom ou raison sociale, adresse et moyen de contact]</strong>. Les coordonnées du responsable ne sont pas encore fournies.</p>
      <h2>2. Le site OverX</h2><p>Dans cette première version, le site est constitué de pages statiques. Il ne propose ni connexion Discord, ni formulaire, ni compte, ni dashboard, ni outil d'analyse d'audience ; aucun cookie non essentiel n'est installé par le code du site. Le site peut lire, si elles sont configurées, les API publiques <code>/api/stats</code> et <code>/api/health</code> du bot pour afficher des mesures ; aucune donnée personnelle n'est transmise pour cela.</p><p>Comme pour tout site hébergé, l'hébergeur peut traiter des données techniques de requête (par exemple adresse IP, date, navigateur) dans ses journaux. L'hébergeur et ses durées de conservation devront être précisés lorsque le déploiement sera choisi.</p>
      <h2>3. Bot FreeGameDrop</h2><p>Le bot Discord est un service séparé du site. Selon le README du dépôt <a href="https://github.com/TOFazer/FreeGameDropDev" target="_blank" rel="noopener noreferrer">FreeGameDropDev</a>, son fonctionnement peut enregistrer dans SQLite des identifiants de serveurs, salons et rôles, des informations d'offres publiques, des favoris associés à un identifiant Discord, des préférences et réglages d'alertes, ainsi qu'un historique minimal d'alertes. Le dépôt indique que le bot ne stocke pas le contenu des messages ni la preuve qu'un jeu a été réclamé.</p><p>Le README précise que les offres publiques non favorites sont retirées du catalogue après 90 jours sans nouvelle observation ; les favoris restent jusqu'à leur retrait ou à la suppression des données. Les autres durées doivent être confirmées par l'exploitant. Les paramètres d'une éventuelle connexion web décrits dans le dépôt ne sont pas activés par ce site.</p>
      <h2>4. Suppression et droits</h2><p>Le dépôt documente la commande <code>/mes-donnees</code> pour demander la suppression des favoris associés au compte. Sa documentation précise que cette commande ne supprime pas les réglages du serveur ni toutes les préférences et alertes personnelles. La procédure complète de contact et d'exercice des droits doit être confirmée par le responsable du traitement.</p><p>Contact pour les demandes relatives aux données : <strong>[À COMPLÉTER : adresse de contact du responsable]</strong>.</p>
      <h2>5. Services tiers</h2><p>Les liens vers Discord et GitHub conduisent vers des services externes soumis à leurs propres conditions et politiques de confidentialité. Le site ne contrôle pas leurs traitements.</p>
      <h2>6. Mise à jour</h2><p>Cette politique devra être complétée et mise à jour si un compte Discord, des statistiques, une API, des formulaires, des cookies ou un dashboard sont ajoutés. Dernière révision du brouillon : 7 octobre 2026.</p>
    </article>
  </section>
</main>
"""

PAGES.append({
    "path": "privacy/index.html",
    "title": "Politique de confidentialité — OverX",
    "description": "Politique de confidentialité provisoire du site OverX et informations documentées sur les données utilisées par FreeGameDrop.",
    "active": "legal",
    "body": _PRIVACY_BODY,
})

_TERMS_BODY = r"""
<main id="main-content">
  <section class="page-hero container legal-hero" data-reveal>
    <p class="eyebrow">INFORMATIONS LÉGALES <span class="crumb-slash">/</span> CONDITIONS</p>
    <h1>Des règles simples.<br><span>À finaliser avant lancement.</span></h1>
    <p class="hero-lead narrow">Projet de conditions pour le site OverX et les liens vers ses bots Discord.</p>
  </section>
  <section class="section container legal-layout" data-reveal>
    <div class="draft-warning"><span aria-hidden="true">!</span><div><strong>Document de travail</strong><p>Le nom et les coordonnées de l'éditeur, les modalités de support et le droit applicable doivent être validés avant publication. Ceci n'est pas un avis juridique.</p></div></div>
    <article class="legal-content">
      <p class="legal-updated">État : version de travail · 7 octobre 2026</p>
      <h2>1. Éditeur et champ d'application</h2><p>Le site OverX est édité par <strong>[À COMPLÉTER : identité légale et coordonnées]</strong>. Les présentes conditions sont un brouillon couvrant la consultation des pages et les liens vers les applications Discord.</p>
      <h2>2. Site et disponibilité</h2><p>Le site fournit des informations sur les projets OverX. Il est actuellement statique et ne fournit ni compte utilisateur, ni dashboard, ni API de configuration. Le statut des bots n'est pas vérifié en temps réel depuis ces pages ; aucune disponibilité permanente n'est promise.</p>
      <h2>3. Utilisation du bot</h2><p>FreeGameDrop est une application distincte opérant sur Discord. Son utilisation dépend des règles de Discord, des permissions accordées au bot et de la disponibilité des sources d'offres. Les utilisateurs et administrateurs doivent respecter les règles de leur serveur et celles de Discord.</p>
      <h2>4. Informations et services tiers</h2><p>Les offres de jeux proviennent de sources tierces et peuvent évoluer. Les liens vers Discord, GitHub, les boutiques et les fournisseurs de données sont soumis aux conditions de ces services. Les informations du site ne garantissent pas qu'une offre soit encore disponible au moment où elle est consultée.</p>
      <h2>5. Propriété intellectuelle</h2><p>Les droits sur les éléments du site et des bots appartiennent à leurs titulaires respectifs. La licence et les modalités de réutilisation du code sont indiquées dans le dépôt du projet lorsqu'elles sont applicables.</p>
      <h2>6. Contact et modifications</h2><p>Contact de l'éditeur : <strong>[À COMPLÉTER : adresse de contact]</strong>. Ces conditions devront être complétées et révisées avant l'ouverture publique du service. Le droit applicable et la juridiction compétente restent à valider par l'éditeur.</p>
    </article>
  </section>
</main>
"""

PAGES.append({
    "path": "terms/index.html",
    "title": "Conditions d'utilisation — OverX",
    "description": "Conditions d'utilisation provisoires du site OverX et des informations relatives à FreeGameDrop.",
    "active": "legal",
    "body": _TERMS_BODY,
})

_LEGAL_BODY = r"""
<main id="main-content">
  <section class="page-hero container legal-hero" data-reveal>
    <p class="eyebrow">INFORMATIONS LÉGALES <span class="crumb-slash">/</span> MENTIONS LÉGALES</p>
    <h1>Qui édite ce site ?<br><span>Informations à renseigner.</span></h1>
    <p class="hero-lead narrow">Les coordonnées légales n'ont pas été fournies. Cette page est volontairement marquée comme incomplète afin de ne pas inventer l'identité de l'éditeur.</p>
  </section>
  <section class="section container legal-layout" data-reveal>
    <div class="draft-warning"><span aria-hidden="true">!</span><div><strong>À compléter avant la mise en ligne publique</strong><p>Renseigne l'identité de l'éditeur et les informations de l'hébergeur avec des données exactes. Fais vérifier les obligations applicables à ton statut.</p></div></div>
    <article class="legal-content">
      <h2>Éditeur du site</h2><ul class="legal-fields"><li><strong>Nom / raison sociale</strong><span>[À COMPLÉTER]</span></li><li><strong>Forme juridique</strong><span>[À COMPLÉTER, le cas échéant]</span></li><li><strong>Adresse</strong><span>[À COMPLÉTER]</span></li><li><strong>Adresse e-mail ou contact</strong><span>[À COMPLÉTER]</span></li><li><strong>Numéro d'immatriculation</strong><span>[À COMPLÉTER si applicable]</span></li><li><strong>Directeur de publication</strong><span>[À COMPLÉTER]</span></li></ul>
      <h2>Hébergement</h2><ul class="legal-fields"><li><strong>Nom de l'hébergeur</strong><span>[À COMPLÉTER après choix du déploiement]</span></li><li><strong>Adresse et contact de l'hébergeur</strong><span>[À COMPLÉTER]</span></li></ul>
      <h2>Propriété intellectuelle</h2><p>Les informations de licence et de réutilisation du code du bot sont à consulter dans le dépôt <a href="https://github.com/TOFazer/FreeGameDropDev" target="_blank" rel="noopener noreferrer">FreeGameDropDev</a>. Les marques, logos et contenus tiers restent la propriété de leurs titulaires.</p>
      <h2>Contact</h2><p>Pour une demande relative au site : <strong>[À COMPLÉTER : moyen de contact vérifié]</strong>.</p>
    </article>
  </section>
</main>
"""

PAGES.append({
    "path": "legal/index.html",
    "title": "Mentions légales — OverX",
    "description": "Mentions légales provisoires du site OverX. Les informations de l'éditeur et de l'hébergeur restent à renseigner.",
    "active": "legal",
    "body": _LEGAL_BODY,
})

NAV_ITEMS = [
    ("Accueil", "index.html", "home"),
    ("OverLoad", "overload/index.html", "overload"),
    ("Bots Discord", "discord-bots/index.html", "bots"),
    ("Documentation", "docs/index.html", "docs"),
    ("Statut", "status/index.html", "status"),
]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def expand_body(page: dict) -> str:
    body = page["body"]
    replacements = {
        "{{OVERLOAD_SOURCE_URL}}": escape(OVERLOAD["source_url"], quote=True),
        "{{OVERLOAD_DOWNLOADS_HOME}}": overload_downloads(show_details=True),
        "{{OVERLOAD_DOWNLOADS}}": overload_downloads(),
        "{{OVERLOAD_ART}}": overload_art(),
        "{{OVERLOAD_SHOWCASE_SECTION}}": overload_showcase_section(),
        "{{FGD_ART}}": fgd_art(),
        "{{STATS_BAND}}": stats_band(),
        "{{WHY_OVERX}}": why_overx(),
        "{{PLATFORM_STRIP}}": platform_strip(),
        "{{COMMUNITY_CTA}}": community_cta(),
        "{{COMMAND_TABLE}}": command_table(FGD_COMMANDS),
        "{{FAQ_BLOCK}}": faq_block(page.get("faqs", FGD_FAQ)),
        "{{OTHER_BOTS}}": other_bots(BOTS[0]["slug"] if BOTS else ""),
    }
    for token, value in replacements.items():
        body = body.replace(token, value)
    return body


def render_nav(root: str, active: str) -> str:
    links = []
    for label, target, key in NAV_ITEMS:
        current = ' aria-current="page"' if key == active else ""
        links.append(f'<a href="{root}{target}"{current}>{label}</a>')
    return "\n        ".join(links)


def render_footer(root: str) -> str:
    platform_links = "\n".join(
        f'<a href="{root}discord-bots/freegamedrop/{p["slug"]}/index.html">Jeux gratuits {p["name"]}</a>'
        for p in FGD_PLATFORMS)
    return f"""
  <footer class="site-footer">
    <div class="container footer-main">
      <div class="footer-brand-block"><a class="brand" href="{root}index.html" aria-label="OverX — accueil"><img src="{root}assets/brand-mark.svg" alt="" width="34" height="34"><span class="brand-word">OVER<span>X</span><small>APPLICATIONS &amp; PROJETS</small></span></a><p>Des applications, des projets et un même univers. OverX réunit les outils d’aujourd’hui et les idées de demain.</p><a class="footer-github" href="https://github.com/TOFazer/OverX" target="_blank" rel="noopener noreferrer">Projet du site sur GitHub <span aria-hidden="true">↗</span></a><a class="footer-github" data-community-cta href="#" hidden>Rejoindre le Discord communautaire <span aria-hidden="true">↗</span></a></div>
      <div class="footer-links"><div><p class="footer-label">EXPLORER</p><a href="{root}index.html#projets">Tous les projets</a><a href="{root}overload/index.html">OverLoad pour Windows</a><a href="{root}discord-bots/index.html">Bots Discord</a><a href="{root}install/index.html">Installer FreeGameDrop</a><a href="{root}docs/index.html">Documentation</a><a href="{root}status/index.html">Statut des services</a><a href="{root}changelog/index.html">Changelog</a></div><div><p class="footer-label">PLATEFORMES</p>{platform_links}<a href="{root}discord-bots/freegamedrop/auto-hebergement/index.html">Auto-hébergement</a></div><div><p class="footer-label">COMMUNAUTÉ</p><a href="{root}support/index.html">Support</a><a href="{root}roadmap/index.html">Roadmap</a><a href="https://github.com/TOFazer/FreeGameDropDev" target="_blank" rel="noopener noreferrer">FreeGameDropDev ↗</a></div><div><p class="footer-label">LÉGAL</p><a href="{root}privacy/index.html">Confidentialité</a><a href="{root}terms/index.html">Conditions</a><a href="{root}legal/index.html">Mentions légales</a></div></div>
    </div>
    <div class="container footer-bottom"><span>© <span data-current-year>2026</span> OverX · Projet indépendant</span><span class="footer-transparency"><span class="footer-dot"></span> Pas de statistiques non vérifiées</span></div>
  </footer>
  <div class="sr-only" role="status" aria-live="polite" data-site-announcer></div>
"""


def page_ld(page: dict, root: str) -> list[dict]:
    blocks = [breadcrumb_ld(page["path"], root)]
    if page["path"] == "index.html":
        blocks.insert(0, org_ld())
    extra = page.get("ld_extra")
    if callable(extra):
        blocks.extend(extra())
    if page.get("faqs") and page["path"] != "docs/index.html":
        blocks.append(faq_ld(page["faqs"]))
    return blocks


def render_page(page: dict) -> str:
    path = page["path"]
    root = asset_root(path)
    title = escape(page["title"], quote=True)
    description = escape(page["description"], quote=True)
    robots = '<meta name="robots" content="noindex,follow">' if path in NOINDEX else ""
    install_url = configured_install_url()
    install_href = escape(install_url, quote=True) if install_url else f"{root}install/index.html#ajouter"
    install_target = ' target="_blank" rel="noopener noreferrer"' if install_url else ""
    body = expand_body(page).replace("{{ROOT}}", root).strip()
    if install_url:
        body = body.replace(f'data-install-cta href="{root}install/index.html#ajouter"', f'data-install-cta href="{install_href}"{install_target}')
        body = body.replace('>Guide d\'installation <span aria-hidden="true">↗</span></a>', '>Ajouter à Discord <span aria-hidden="true">↗</span></a>')
        body = body.replace('data-discord-install href="#ajouter" aria-disabled="true"', f'data-discord-install href="{install_href}"{install_target}')
        body = body.replace('>Invitation Discord à configurer <span aria-hidden="true">↗</span></a>', '>Ajouter à Discord <span aria-hidden="true">↗</span></a>')
        body = body.replace('class="status-pill status-neutral install-state" data-install-state><span></span> Lien de production à configurer', 'class="status-pill status-current install-state" data-install-state><span></span> Invitation prête')
        body = body.replace("Le lien d'invitation Discord n'a pas encore été communiqué.", "Invitation Discord configurée. Choisis le serveur, puis autorise le bot dans Discord.")
        body = body.replace("Application ID / invitation publique à renseigner dans la configuration du site.", "Le bouton ouvre l'invitation OAuth2 fournie pour l'application de production.")
        body = body.replace("L'invitation publique n'est pas encore renseignée. Le bouton d'installation restera inactif jusque-là.", "Le bouton ouvre l'invitation officielle de production.")
        body = body.replace("Le lien officiel de l'application PROD n'a pas encore été renseigné.", "Invitation officielle configurée. Discord te demandera de choisir un serveur et de vérifier les permissions.")
    nav = render_nav(root, page["active"])
    footer = render_footer(root)
    ld_scripts = "\n  ".join(jsonld_block(block) for block in page_ld(page, root))
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#05060b">
{robots}
  <meta name="description" content="{description}">
{seo_head(page)}
  <title>{title}</title>
  <link rel="icon" type="image/svg+xml" href="{root}assets/brand-mark.svg">
  <link rel="stylesheet" href="{root}assets/css/site.css">
  {ld_scripts}
  <script src="{root}assets/site-config.js" defer></script>
  <script src="{root}assets/js/site.js" defer></script>
</head>
<body>
  <a class="skip-link" href="#main-content">Aller au contenu</a>
  <header class="site-header">
    <div class="container header-inner">
      <a class="brand" href="{root}index.html" aria-label="OverX — accueil"><img src="{root}assets/brand-mark.svg" alt="" width="36" height="36"><span class="brand-word">OVER<span>X</span><small>APPLICATIONS &amp; PROJETS</small></span></a>
      <nav class="site-nav" id="primary-nav" data-site-nav aria-label="Navigation principale">
        {nav}
        <a class="mobile-nav-cta" href="{root}index.html#projets">Nos projets</a>
      </nav>
      <div class="header-actions"><a class="button button-header" href="{root}index.html#projets">Nos projets <span aria-hidden="true">→</span></a><button class="menu-toggle" type="button" aria-label="Ouvrir le menu" aria-expanded="false" aria-controls="primary-nav" data-menu-toggle><span></span><span></span><span></span></button></div>
    </div>
  </header>
{body}
{footer}
</body>
</html>
"""


def write_sitemap() -> None:
    base = site_url()
    today = date.today().isoformat()
    urls = [page["path"] for page in PAGES if page["path"] not in NOINDEX]
    if base:
        entries = "\n".join(
            f"  <url><loc>{escape(f'{base}/{PurePosixPath(path)}', quote=True)}</loc><lastmod>{today}</lastmod></url>"
            for path in urls)
        (ROOT / "sitemap.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n',
            encoding="utf-8")
        print("generated sitemap.xml")
    robots_lines = ["User-agent: *", "Allow: /"]
    if base:
        robots_lines.append(f"Sitemap: {base}/sitemap.xml")
    else:
        robots_lines.append("")
        robots_lines.append("# Add the Sitemap directive once the public domain is confirmed in assets/site-config.js (siteUrl).")
    (ROOT / "robots.txt").write_text("\n".join(robots_lines) + "\n", encoding="utf-8")
    print("generated robots.txt")


def main() -> None:
    for page in PAGES:
        destination = ROOT / page["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(render_page(page), encoding="utf-8")
        print(f"generated {destination.relative_to(ROOT)}")
    write_sitemap()
    if not site_url():
        print("note: siteUrl is empty — canonical/og:url/twitter:image and sitemap.xml are skipped until the public domain is set.")


if __name__ == "__main__":
    main()
