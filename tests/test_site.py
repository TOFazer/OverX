"""Offline regression tests for the OverX studio site and OverLoad download contract.

Run with: python3 -m unittest discover -s tests -v
No dependency, GitHub token, release number or network access is required.
"""
from __future__ import annotations

import struct
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from scripts import build_site, check_site

ROOT = Path(__file__).resolve().parents[1]
PAGES = {page["path"]: page for page in build_site.PAGES}
DOWNLOADS = {
    "installer": "https://github.com/TOFazer/OverLoad/releases/latest/download/OverLoad-Setup.exe",
    "portable": "https://github.com/TOFazer/OverLoad/releases/latest/download/OverLoad-Portable-win64.zip",
}
OVERLOAD_PAGES = ("index.html", "overload/index.html")
STUDIO_PALETTE = ("#101713", "#1A261F", "#315E43", "#A9C7AE", "#E1E8E1")


class InspectPage(check_site.PageParser):
    def __init__(self, html: str) -> None:
        super().__init__()
        self.anchors: list[dict[str, str | None]] = []
        self.meta: list[dict[str, str | None]] = []
        self.all_ids: list[str] = []
        self.h1_count = 0
        self.feed(html)
        self.close()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        super().handle_starttag(tag, attrs)
        values = dict(attrs)
        if tag == "a":
            self.anchors.append(values)
        if tag == "meta":
            self.meta.append(values)
        if values.get("id"):
            self.all_ids.append(str(values["id"]))
        if tag == "h1":
            self.h1_count += 1

    def downloads(self) -> dict[str, dict[str, str | None]]:
        return {
            str(anchor["data-overload-download"]): anchor
            for anchor in self.anchors if "data-overload-download" in anchor
        }


def render(path: str) -> str:
    return build_site.render_page(PAGES[path])


class OverLoadDownloadTests(unittest.TestCase):
    def test_installer_and_portable_use_exact_permanent_urls(self) -> None:
        for path in OVERLOAD_PAGES:
            with self.subTest(page=path):
                downloads = InspectPage(render(path)).downloads()
                self.assertEqual(set(downloads), set(DOWNLOADS))
                for kind, expected_url in DOWNLOADS.items():
                    self.assertEqual(downloads[kind]["href"], expected_url)

    def test_committed_html_has_real_links_without_javascript(self) -> None:
        for path in OVERLOAD_PAGES:
            with self.subTest(page=path):
                html = (ROOT / path).read_text(encoding="utf-8")
                for kind, anchor in InspectPage(html).downloads().items():
                    self.assertEqual(anchor["href"], DOWNLOADS[kind])
                    self.assertNotEqual(anchor.get("aria-disabled"), "true")
                    self.assertNotIn("onclick", anchor)
                    self.assertNotIn("data-install-cta", anchor)
                    self.assertNotIn("data-discord-install", anchor)

    def test_downloads_do_not_depend_on_discord_configuration(self) -> None:
        discord_url = "https://discord.com/oauth2/authorize?client_id=123456789012345678"
        for install_url in (None, discord_url):
            with patch.object(build_site, "configured_install_url", return_value=install_url):
                for path in OVERLOAD_PAGES:
                    with self.subTest(invite=install_url, page=path):
                        downloads = InspectPage(render(path)).downloads()
                        self.assertEqual({kind: link["href"] for kind, link in downloads.items()}, DOWNLOADS)

    def test_latest_release_notes_remain_accessible(self) -> None:
        for path in OVERLOAD_PAGES:
            with self.subTest(page=path):
                links = InspectPage(render(path)).anchors
                self.assertTrue(any(
                    anchor.get("href") == "https://github.com/TOFazer/OverLoad/releases/latest"
                    for anchor in links
                ))

    def test_installer_has_a_visible_installation_explanation(self) -> None:
        for path in OVERLOAD_PAGES:
            with self.subTest(page=path):
                html = render(path)
                parsed = InspectPage(html)
                note_id = parsed.downloads()["installer"]["aria-describedby"]
                self.assertIn(note_id, parsed.ids)
                self.assertIn("puis lance l'installateur sur ton PC", html)
                self.assertIn("Dernière version stable", html)

    def test_overload_page_has_no_discord_install_action(self) -> None:
        self.assertNotIn("data-install-cta", render("overload/index.html"))
        self.assertNotIn("data-discord-install", render("overload/index.html"))

    def test_overload_visuals_use_real_application_captures(self) -> None:
        home_html = render("index.html")
        overload_html = render("overload/index.html")
        self.assertIn('src="assets/overload/accueil.png"', home_html)
        self.assertIn('src="assets/overload/telechargements.png"', home_html)
        self.assertIn('src="assets/overload/createurs.png"', home_html)
        for screen in build_site.OVERLOAD_SCREENS:
            with self.subTest(screen=screen["id"]):
                self.assertIn(f'src="../{screen["image"]}"', overload_html)
                self.assertTrue((ROOT / screen["image"]).is_file())


