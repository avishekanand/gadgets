"""Headlines from RSS / Atom feeds, grouped into sections for the home-screen carousel.

Returns {"sections": [{"name": "Tech", "items": [{"title", "summary", "source", "url", "published"}]}, ...]}
in the order the sections first appear in the config. Within a section sources take turns (newest
first within each), duplicates (same title) are dropped. A feed that fails is skipped; the section still shows the
others. Feeds are untrusted input: size-capped, parsed with the stdlib (no DTD/entity fetching).
"""
from __future__ import annotations

import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

UA = {"User-Agent": "kindle-dashboard/0.1 (personal e-reader dashboard)"}
MAX_FEED_BYTES = 3 * 1024 * 1024
ATOM = "{http://www.w3.org/2005/Atom}"
RSS1 = "{http://purl.org/rss/1.0/}"
DC = "{http://purl.org/dc/elements/1.1/}"


def _text(el) -> str:
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


SUMMARY_CHARS = 320
_TAGS = re.compile(r"<[^>]+>")


def summarize(raw: str) -> str:
    """Feed description (often escaped HTML) → plain text, cut at a word boundary."""
    text = html.unescape(_TAGS.sub(" ", html.unescape(raw or "")))
    text = " ".join(text.split())
    text = re.sub(r"^arXiv:\S+\s+Announce Type:\s*\S+\s*Abstract:\s*", "", text)  # arXiv RSS preamble
    text = re.sub(r"\s*(The post .* appeared first on .*|Continue reading.*|Read more.*)$", "", text)
    if len(text) <= SUMMARY_CHARS:
        return text
    cut = text[:SUMMARY_CHARS].rsplit(" ", 1)[0].rstrip(",;:—-")
    return cut + "…"


def _raw(el) -> str:
    """Inner text of an element, keeping escaped or embedded markup as text for summarize()."""
    if el is None:
        return ""
    return (el.text or "") + "".join(ET.tostring(c, encoding="unicode") for c in el)


def _when(raw: str) -> datetime | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)  # RSS: "Sat, 21 Nov 2026 20:01:00 +0000"
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))  # Atom: ISO 8601
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_feed(xml_bytes: bytes, source: str) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    out = []
    for item in root.iter("item"):  # RSS 2.0
        out.append({"title": _text(item.find("title")), "url": _text(item.find("link")),
                    "summary": summarize(_raw(item.find("description"))),
                    "when": _when(_text(item.find("pubDate")))})
    for item in root.iter(RSS1 + "item"):  # RSS 1.0 / RDF (e.g. Nature)
        out.append({"title": _text(item.find(RSS1 + "title")), "url": _text(item.find(RSS1 + "link")),
                    "summary": summarize(_raw(item.find(RSS1 + "description"))),
                    "when": _when(_text(item.find(DC + "date")))})
    for entry in root.iter(ATOM + "entry"):  # Atom
        link = entry.find(ATOM + "link[@rel='alternate']")
        if link is None:
            link = entry.find(ATOM + "link")
        out.append({"title": _text(entry.find(ATOM + "title")),
                    "url": link.get("href", "") if link is not None else "",
                    "summary": summarize(_raw(entry.find(ATOM + "summary")) or _raw(entry.find(ATOM + "content"))),
                    "when": _when(_text(entry.find(ATOM + "published")) or _text(entry.find(ATOM + "updated")))})
    for it in out:
        it["source"] = source
    return [it for it in out if it["title"]]


def merge(sections: dict[str, list[dict]], per_section: int, counts: dict[str, int] | None = None) -> dict:
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    result = []
    for name, items in sections.items():
        # newest first within each source, then alternate sources so one busy feed can't crowd out the rest
        by_src: dict[str, list[dict]] = {}
        for it in items:
            by_src.setdefault(it["source"], []).append(it)
        queues = sorted((sorted(v, key=lambda it: it["when"] or epoch, reverse=True) for v in by_src.values()),
                        key=lambda q: q[0]["when"] or epoch, reverse=True)
        items = [q[i] for i in range(max((len(q) for q in queues), default=0)) for q in queues if i < len(q)]
        seen, kept = set(), []
        for it in items:
            key = it["title"].lower()
            if key in seen:
                continue
            seen.add(key)
            kept.append({"title": it["title"], "summary": it.get("summary", ""), "source": it["source"],
                         "url": it["url"] if it["url"].startswith(("https://", "http://")) else "",
                         "published": it["when"].isoformat() if it["when"] else None})
            if len(kept) >= (counts or {}).get(name, per_section):
                break
        if kept:
            result.append({"name": name, "items": kept})
    return {"sections": result}


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
        data = r.read(MAX_FEED_BYTES + 1)
    if len(data) > MAX_FEED_BYTES:
        raise ValueError("feed too large")
    return data


def fetch_news(feeds: list[dict], per_section: int, fetch=_fetch, counts: dict[str, int] | None = None) -> dict:
    sections: dict[str, list[dict]] = {}
    ok = 0
    for f in feeds:
        sections.setdefault(f.get("section", "News"), [])
        try:
            sections[f.get("section", "News")] += parse_feed(fetch(f["url"]), f.get("name", ""))
            ok += 1
        except Exception:  # noqa: BLE001 — one broken feed must not blank the others
            continue
    if feeds and not ok:
        raise RuntimeError("all news feeds failed")
    return merge(sections, per_section, counts)


def fetch_headlines(feeds: list[dict], section: str, count: int, fetch=_fetch) -> list[dict]:
    """Top `count` stories for one section, newest first — for the fridge's
    compact HEADLINES block. Only the feeds in `section` are fetched; if that
    section names no feeds, all feeds are used instead. If every fetched feed
    fails, fetch_news raises RuntimeError (the caller treats that as "no news"
    and drops the block rather than blanking the board)."""
    if count <= 0 or not feeds:
        return []
    sel = [f for f in feeds if f.get("section") == section] or feeds
    data = fetch_news(sel, per_section=count, fetch=fetch)
    secs = data["sections"]
    chosen = next((s for s in secs if s["name"] == section), secs[0] if secs else None)
    return chosen["items"][:count] if chosen else []
