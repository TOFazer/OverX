#!/usr/bin/env python3
"""Fetch the same public offer sources used by FreeGameDrop and publish the site feed.

No credentials are needed. A refresh fails rather than replacing the last good feed
when any source is unavailable, so a temporary outage cannot erase the catalogue.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "offers.json"
GAMERPOWER_URL = "https://www.gamerpower.com/api/giveaways"
EPIC_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
EPIC_STORE = "https://store.epicgames.com"
ACTIVE_STATUSES = {"active", "free", "available"}


def get_json(url: str, params: dict[str, str] | None = None):
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "OverX-FreeGameDrop-Catalogue/1.0"})
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def parse_date(value: object) -> datetime | None:
    if not value or str(value).strip().casefold() in {"n/a", "never", "unknown"}:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def platform_key(value: object) -> str:
    text = str(value or "").casefold()
    for key, patterns in {
        "steam": ("steam",),
        "epic": ("epic",),
        "gog": ("gog",),
        "ubisoft": ("ubisoft",),
    }.items():
        if any(pattern in text for pattern in patterns):
            return key
    return "other"


def valid_http_url(value: object) -> str:
    text = str(value or "").strip()
    return text if text.startswith("https://") else ""


def normalise_gamerpower(item: dict, category: str, now: datetime) -> dict | None:
    if not isinstance(item, dict) or item.get("free_verified") is False:
        return None
    status = str(item.get("status") or "").strip().casefold()
    if status and status not in ACTIVE_STATUSES:
        return None
    end = parse_date(item.get("end_date"))
    if end and end <= now:
        return None
    title = str(item.get("title") or "").strip()
    item_id = str(item.get("id") or "").strip()
    # Do not publish an offer with no usable claim destination.
    url = valid_http_url(item.get("open_giveaway_url") or item.get("gamerpower_url"))
    if not title or not item_id or not url:
        return None
    raw_type = str(item.get("type") or "").casefold()
    if category == "game":
        offer_type = "game"
    elif any(word in raw_type for word in ("dlc", "expansion", "extension", "add-on", "addon")):
        offer_type = "dlc"
    else:
        offer_type = "pack"
    platform = platform_key(item.get("platforms"))
    image = valid_http_url(item.get("image") or item.get("thumbnail"))
    return {
        "id": f"gamerpower-{item_id}",
        "title": title,
        "description": str(item.get("description") or "").strip(),
        "type": offer_type,
        "type_label": {"game": "Jeu complet", "dlc": "DLC / extension", "pack": "Contenu bonus"}[offer_type],
        "platform": platform,
        "platform_label": {"steam": "Steam", "epic": "Epic Games Store", "gog": "GOG", "ubisoft": "Ubisoft Connect"}.get(platform, str(item.get("platforms") or "Autre plateforme")),
        "store": str(item.get("platforms") or "GamerPower"),
        "url": url,
        "image": image,
        "price_original": str(item.get("worth") or ""),
        "expires_at": end.isoformat().replace("+00:00", "Z") if end else None,
        "availability": "temporary" if end else "unknown",
        "is_permanent": False,
        "source": "GamerPower",
    }


def epic_product_url(element: dict) -> str:
    mappings = element.get("offerMappings")
    if isinstance(mappings, list):
        for mapping in mappings:
            if isinstance(mapping, dict) and mapping.get("pageSlug"):
                slug = str(mapping["pageSlug"]).strip("/").split("/")[0]
                if slug:
                    return f"{EPIC_STORE}/fr/p/{slug}"
    slug = str(element.get("productSlug") or "").strip("/").split("/")[0]
    if not slug:
        catalog = element.get("catalogNs")
        mappings = catalog.get("mappings") if isinstance(catalog, dict) else None
        if isinstance(mappings, list):
            slug = next((str(m.get("pageSlug", "")).strip("/").split("/")[0] for m in mappings if isinstance(m, dict) and m.get("pageSlug")), "")
    return f"{EPIC_STORE}/fr/p/{slug}" if slug else ""


def normalise_epic(element: dict, now: datetime) -> dict | None:
    promotions = element.get("promotions")
    if not isinstance(promotions, dict):
        return None
    offer = None
    for group in promotions.get("promotionalOffers") or []:
        if not isinstance(group, dict):
            continue
        for candidate in group.get("promotionalOffers") or []:
            if isinstance(candidate, dict):
                setting = candidate.get("discountSetting")
                discount = setting.get("discountPercentage") if isinstance(setting, dict) else None
                if discount == 0:
                    offer = candidate
                    break
        if offer:
            break
    if not offer:
        return None
    expires = parse_date(offer.get("endDate"))
    if expires and expires <= now:
        return None
    url = epic_product_url(element)
    title = str(element.get("title") or "").strip()
    if not url or not title:
        return None
    images = element.get("keyImages") or []
    image = ""
    for preferred in ("OfferImageWide", "DieselStoreFrontWide", "Thumbnail"):
        image = next((valid_http_url(row.get("url")) for row in images if isinstance(row, dict) and row.get("type") == preferred and valid_http_url(row.get("url"))), "")
        if image:
            break
    if not image:
        image = next((valid_http_url(row.get("url")) for row in images if isinstance(row, dict) and valid_http_url(row.get("url"))), "")
    price = element.get("price") or {}
    total = price.get("totalPrice") or {}
    fmt = total.get("fmtPrice") or {}
    item_type = str(element.get("offerType") or "").casefold()
    offer_type = "dlc" if item_type in {"dlc", "add_on", "addon", "expansion", "expansion_pack", "pack"} else "game"
    return {
        "id": f"epic-{element.get('id') or url.rsplit('/', 1)[-1]}",
        "title": title,
        "description": str(element.get("description") or "").strip(),
        "type": offer_type,
        "type_label": "DLC / extension" if offer_type == "dlc" else "Jeu complet",
        "platform": "epic",
        "platform_label": "Epic Games Store",
        "store": "Epic Games Store",
        "url": url,
        "image": image,
        "price_original": str(fmt.get("originalPrice") or ""),
        "expires_at": expires.isoformat().replace("+00:00", "Z") if expires else None,
        "availability": "temporary" if expires else "unknown",
        "is_permanent": False,
        "source": "Epic Games Store",
    }


def fetch_gamerpower(kind: str) -> list[dict]:
    payload = get_json(GAMERPOWER_URL, {"type": kind, "sort-by": "date"})
    if not isinstance(payload, list):
        raise ValueError(f"Réponse GamerPower inattendue pour {kind} (liste attendue)")
    now = datetime.now(timezone.utc)
    return [offer for row in payload if (offer := normalise_gamerpower(row, kind, now))]


def fetch_epic() -> list[dict]:
    payload = get_json(EPIC_URL, {"locale": "fr-FR", "country": "FR", "allowCountries": "FR"})
    try:
        elements = payload["data"]["Catalog"]["searchStore"]["elements"]
    except (KeyError, TypeError) as error:
        raise ValueError("Réponse Epic Games Store inattendue") from error
    if not isinstance(elements, list):
        raise ValueError("La liste des offres Epic est invalide")
    now = datetime.now(timezone.utc)
    return [offer for row in elements if isinstance(row, dict) and (offer := normalise_epic(row, now))]


def main() -> int:
    try:
        offers = fetch_gamerpower("game") + fetch_gamerpower("loot") + fetch_epic()
    except (URLError, TimeoutError, ValueError, OSError) as error:
        print(f"Erreur de collecte : {error}", file=sys.stderr)
        return 1
    unique = {offer["id"]: offer for offer in offers}
    ordered = sorted(unique.values(), key=lambda item: (item["expires_at"] is None, item["expires_at"] or "9999", item["title"].casefold()))
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "FreeGameDrop — GamerPower + Epic Games Store",
        "notice": "Offres en cours collectées automatiquement. Chaque lien mène à la page de l'offre ou au produit sur sa boutique officielle.",
        "offers": ordered,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Catalogue actualisé : {len(ordered)} offre(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
