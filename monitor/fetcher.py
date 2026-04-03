import hashlib
import logging
import feedparser
import requests
from datetime import datetime, timezone

from config import RSS_FEEDS, NEWS_API_KEY
from monitor.classifier import is_relevant, classify_severity, extract_tags
from monitor.scorer import compute_event_score
from monitor.storage import upsert_event

logger = logging.getLogger(__name__)


def _parse_date(entry) -> str:
    for field in ("published_parsed", "updated_parsed"):
        t = getattr(entry, field, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


def _strip_html(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", text).strip()


def _entry_to_dict(entry, source_name: str) -> dict:
    title   = entry.get("title", "").strip()
    summary = _strip_html(entry.get("summary", entry.get("description", "")).strip())[:1000]
    url     = entry.get("link", "")
    guid    = entry.get("id", entry.get("link", ""))
    if not guid:
        guid = hashlib.md5(f"{title}{url}".encode()).hexdigest()

    return {
        "guid":        guid,
        "title":       title,
        "summary":     summary,
        "url":         url,
        "source":      source_name,
        "published":   _parse_date(entry),
        "fetched_at":  datetime.now(timezone.utc).isoformat(),
        "severity":    "",
        "tags":        "",
        "event_score": None,
    }


def _classify_and_store(entry: dict) -> bool:
    entry["severity"]    = classify_severity(entry)
    entry["tags"]        = ",".join(extract_tags(entry))
    entry["event_score"] = compute_event_score(entry)
    return upsert_event(entry)


def fetch_rss(feed_cfg: dict) -> int:
    name, url = feed_cfg["name"], feed_cfg["url"]
    new_count = 0
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "IranConflictMonitor/1.0"})
        if feed.bozo and not feed.entries:
            logger.warning("Feed parse error for %s: %s", name, feed.bozo_exception)
            return 0
        for raw in feed.entries:
            entry = _entry_to_dict(raw, name)
            if not is_relevant(entry):
                continue
            if _classify_and_store(entry):
                new_count += 1
                logger.info("[%s] New event (%s, score=%.1f): %s",
                            name, entry["severity"], entry["event_score"], entry["title"][:80])
    except Exception as exc:
        logger.error("Error fetching %s: %s", name, exc)
    return new_count


def fetch_newsapi(query: str = "Iran military conflict") -> int:
    if not NEWS_API_KEY:
        return 0
    new_count = 0
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q": query, "language": "en", "sortBy": "publishedAt", "pageSize": 50},
            headers={"X-Api-Key": NEWS_API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        for article in resp.json().get("articles", []):
            entry = {
                "guid":        hashlib.md5(article["url"].encode()).hexdigest(),
                "title":       article.get("title", "").strip(),
                "summary":     (article.get("description") or "")[:1000],
                "url":         article.get("url", ""),
                "source":      article.get("source", {}).get("name", "NewsAPI"),
                "published":   article.get("publishedAt", datetime.now(timezone.utc).isoformat()),
                "fetched_at":  datetime.now(timezone.utc).isoformat(),
                "severity":    "",
                "tags":        "",
                "event_score": None,
            }
            if not is_relevant(entry):
                continue
            if _classify_and_store(entry):
                new_count += 1
    except Exception as exc:
        logger.error("NewsAPI fetch error: %s", exc)
    return new_count


def run_fetch_cycle() -> dict:
    logger.info("Starting fetch cycle …")
    results = {"rss": {}, "newsapi": 0, "total_new": 0}

    for feed in RSS_FEEDS:
        n = fetch_rss(feed)
        results["rss"][feed["name"]] = n
        results["total_new"] += n

    n = fetch_newsapi()
    results["newsapi"] = n
    results["total_new"] += n

    logger.info("Fetch cycle complete. New events: %d", results["total_new"])
    return results