class GameCatalogueTests(unittest.TestCase):
    def test_catalogue_cards_open_an_individual_game_or_dlc_page(self) -> None:
        catalog = render("jeux-gratuits/index.html")
        detail = render("jeux-gratuits/fiche.html")
        self.assertIn('data-offers-detail-url="../jeux-gratuits/fiche.html"', catalog)
        self.assertIn('data-offer-detail data-offer-data-url="../data/offers.json"', detail)
        self.assertIn('data-offer-detail-title', detail)
        self.assertIn('data-offer-detail-claim', detail)
        self.assertIn('id=${encodeURIComponent(String(offer.id))}', (ROOT / "assets/js/site.js").read_text(encoding="utf-8"))

    def test_catalogue_has_pagination_for_large_filtered_results(self) -> None:
        html = render("jeux-gratuits/index.html")
        self.assertIn('data-offers-pagination aria-label="Pages du catalogue" hidden', html)
        script = (ROOT / "assets/js/site.js").read_text(encoding="utf-8")
        self.assertIn("const PAGE_SIZE = 24", script)
        self.assertIn("filtered.slice(pageStart, pageStart + PAGE_SIZE)", script)
        self.assertIn('aria-label="Page suivante"', script)

    def test_offer_cards_use_product_links_and_official_or_steam_images(self) -> None:
        script = (ROOT / "assets/js/site.js").read_text(encoding="utf-8")
        self.assertIn('parsed.protocol !== "https:" || parsed.pathname === "/"', script)
        self.assertIn("cdn.akamai.steamstatic.com/steam/apps/${steamMatch[1]}/header.jpg", script)
        self.assertIn("Lien de l'offre indisponible", script)
        self.assertIn('href="${escapeHtml(url)}"', script)
        docs = (ROOT / "data/README.md").read_text(encoding="utf-8")
        self.assertIn("fiche précise du jeu ou du DLC", docs)


