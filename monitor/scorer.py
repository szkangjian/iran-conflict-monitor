"""
Conflict severity scorer.

All scoring is stateless snapshot-based: every call re-computes from the
current event window. No historical score state is carried forward.
"""

import re
import math
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Per-event scoring patterns ───────────────────────────────────────────────
# Each event gets ONE signed score:
#   positive → escalatory,  negative → de-escalatory
# For escalation: take the MAX matching score (worst single signal wins).
# For de-escalation: SUM all matching scores (compounding reassurance).

_ESC = [
    (r"nuclear.{0,60}(attack|strike|weapon|bomb|warhead)",         10.0),
    (r"(declares?\s+war|war\s+declared)",                          10.0),
    (r"ballistic\s+missile.{0,40}(strike|hit|fired|used|launch)",   8.0),
    (r"(airstrike|air\s+strike|bombing\s+raid)",                    7.0),
    (r"(bridge|power\s+plant|refinery|port|dam).{0,30}"
     r"(bombed|destroyed|struck|destroyed)",                        7.0),
    (r"drone.{0,30}(attack|strike|hit)",                            6.0),
    (r"(assassination|targeted\s+killing|assassinated)",            6.0),
    (r"(hezbollah|hamas|houthi).{0,40}(attack|launch|fired|struck)", 5.0),
    (r"sanctions?.{0,30}(escalat|expand|widen|new|impos|sweeping)", 4.0),
    (r"\bblockade\b",                                               4.0),
    (r"(military\s+exercise|troops?\s+deploy|forces?\s+mass)",      3.0),
    (r"\b(warning|ultimatum|threatens?)\b",                         2.0),
    (r"(spy\b|espionage|intelligence\s+operat)",                    1.0),
]

_DEESC = [
    (r"ceasefire.{0,40}(signed|agreed|agreement|deal|reached)",    -6.0),
    (r"peace\s+(deal|agreement|accord|treaty)",                    -6.0),
    (r"(negotiations?|talks?).{0,30}"
     r"(begin|start|resume|underway|launched|open)",               -4.0),
    (r"troops?.{0,30}(withdraw|pull\s*back|redeploy|retreat)",     -3.0),
    (r"\bde.?escalat",                                             -3.0),
    (r"diplomatic.{0,40}(contact|channel|envoy).{0,30}"
     r"(restor|resum|open)",                                       -2.0),
    (r"(unilateral\s+ceasefire|pause\s+in\s+(fighting|hostilities))", -2.0),
    (r"(humanitarian\s+corridor|aid\s+access\s+granted)",          -1.0),
]


def compute_event_score(entry: dict) -> float:
    """Return signed score for one event (+escalatory / -de-escalatory)."""
    text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
    pos = max((v for p, v in _ESC   if re.search(p, text)), default=0.0)
    neg = sum(v for p, v in _DEESC if re.search(p, text))
    return float(pos + neg)


# ── D1: Military intensity (48 h) ───────────────────────────────────────────

def _d1(events: list) -> float:
    if not events:
        return 0.0
    scores     = [float(e.get("event_score") or 0) for e in events]
    pos_scores = [s for s in scores if s > 0]
    peak       = max(pos_scores, default=0.0)
    net_sum    = sum(scores)
    volume     = min(3.0, math.log2(len(pos_scores) + 1))
    return min(10.0, max(0.0, peak * 0.5 + net_sum * 0.3 + volume * 0.5))


# ── D2: Escalation trend (7d vs 7–14d) ──────────────────────────────────────

def _d2(events_this: list, events_prev: list) -> float:
    def daily_avg(evs):
        return sum(float(e.get("event_score") or 0) for e in evs) / 7.0

    this_avg = daily_avg(events_this)
    prev_avg = daily_avg(events_prev)
    delta    = (this_avg - prev_avg) / (abs(prev_avg) + 0.1)

    if   delta >  1.0: return 10.0
    elif delta >  0.5: return  8.0
    elif delta >  0.2: return  6.0
    elif delta >  0.0: return  5.0
    elif delta > -0.2: return  4.0
    elif delta > -0.5: return  3.0
    elif delta > -0.8: return  2.0
    else:              return  0.0


# ── D3: Nuclear / strategic risk (48 h) ─────────────────────────────────────

_D3_POS = [
    (r"enrichment.{0,30}90\s*%",                                    5.0),
    (r"enrichment.{0,30}(8[0-9]|7[0-9]|6[0-9])\s*%",              3.0),
    (r"enrichment.{0,30}(5[0-9]|4[0-9]|3[0-9]|2[0-9])\s*%",       1.0),
    (r"(ballistic\s+missile|hypersonic).{0,30}(test|launch|fire|used)", 3.0),
    (r"(natanz|fordo).{0,40}(attack|struck|bombed|damaged)",        4.0),
    (r"nuclear.{0,40}(threat|weapon|warhead)",                      2.0),
    (r"iaea.{0,40}(block|refus|deny|denied|access\s+denied)",       1.0),
]

_D3_NEG = [
    (r"iaea.{0,40}(access|inspector|return|restor)",               -2.0),
    (r"enrichment.{0,40}(suspend|halt|stop|pause|freez)",          -3.0),
    (r"(jcpoa|nuclear\s+deal).{0,40}(reviv|resum|restart|renew)",  -2.0),
]


def _d3(events: list) -> float:
    combined = " ".join(
        f"{e.get('title','')} {e.get('summary','')}".lower() for e in events
    )
    score = sum(v for p, v in _D3_POS if re.search(p, combined))
    score += sum(v for p, v in _D3_NEG if re.search(p, combined))
    return min(10.0, max(0.0, score))


