import re
import logging
from config import (
    IRAN_KEYWORDS,
    CONFLICT_KEYWORDS,
    SEVERITY_CRITICAL_KEYWORDS,
    SEVERITY_HIGH_KEYWORDS,
    SEVERITY_MEDIUM_KEYWORDS,
)

logger = logging.getLogger(__name__)


def _text(entry: dict) -> str:
    return f"{entry.get('title', '')} {entry.get('summary', '')}".lower()


def is_relevant(entry: dict) -> bool:
    text = _text(entry)
    has_iran = any(re.search(r"\b" + re.escape(kw) + r"\b", text) for kw in IRAN_KEYWORDS)
    has_conflict = any(re.search(r"\b" + re.escape(kw) + r"\b", text) for kw in CONFLICT_KEYWORDS)
    return has_iran and has_conflict


def classify_severity(entry: dict) -> str:
    text = _text(entry)
    for kw in SEVERITY_CRITICAL_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", text):
            return "critical"
    for kw in SEVERITY_HIGH_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", text):
            return "high"
    for kw in SEVERITY_MEDIUM_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", text):
            return "medium"
    return "low"


def extract_tags(entry: dict) -> list[str]:
    text = _text(entry)
    tag_groups = {
        "nuclear": ["nuclear", "uranium", "enrichment", "centrifuge", "natanz", "fordo", "jcpoa"],
        "missile": ["missile", "ballistic", "hypersonic", "rocket"],
        "drone": ["drone", "uav", "unmanned"],
        "sanctions": ["sanctions", "embargo"],
        "diplomacy": ["diplomatic", "negotiations", "talks", "deal"],
        "proxy": ["hezbollah", "hamas", "houthi", "proxy"],
        "israel": ["israel", "idf", "mossad"],
        "us": ["pentagon", "us military", "cia", "white house"],
        "irgc": ["irgc", "revolutionary guard", "quds force"],
        "assassination": ["assassination", "killed", "targeted killing"],
    }
    tags = []
    for tag, keywords in tag_groups.items():
        if any(re.search(r"\b" + re.escape(kw) + r"\b", text) for kw in keywords):
            tags.append(tag)
    return tags