class ProjectHubTests(unittest.TestCase):
    def test_home_follows_five_part_studio_architecture(self) -> None:
        home = render("index.html")
        parsed = InspectPage(home)
        self.assertEqual("".join(parsed.title_text), "OverX — Studio logiciel indépendant")
        self.assertTrue({"accueil", "projets", "overload", "bots", "overx", "conclusion"}.issubset(parsed.ids))
        positions = [
            home.index('id="accueil"'),
            home.index('id="overload"'),
            home.index('id="bots"'),
            home.index('id="overx"'),
            home.index('id="conclusion"'),
            home.index('<footer class="site-footer">'),
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('href="overload/index.html"', home)
        self.assertIn('href="discord-bots/freegamedrop/index.html"', home)

    def test_studio_hero_has_concise_copy_two_actions_and_vector_signature(self) -> None:
        home = render("index.html")
        hero = home.split('<section class="studio-hero"', 1)[1].split("</section>", 1)[0]
        actions = InspectPage(hero).anchors
        self.assertEqual([a["href"] for a in actions], ["#projets", "#overx"])
        self.assertIn("pensés pour vous.", hero)
        self.assertIn("Découvrir nos projets", hero)
        self.assertIn("À propos d'OverX", hero)
        self.assertIn('class="studio-emblem-svg"', hero)
        for name in ("brand-mark.svg", "brand-sculpture.svg"):
            ElementTree.parse(ROOT / "assets" / name)

    def test_studio_design_tokens_are_defined_once_and_applied_everywhere(self) -> None:
        self.assertFalse((ROOT / "assets" / "css" / "forest-minimal.css").exists())
        css = (ROOT / "assets" / "css" / "site.css").read_text(encoding="utf-8")
        self.assertEqual(css.count(":root {"), 1)
        for color in STUDIO_PALETTE:
            with self.subTest(color=color):
                self.assertIn(color, css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertNotIn("#F3F1E8", css)
        for path in PAGES:
            with self.subTest(page=path):
                html = render(path)
                root = build_site.asset_root(path)
                self.assertIn(f'href="{root}assets/css/site.css"', html)
                self.assertNotIn("forest-minimal.css", html)
                self.assertIn('content="#101713"', html)

    def test_discord_demo_is_not_presented_as_a_real_offer(self) -> None:
        home = render("index.html")
        self.assertIn("DÉMONSTRATION", home)
        self.assertIn("jeu fictif", home)
        self.assertIn("Ajouter à Discord", home)
        self.assertNotIn("Cyberpunk 2077", home)
        self.assertNotIn('data-stat="guilds"', home)

    def test_home_structured_catalogue_lists_both_projects(self) -> None:
        blocks = build_site.page_ld(PAGES["index.html"], "")
        catalogue = next(block for block in blocks if block["@type"] == "ItemList")
        self.assertEqual([item["name"] for item in catalogue["itemListElement"]], ["OverLoad", "FreeGameDrop"])
        self.assertNotIn("Discord", build_site.org_ld()["slogan"])

    def test_shared_navigation_and_site_repository_use_overx(self) -> None:
        for path in PAGES:
            with self.subTest(page=path):
                html = render(path)
                root = build_site.asset_root(path)
                self.assertIn(f'href="{root}overload/index.html"', html)
                self.assertIn(f'href="{root}index.html#projets"', html)
                self.assertIn('href="https://github.com/TOFazer/OverX"', html)
                self.assertNotIn("OrvexWebsite", html)
                self.assertNotIn("DISCORD TOOLS", html)

    def test_overload_navigation_is_marked_current(self) -> None:
        links = InspectPage(render("overload/index.html")).anchors
        current = [anchor for anchor in links if anchor.get("aria-current") == "page"]
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["href"], "../overload/index.html")

    def test_existing_bot_invite_is_preserved(self) -> None:
        for path in ("index.html", "discord-bots/freegamedrop/index.html"):
            with self.subTest(page=path):
                links = InspectPage(render(path)).anchors
                invites = [anchor for anchor in links if "data-install-cta" in anchor]
                self.assertTrue(invites)
                for anchor in invites:
                    self.assertEqual(anchor["href"], build_site.configured_install_url())
        self.assertEqual(build_site.software_ld(build_site.BOTS[0])["operatingSystem"], "Discord")


class GeneratedSiteTests(unittest.TestCase):
    def test_all_generated_pages_match_the_builder(self) -> None:
        self.assertEqual(set(PAGES), set(check_site.EXPECTED_PAGES))
        for path in PAGES:
            with self.subTest(page=path):
                self.assertEqual((ROOT / path).read_text(encoding="utf-8"), render(path))

    def test_each_page_has_one_h1_and_unique_ids(self) -> None:
        for path in PAGES:
            with self.subTest(page=path):
                parsed = InspectPage(render(path))
                self.assertEqual(parsed.h1_count, 1)
                duplicates = [name for name, count in Counter(parsed.all_ids).items() if count > 1]
                self.assertEqual(duplicates, [])

    def test_overload_software_metadata_uses_windows_and_latest_download(self) -> None:
        blocks = build_site.page_ld(PAGES["overload/index.html"], "../")
        software = next(block for block in blocks if block["@type"] == "SoftwareApplication")
        self.assertEqual(software["name"], "OverLoad")
        self.assertEqual(software["operatingSystem"], "Windows 11 (64 bits)")
        self.assertEqual(software["downloadUrl"], DOWNLOADS["installer"])
        self.assertNotIn("softwareVersion", software)
        breadcrumb = next(block for block in blocks if block["@type"] == "BreadcrumbList")
        self.assertEqual(breadcrumb["itemListElement"][-1]["name"], "OverLoad")

    def test_overload_faq_metadata_matches_its_visible_faq(self) -> None:
        blocks = build_site.page_ld(PAGES["overload/index.html"], "../")
        faq = next(block for block in blocks if block["@type"] == "FAQPage")
        questions = [item["name"] for item in faq["mainEntity"]]
        self.assertEqual(questions, [question for question, _ in build_site.OVERLOAD_FAQ])
        self.assertEqual(render("overload/index.html").count('<details class="faq-item">'), len(questions))

    def test_metadata_supports_project_subpath_deployment(self) -> None:
        with patch.object(build_site, "site_url", return_value="https://example.org/OverX"):
            html = render("overload/index.html")
            self.assertIn('<link rel="canonical" href="https://example.org/OverX/overload/index.html">', html)
            self.assertIn('content="https://example.org/OverX/assets/og/overload.png"', html)
            self.assertEqual(InspectPage(html).downloads()["installer"]["href"], DOWNLOADS["installer"])

    def test_sitemap_includes_overload_and_excludes_legal_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(build_site, "ROOT", root), patch.object(build_site, "site_url", return_value="https://example.org/OverX"):
                build_site.write_sitemap()
            sitemap = ElementTree.fromstring((root / "sitemap.xml").read_text(encoding="utf-8"))
            urls = [node.text for node in sitemap.findall("{*}url/{*}loc")]
            self.assertIn("https://example.org/OverX/overload/index.html", urls)
            self.assertFalse(any(url.endswith(tuple(build_site.NOINDEX)) for url in urls))
            self.assertIn("Sitemap: https://example.org/OverX/sitemap.xml", (root / "robots.txt").read_text(encoding="utf-8"))

    def test_social_cards_are_valid_1200_by_630_pngs(self) -> None:
        for name in ("overx", "overload", "freegamedrop"):
            with self.subTest(image=name):
                header = (ROOT / "assets" / "og" / f"{name}.png").read_bytes()[:24]
                self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(struct.unpack(">II", header[16:24]), (1200, 630))


if __name__ == "__main__":
    unittest.main()
