#!/usr/bin/env python3
"""
Marktplaats-monitor template.
Vervang de instellingen hieronder met wat jij wilt zoeken.
Eerste run is stil; daarna alleen berichten bij nieuwe advertenties.

Draai lokaal met `python monitor.py --test` om je filter te controleren.
"""

import json
import os
import re
import sys
import requests

# ── INSTELLINGEN — pas dit aan ────────────────────────────────

# Wat zoek je? Meerdere queries mag, wordt gecombineerd.
ZOEKTERMEN = [
    "VOORBEELD zoekterm 1",
    "VOORBEELD zoekterm 2",
]

# Optioneel: minimum en maximum prijs (in euro's).
# Zet MAX_PRIJS op None voor geen bovengrens.
MIN_PRIJS = 0
MAX_PRIJS = None

# Als één van deze substrings in de tekst staat: overslaan.
# Handig om ruis eruit te filteren (accessoires, verkeerde categorieën, etc.)
EXCLUDE_KEYWORDS = [
    # "voorbeeld",
    # "kapot",
]

# Optioneel: positieve indicatoren die een ⭐ geven in de notificatie.
# Laat de regex leeg (r"") als je hier niks mee wil.
LOG_INDICATOREN = re.compile(r"", re.IGNORECASE)

# Optioneel: filter op lengte/maat in feet (bv. voor surfboards).
# Zet beide op None om deze check over te slaan.
MIN_LENGTE_FT = None   # bv. 9.0
MAX_LENGTE_FT = None   # bv. 9.67

# Emoji + titel voor je pushberichten.
EMOJI = "🔔"
NTFY_TITLE = "Nieuwe advertentie op Marktplaats"
NTFY_TAG = "bell"

# ── EINDE INSTELLINGEN ───────────────────────────────────────

SEEN_FILE = "seen_ids.json"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")

API_URL = "https://www.marktplaats.nl/lrp/api/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}

LENGTE_PATRONEN = [
    re.compile(r"(\d{1,2})['\u2019\u2032]{1,2}\s*(\d{1,2})"),
    re.compile(r"(\d{1,2})\s*(?:ft|feet|voet)\s*(\d{1,2})\b", re.IGNORECASE),
    re.compile(r"(\d{1,2})[.,](\d{1,2})\s*(?:ft|feet|voet)\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,2})\s*(?:ft|feet|voet)\b(?!\s*\d)", re.IGNORECASE),
]


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f)), False
    return set(), True


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(seen), f)


def zoek_marktplaats(query):
    params = {
        "query": query, "limit": 30, "offset": 0,
        "sortBy": "SORT_INDEX", "sortOrder": "DECREASING",
        "viewOptions": "list-view",
    }
    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json().get("listings", [])


def extract_lengtes(tekst):
    gevonden = []
    for pat in LENGTE_PATRONEN:
        for m in pat.finditer(tekst):
            try:
                voet = int(m.group(1))
                inch = int(m.group(2)) if len(m.groups()) > 1 and m.group(2) else 0
            except (ValueError, IndexError):
                continue
            if 6 <= voet <= 11 and 0 <= inch <= 11:
                gevonden.append(voet + inch / 12)
    return gevonden


def is_relevant(listing):
    tekst = (listing.get("title", "") + " " +
             listing.get("description", "")).lower()

    if any(kw in tekst for kw in EXCLUDE_KEYWORDS):
        return False

    if MIN_LENGTE_FT is not None and MAX_LENGTE_FT is not None:
        lengtes = extract_lengtes(tekst)
        if lengtes and not any(MIN_LENGTE_FT <= l <= MAX_LENGTE_FT for l in lengtes):
            return False

    prijs_info = listing.get("priceInfo", {})
    prijs_cent = prijs_info.get("priceCents", 0)
    if prijs_info.get("priceType") == "FIXED" and prijs_cent:
        prijs = prijs_cent / 100
        if prijs < MIN_PRIJS:
            return False
        if MAX_PRIJS and prijs > MAX_PRIJS:
            return False

    return True


def formatteer(listing):
    titel = listing.get("title", "Onbekend")
    prijs_cent = listing.get("priceInfo", {}).get("priceCents", 0)
    prijs = f"€{prijs_cent / 100:.0f}" if prijs_cent else "Bieden"
    locatie = listing.get("location", {}).get("cityName", "?")
    url = "https://www.marktplaats.nl" + listing.get("vipUrl", "")

    tekst = (titel + " " + listing.get("description", "")).lower()
    ster = "⭐ " if LOG_INDICATOREN.pattern and LOG_INDICATOREN.search(tekst) else ""

    return f"{ster}{EMOJI} {titel}\n💶 {prijs} — 📍 {locatie}\n{url}"


def notify(bericht):
    if NTFY_TOPIC:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=bericht.encode("utf-8"),
            headers={"Title": NTFY_TITLE, "Tags": NTFY_TAG},
            timeout=10,
        )
    else:
        print(bericht)


def main():
    seen, eerste_run = load_seen()
    nieuw = []

    for query in ZOEKTERMEN:
        try:
            for listing in zoek_marktplaats(query):
                lid = listing.get("itemId")
                if not lid or lid in seen:
                    continue
                seen.add(lid)
                if is_relevant(listing):
                    nieuw.append(listing)
        except requests.RequestException as e:
            print(f"Fout bij query '{query}': {e}")

    if eerste_run:
        print(f"Eerste run: {len(seen)} advertenties gemarkeerd als gezien.")
    else:
        for listing in nieuw:
            notify(formatteer(listing))
        print(f"Klaar. {len(nieuw)} nieuwe relevante advertentie(s).")

    save_seen(seen)


def test_mode():
    """Print alle huidige zoekresultaten met filter-diagnose (geen pushes)."""
    print(f"=== Testmode: {len(ZOEKTERMEN)} zoekterm(en) ===\n")
    for query in ZOEKTERMEN:
        print(f"── Zoekterm: {query} ──")
        try:
            listings = zoek_marktplaats(query)
        except requests.RequestException as e:
            print(f"  Fout: {e}\n")
            continue
        pass_count = 0
        for listing in listings:
            titel = listing.get("title", "?")
            tekst = (titel + " " + listing.get("description", "")).lower()
            hits = [kw for kw in EXCLUDE_KEYWORDS if kw in tekst]
            if hits:
                print(f"  ❌ {titel[:60]} — exclude: {hits}")
                continue
            if is_relevant(listing):
                print(f"  ✅ {titel[:60]}")
                pass_count += 1
            else:
                print(f"  ❌ {titel[:60]} — lengte/prijs")
        print(f"  → {pass_count}/{len(listings)} door filter\n")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_mode()
    else:
        main()
