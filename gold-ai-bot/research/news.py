"""Opcioni izvor vesti (RSS) bez dodatnih zavisnosti.

Sluzi kao dopunski kontekst AI analitičaru. Ako mreza nije dostupna ili izvor
ne radi, tiho vraca praznu listu - bot tada radi samo sa web_search-om i cenom.
"""
from __future__ import annotations

import logging
import urllib.request
import xml.etree.ElementTree as ET

log = logging.getLogger("news")

# Investing.com commodities RSS (zlato je roba vodjena USD-om, prinosima, Fed-om)
DEFAULT_FEEDS = [
    "https://www.investing.com/rss/commodities_Gold.rss",
]


def fetch_headlines(feeds: list[str] | None = None, limit: int = 10) -> list[str]:
    feeds = feeds or DEFAULT_FEEDS
    headlines: list[str] = []
    for url in feeds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "gold-ai-bot/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                root = ET.fromstring(resp.read())
            for item in root.iter("item"):
                title = item.findtext("title")
                if title:
                    headlines.append(title.strip())
                if len(headlines) >= limit:
                    break
        except Exception as e:  # noqa: BLE001 - vesti su opcione
            log.warning("Ne mogu da povucem vesti sa %s: %s", url, e)
    return headlines[:limit]