# ── D4: Geographic / actor spread (7 d) ─────────────────────────────────────

_GEO_GLOBAL  = r"\b(russia|china|europe|european|nato|moscow|beijing)\b"
_GEO_BROADER = r"\b(pakistan|turkey|iraq|baghdad|ankara|islamabad)\b"
_GEO_GULF    = r"\b(saudi|uae|emirates|kuwait|bahrain|qatar|riyadh|abu\s+dhabi)\b"
_PROXIES     = {
    "hezbollah": r"\bhezbollah\b",
    "hamas":     r"\bhamas\b",
    "houthi":    r"\bhouthi\b",
}
_PROXY_CEASEFIRE = (r"\b(hezbollah|hamas|houthi)\b.{0,60}"
                    r"(ceasefire|halt|stop|withdraw|pause)")
_NEUTRAL_MEDIATION = r"\b(mediat|neutral|broker|facilitat).{0,40}(iran|conflict|crisis)\b"


def _d4(events: list) -> float:
    combined = " ".join(
        f"{e.get('title','')} {e.get('summary','')}".lower() for e in events
    )
    # Sub-item A: geographic spread
    if   re.search(_GEO_GLOBAL,  combined): geo = 9
    elif re.search(_GEO_BROADER, combined): geo = 7
    elif re.search(_GEO_GULF,    combined): geo = 5
    else:                                    geo = 3

    # Sub-item B: proxy activity
    proxy_active = sum(1 for r in _PROXIES.values() if re.search(r, combined))

    # Sub-item C: de-escalation — ceasefire per proxy + neutral mediators
    ceasefire_count = len(re.findall(_PROXY_CEASEFIRE, combined))
    neutral_count   = len(re.findall(_NEUTRAL_MEDIATION, combined))
    neg = -(ceasefire_count + neutral_count)

    return min(10.0, max(0.0, geo + proxy_active + neg))


# ── D5: Diplomatic status (7 d) — reverse indicator ─────────────────────────

# Each list: (pattern, score). Lower score = more active diplomacy = less dangerous.
_D5_LOW = [   # good news → low D5
    (r"(talks?|negotiations?).{0,30}(underway|ongoing|continu|progress)", 1.0),
    (r"(summit|meeting).{0,30}(iran|tehran).{0,30}(held|convened)",        2.0),
    (r"(mediati|third.party|broker).{0,30}(active|working|propos)",        2.0),
    (r"(envoy|diplomat|minister).{0,30}(visit|met|travel).{0,30}(iran|tehran)", 3.0),
]
_D5_HIGH = [  # bad news → high D5
    (r"(talks?|negotiations?).{0,30}(collaps|fail|broke|dead)",  6.0),
    (r"diplomatic.{0,30}(sever|cut|broke|suspend)",               7.0),
    (r"(expel|expuls|persona\s+non\s+grata)",                     8.0),
    (r"(war\s+declared|declares?\s+war|state\s+of\s+war)",       10.0),
]


def _d5(events: list) -> float:
    """Return score of the most recent dominant diplomatic signal. Default 5."""
    sorted_evs = sorted(events, key=lambda e: e.get("published", ""), reverse=True)
    for ev in sorted_evs:
        text = f"{ev.get('title','')} {ev.get('summary','')}".lower()
        for pattern, val in _D5_HIGH:
            if re.search(pattern, text):
                return val
        for pattern, val in _D5_LOW:
            if re.search(pattern, text):
                return val
    return 5.0


# ── Final composite score ────────────────────────────────────────────────────

_LEVELS = [
    (80, "核门槛边缘",   "Nuclear Threshold"),
    (60, "全面战争",     "Full-Scale War"),
    (40, "直接军事对抗", "Direct Military Conflict"),
    (20, "代理对抗",     "Proxy Conflict"),
    ( 0, "低度紧张",     "Low Tension"),
]


def _level(score: float) -> tuple[str, str]:
    for threshold, zh, en in _LEVELS:
        if score >= threshold:
            return zh, en
    return _LEVELS[-1][1], _LEVELS[-1][2]


def compute_score() -> dict:
    """Compute and return the current conflict score with full breakdown."""
    from monitor.storage import get_events_in_window

    events_48h   = get_events_in_window(hours=48)
    events_7d    = get_events_in_window(hours=168)
    events_7_14d = get_events_in_window(hours=336, offset_hours=168)

    d1 = _d1(events_48h)
    d2 = _d2(events_7d, events_7_14d)
    d3 = _d3(events_48h)
    d4 = _d4(events_7d)
    d5 = _d5(events_7d)

    raw             = (d1 * 0.30 + d2 * 0.25 + d3 * 0.20 + d4 * 0.15 + d5 * 0.10) * 10
    nuclear_override = d3 >= 7
    final           = round(min(100.0, max(0.0, max(raw, 70.0) if nuclear_override else raw)), 1)

    level_zh, level_en = _level(final)
    result = {
        "score":            final,
        "level_zh":         level_zh,
        "level_en":         level_en,
        "dimensions":       {
            "d1": round(d1, 2),
            "d2": round(d2, 2),
            "d3": round(d3, 2),
            "d4": round(d4, 2),
            "d5": round(d5, 2),
        },
        "nuclear_override": nuclear_override,
        "computed_at":      datetime.now(timezone.utc).isoformat(),
    }
    logger.info(
        "Score: %.1f (%s)  D1=%.1f D2=%.1f D3=%.1f D4=%.1f D5=%.1f%s",
        final, level_zh, d1, d2, d3, d4, d5,
        "  [NUCLEAR OVERRIDE]" if nuclear_override else "",
    )
    return result
