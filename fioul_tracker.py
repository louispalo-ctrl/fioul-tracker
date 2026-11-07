#!/usr/bin/env python3
"""
Fioul tracker - houdt de prijs van fioul de qualité supérieure (Fioulmarket.fr) bij.
Voegt bij elke run één regel toe aan fioul_prijzen.csv.

Installatie:  pip install requests beautifulsoup4
Test:         python fioul_tracker.py --debug
Plannen:      zie onderaan (cron of Windows Taakplanner), 4x per dag.

LET OP: Fioulmarket toont de prijs mogelijk afhankelijk van postcode en
volume. Pas URL, POSTCODE en LITERS hieronder aan en controleer met --debug
of de juiste prijs wordt gevonden.
"""
import argparse, csv, re, sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.fioulmarket.fr/"          # <- vervang door de exacte prijspagina
POSTCODE = "75001"                            # <- jouw postcode (indien nodig)
LITERS = 1000
KEYWORDS = r"(qualit[ée]\s+sup[ée]rieure|fioul\s+premier|premier)"
CSV_FILE = Path(__file__).with_name("fioul_prijzen.csv")
HEADERS = {"User-Agent": "Mozilla/5.0 (fioul-tracker; persoonlijk gebruik)"}

# Prijzen als "1 098,50 €", "1098 €" of "1,133 €"
PRICE_RE = re.compile(r"(\d{1,2}[\s\u202f\u00a0]?\d{3}(?:[.,]\d{1,2})?|\d[.,]\d{2,3})\s*€")


def to_float(s: str) -> float:
    s = re.sub(r"[\s\u202f\u00a0]", "", s).replace(",", ".")
    return float(s)


def find_price(text: str):
    """Zoek het eerste bedrag kort na een 'qualité supérieure'-vermelding."""
    for m in re.finditer(KEYWORDS, text, flags=re.I):
        window = text[m.end(): m.end() + 250]
        p = PRICE_RE.search(window)
        if p:
            return to_float(p.group(1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true", help="bewaar HTML en toon resultaat")
    args = ap.parse_args()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    price, status = None, "ok"
    try:
        r = requests.get(URL, headers=HEADERS, timeout=30, params={"zipcode": POSTCODE})
        r.raise_for_status()
        if args.debug:
            Path("debug_page.html").write_text(r.text, encoding="utf-8")
        text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
        price = find_price(text)
        if price is None:
            status = "prijs_niet_gevonden"
    except Exception as e:
        status = f"fout: {e.__class__.__name__}"

    # Per 1000 L of per liter normaliseren naar euro per 1000 liter
    per_1000 = None
    if price is not None:
        per_1000 = round(price * 1000, 2) if price < 10 else round(price, 2)

    new = not CSV_FILE.exists()
    with CSV_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        if new:
            w.writerow(["tijdstip", "product", "postcode", "liters",
                        "prijs_per_1000L_eur", "status"])
        w.writerow([now, "fioul qualité supérieure", POSTCODE, LITERS,
                    str(per_1000).replace(".", ",") if per_1000 else "", status])

    print(now, per_1000, status)
    sys.exit(0 if status == "ok" else 1)


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# 4x PER DAG PLANNEN (07:00, 12:00, 17:00, 22:00)
#
# Mac/Linux - voer `crontab -e` uit en voeg toe:
#   0 7,12,17,22 * * * /usr/bin/python3 /pad/naar/fioul_tracker.py
#
# Windows - Taakplanner > Taak maken > 4 triggers (dagelijks) > Actie:
#   Programma: python   Argumenten: C:\pad\naar\fioul_tracker.py
#
# Zonder eigen computer: gratis via GitHub Actions (schedule: cron
# "0 6,11,16,21 * * *") dat het CSV-bestand in je repo bijwerkt.
# ---------------------------------------------------------------------------
