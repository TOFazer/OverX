#!/usr/bin/env python3
"""Small standard-library smoke checker for generated site files and local links."""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PAGES = [
    "index.html",
    "jeux-gratuits/index.html",
    "jeux-gratuits/fiche.html",
    "overload/index.html",
    "discord-bots/index.html",
    "discord-bots/freegamedrop/index.html",
    "discord-bots/freegamedrop/catalogue/index.html",
    "discord-bots/freegamedrop/auto-hebergement/index.html",
    "discord-bots/freegamedrop/steam/index.html",
    "discord-bots/freegamedrop/epic-games/index.html",
    "discord-bots/freegamedrop/gog/index.html",
    "discord-bots/freegamedrop/ubisoft/index.html",
    "install/index.html",
    "docs/index.html",
    "status/index.html",
    "roadmap/index.html",
    "changelog/index.html",
    "support/index.html",
    "privacy/index.html",
    "terms/index.html",
    "legal/index.html",
]


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[tuple[str, str]] = []
        self.title_depth = 0
        self.title_text: list[str] = []
        self.ld_depth = 0
        self.ld_chunks: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(str(values["id"]))
        if tag == "a" and values.get("href") is not None:
            self.links.append((str(values["href"]), "href"))
        if tag in {"script", "img", "source"} and values.get("src"):
            self.links.append((str(values["src"]), "src"))
        if tag == "link" and values.get("href"):
            self.links.append((str(values["href"]), "href"))
        if tag == "title":
            self.title_depth += 1
        if tag == "script" and values.get("type") == "application/ld+json":
            self.ld_depth += 1
            self.ld_chunks.append([])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self.title_depth:
            self.title_depth -= 1
        if tag == "script" and self.ld_depth:
            self.ld_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.title_depth:
            self.title_text.append(data)
        if self.ld_depth:
            self.ld_chunks[-1].append(data)


def main() -> int:
    errors: list[str] = []
    parsed_pages: dict[Path, PageParser] = {}

    for relative in EXPECTED_PAGES:
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"Missing generated page: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(text)
        parsed_pages[path] = parser
        if not " ".join(parser.title_text).strip():
            errors.append(f"Missing <title>: {relative}")
        if re.search(r"\{\{[A-Z_]+\}\}", text):
            errors.append(f"Unexpanded placeholder: {relative}")
        for index, chunks in enumerate(parser.ld_chunks):
            try:
                json.loads("".join(chunks))
            except json.JSONDecodeError as issue:
                errors.append(f"Invalid JSON-LD block {index} in {relative}: {issue}")
        if not parser.ld_chunks:
            errors.append(f"Missing JSON-LD metadata: {relative}")

    for source, parser in parsed_pages.items():
        for raw_url, attribute in parser.links:
            url = urlsplit(raw_url)
            if url.scheme or url.netloc or raw_url.startswith(("mailto:", "tel:", "javascript:")):
                continue
            target = (source.parent / unquote(url.path)).resolve() if url.path else source
            if not target.exists():
                errors.append(f"Broken local {attribute} in {source.relative_to(ROOT)}: {raw_url}")
                continue
            if url.fragment and target.suffix.lower() in {".html", ".htm"} and target in parsed_pages:
                if unquote(url.fragment) not in parsed_pages[target].ids:
                    errors.append(f"Missing fragment in {source.relative_to(ROOT)}: {raw_url}")

    config = ROOT / "assets/site-config.js"
    config_text = config.read_text(encoding="utf-8") if config.exists() else ""
    if "DISCORD_TOKEN=" in config_text or "DISCORD_CLIENT_SECRET=" in config_text:
        errors.append("A Discord secret appears in the public site configuration")

    site_url_match = re.search(r'^\s*siteUrl:\s*"([^"]+)"', config_text, re.MULTILINE)
    sitemap = ROOT / "sitemap.xml"
    if site_url_match:
        if not sitemap.is_file():
            errors.append("siteUrl is set but sitemap.xml is missing (run scripts/build_site.py)")
        else:
            sitemap_text = sitemap.read_text(encoding="utf-8")
            for relative in EXPECTED_PAGES:
                if relative.endswith(("privacy/index.html", "terms/index.html", "legal/index.html")):
                    continue
                if f"/{relative}" not in sitemap_text:
                    errors.append(f"sitemap.xml does not list {relative}")
    elif sitemap.is_file():
        errors.append("sitemap.xml exists although siteUrl is empty (stale file, rebuild)")

    robots = ROOT / "robots.txt"
    if robots.is_file():
        robots_text = robots.read_text(encoding="utf-8")
        if site_url_match and "Sitemap:" not in robots_text:
            errors.append("robots.txt lacks the Sitemap directive although siteUrl is set")

    for image in ("assets/og/overx.png", "assets/og/overload.png", "assets/og/freegamedrop.png"):
        if not (ROOT / image).is_file():
            errors.append(f"Missing share image {image} (run scripts/build_og_images.py with Pillow)")

    for capture in (
        "assets/overload/accueil.png",
        "assets/overload/telechargements.png",
        "assets/overload/createurs.png",
        "assets/overload/historique.png",
        "assets/overload/parametres.png",
        "assets/overload/theme-clair.png",
    ):
        if not (ROOT / capture).is_file():
            errors.append(f"Missing OverLoad application capture {capture}")

    if errors:
        print("Site check failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"Site check passed: {len(parsed_pages)} crawlable pages, local links, fragments, JSON-LD and sitemap verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
