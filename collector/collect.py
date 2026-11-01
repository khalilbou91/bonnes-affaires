#!/usr/bin/env python3
"""Robot de collecte des bonnes affaires.

Lit les flux RSS déclarés dans sources.json, normalise chaque offre,
supprime les doublons, garde l'historique récent et écrit site/data/deals.json.

Aucune dépendance externe : Python 3.9+ suffit.

Usage :
    python collector/collect.py                 # collecte réelle
    python collector/collect.py --fixtures DIR  # test hors ligne (fichiers .xml locaux)
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "collector" / "sources.json"
OUTPUT = ROOT / "site" / "data" / "deals.json"

NS = {
    "media": "http://search.yahoo.com/mrss/",
    "pepper": "http://www.pepper.com/rss",
}
USER_AGENT = "BonnesAffairesBot/1.0 (+site personnel de veille de bons plans)"
PRICE_RE = re.compile(r"(\d{1,3}(?:[ \u00a0.]\d{3})*(?:[.,]\d{1,2})?)\s?(?:€|eur)", re.I)


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


# --------------------------------------------------------------------------- lecture

def fetch(url: str, retries: int = 2) -> bytes | None:
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=25) as resp:
                return resp.read()
        except Exception as exc:  # réseau, 4xx, 5xx…
            log(f"  ! {url} (essai {attempt + 1}) : {exc}")
            time.sleep(2 * (attempt + 1))
    return None


def read_feed(url: str, fixtures: Path | None) -> bytes | None:
    if fixtures:
        f = fixtures / (url.rstrip("/").split("/")[-1] + ".xml")
        return f.read_bytes() if f.exists() else None
    return fetch(url)


# --------------------------------------------------------------------------- normalisation

def parse_price(text: str | None) -> float | None:
    if not text:
        return None
    t = text.strip().lower()
    if t.startswith("gratuit") or t == "free":
        return 0.0
    m = PRICE_RE.search(t + ("€" if "€" not in t and "eur" not in t else ""))
    if not m:
        return None
    raw = m.group(1).replace("\u00a0", "").replace(" ", "")
    # "1.299,99" -> 1299.99 ; "86,74" -> 86.74 ; "1.299" -> 1299
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):
        raw = raw.replace(".", "")
    try:
        return round(float(raw), 2)
    except ValueError:
        return None


def clean_text(text: str | None) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(text: str | None) -> datetime:
    try:
        d = parsedate_to_datetime(text) if text else None
        if d and d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d or datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def parse_items(xml_bytes: bytes, source: str, category: str | None) -> list[dict]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        log(f"  ! XML illisible : {exc}")
        return []
    deals = []
    for item in root.iter("item"):
        link = (item.findtext("link") or "").strip()
        title = clean_text(item.findtext("title"))
        if not link.startswith("http") or not title:
            continue
        merchant_el = item.find("pepper:merchant", NS)
        merchant = merchant_el.get("name") if merchant_el is not None else None
        price = parse_price(merchant_el.get("price")) if merchant_el is not None else None
        if price is None:
            price = parse_price(title)
        img_el = item.find("media:content", NS)
        if img_el is None:
            img_el = item.find("media:thumbnail", NS)
        image = img_el.get("url") if img_el is not None else None
        published = parse_date(item.findtext("pubDate"))
        deals.append({
            "id": hashlib.sha1(link.encode()).hexdigest()[:12],
            "titre": title[:180],
            "prix": price,
            "marchand": merchant,
            "image": image,
            "lien": link,
            "source": source,
            "categorie": category,
            "date": published.astimezone(timezone.utc).isoformat(timespec="seconds"),
            "populaire": False,
        })
    return deals


# --------------------------------------------------------------------------- programme

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", type=Path, help="dossier de flux .xml locaux pour tester hors ligne")
    ap.add_argument("--output", type=Path, default=OUTPUT)
    args = ap.parse_args()

    cfg = json.loads(SOURCES.read_text(encoding="utf-8"))
    categories = set(cfg["categories"])
    by_id: dict[str, dict] = {}

    # 1. Historique : on garde les offres déjà connues (un flux RSS ne montre que les dernières).
    if args.output.exists():
        try:
            for d in json.loads(args.output.read_text(encoding="utf-8")).get("offres", []):
                d["populaire"] = False
                by_id[d["id"]] = d
        except (json.JSONDecodeError, KeyError):
            log("  ! ancien deals.json illisible, on repart de zéro")

    # 2. Flux par catégorie.
    ok_feeds = 0
    for feed in cfg["flux"]:
        if feed["categorie"] not in categories:
            log(f"  ! catégorie inconnue pour {feed['url']} : {feed['categorie']}")
            continue
        log(f"- {feed['source']} / {feed['categorie']} : {feed['url']}")
        data = read_feed(feed["url"], args.fixtures)
        if not data:
            continue
        ok_feeds += 1
        for d in parse_items(data, feed["source"], feed["categorie"]):
            old = by_id.get(d["id"])
            by_id[d["id"]] = {**old, **d} if old else d
        if not args.fixtures:
            time.sleep(1.5)  # politesse envers le site source

    # 3. Flux "populaires" : marquent les offres déjà connues.
    for feed in cfg.get("flux_populaires", []):
        data = read_feed(feed["url"], args.fixtures)
        if not data:
            continue
        for d in parse_items(data, feed["source"], None):
            if d["id"] in by_id:
                by_id[d["id"]]["populaire"] = True

    if ok_feeds == 0 and not by_id:
        log("Aucun flux lu : deals.json n'est pas modifié.")
        return 1

    # 4. Nettoyage : âge maximum, tri du plus récent au plus ancien, plafond.
    limit = datetime.now(timezone.utc) - timedelta(days=cfg.get("max_age_jours", 7))
    deals = [d for d in by_id.values()
             if d.get("categorie") in categories and datetime.fromisoformat(d["date"]) >= limit]
    deals.sort(key=lambda d: d["date"], reverse=True)
    deals = deals[: cfg.get("max_offres", 400)]

    out = {
        "mis_a_jour": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "categories": cfg["categories"],
        "offres": deals,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"OK : {len(deals)} offres écrites dans {args.output} ({ok_feeds} flux lus)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
