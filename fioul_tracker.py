#!/usr/bin/env python3
"""
Fioul tracker - landelijke gemiddelde prijs van Fioulmarket.fr.
Voegt bij elke run één regel toe aan fioul_prijzen.csv.

Bron: https://www.fioulmarket.fr/prix-fioul (prijs per 1000 liter, landelijk
gemiddelde, door Fioulmarket meerdere keren per dag bijgewerkt).
Het script probeert ook de prijs van "qualité supérieure" te vinden; staat die
niet op de pagina, dan blijft die kolom leeg.

Installatie:  pip install requests beautifulsoup4
Test:         python fioul_tracker.py --debug
"""
import argparse, csv, re, sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.fioulmarket.fr/prix-fioul"
CSV_FILE = Path(__file__).with_name("fioul_prijzen.csv")
HEADER = ["tijdstip", "bron", "prijs_gewoon_per_1000L_eur",
          "prijs_superieur_per_1000L_eur", "status"]
HEADERS = {"User-Agent": "Mozilla/5.0 (fioul-tracker; persoonlijk gebruik)"}

NUM = r"(\d{1,2}[\s\u202f\u00a0]?\d{3}|\d{3,4})"          # 1584 of 1 584
ORD_RE = re.compile(r"Prix moyen en France aujourd.hui\s*" + NUM + r"\s*€", re.I)
ORD_FALLBACK = re.compile(NUM + r"\s*€\s*/\s*1000\s*L", re.I)
SUP_RE = re.compile(r"(qualit[ée]\s+sup[ée]rieure|fioul\s+premier)[^\d]{0,200}?" + NUM + r"\s*€", re.I)


def to_int(s: str) -> int:
    return int(re.sub(r"[\s\u202f\u00a0]", "", s))


def parse(text: str):
    """Geef (gewoon, superieur) terug; None als niet gevonden."""
    m = ORD_RE.search(text) or ORD_FALLBACK.search(text)
    ordinary = to_int(m.group(1)) if m else None
    s = SUP_RE.search(text)
    superior = to_int(s.group(2)) if s else None
    ok = lambda v: v is not None and 500 <= v <= 4000   # plausibele bandbreedte
    return (ordinary if ok(ordinary) else None,
            superior if ok(superior) else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ordinary = superior = None
    status = "ok"
    try:
        r = requests.get(URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        if args.debug:
            Path("debug_page.html").write_text(r.text, encoding="utf-8")
        text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
        ordinary, superior = parse(text)
        if ordinary is None and superior is None:
            status = "prijs_niet_gevonden"
        elif superior is None:
            status = "alleen_gewoon_gevonden"
    except Exception as e:
        status = f"fout: {e.__class__.__name__}"

    # Begin opnieuw als het bestand een ouder kolomformaat heeft
    if CSV_FILE.exists():
        first = CSV_FILE.read_text(encoding="utf-8").splitlines()[:1]
        if not first or first[0].split(";") != HEADER:
            CSV_FILE.unlink()

    new = not CSV_FILE.exists()
    with CSV_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        if new:
            w.writerow(HEADER)
        w.writerow([now, URL,
                    ordinary if ordinary else "",
                    superior if superior else "",
                    status])

    print(now, "gewoon:", ordinary, "superieur:", superior, status)
    sys.exit(0 if status in ("ok", "alleen_gewoon_gevonden") else 1)


if __name__ == "__main__":
    main()
