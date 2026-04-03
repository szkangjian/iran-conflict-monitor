import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from monitor.scorer import (
    compute_event_score,
    _d1, _d2, _d3, _d4, _d5,
    compute_score,
)


def ev(title="", summary="", score=None):
    return {"title": title, "summary": summary, "event_score": score}


# ── compute_event_score ──────────────────────────────────────────────────────

class TestEventScore:
    def test_airstrike_positive(self):
        assert compute_event_score(ev("Israel conducts airstrike on Iran")) > 0

    def test_ceasefire_negative(self):
        assert compute_event_score(ev("Ceasefire agreement signed between parties")) < 0

    def test_negotiation_negative(self):
        assert compute_event_score(ev("Iran nuclear talks begin in Geneva")) < 0

    def test_nuclear_attack_max(self):
        s = compute_event_score(ev("Nuclear weapon attack feared as war declared"))
        assert s == 10.0

    def test_ballistic_missile_high(self):
        s = compute_event_score(ev("Iran fires ballistic missile, missile launched toward Israel"))
        assert s >= 8.0

    def test_diplomatic_contact_negative(self):
        s = compute_event_score(ev("", "diplomatic channel between Iran and US restored after months"))
        assert s < 0

    def test_neutral_event_zero(self):
        s = compute_event_score(ev("Iran holds cultural festival in Tehran"))
        assert s == 0.0

    def test_mixed_signal_reduced(self):
        # "talks collapsed" — negotiations started (-4) but collapsed (net ≈ +6 from high D5)
        # At event level: neg from "talks" pattern + pos from nothing → net negative still
        s = compute_event_score(ev("Iran nuclear talks begin but then collapsed"))
        # "begin" → -4; no clear escalation pattern → pos=0; net = -4
        assert s <= 0


# ── D1 ───────────────────────────────────────────────────────────────────────

class TestD1:
    def test_empty_returns_zero(self):
        assert _d1([]) == 0.0

    def test_single_high_event(self):
        events = [ev(score=8.0), ev(score=2.0)]
        assert _d1(events) > 0

    def test_negative_events_reduce_score(self):
        pos_only = [ev(score=5.0), ev(score=5.0)]
        mixed    = [ev(score=5.0), ev(score=5.0), ev(score=-6.0)]
        assert _d1(mixed) < _d1(pos_only)

    def test_all_negative_events_zero(self):
        events = [ev(score=-4.0), ev(score=-3.0)]
        assert _d1(events) == 0.0

    def test_score_capped_at_ten(self):
        events = [ev(score=10.0)] * 20
        assert _d1(events) <= 10.0


# ── D2 ───────────────────────────────────────────────────────────────────────

class TestD2:
    def test_escalating_trend(self):
        this = [ev(score=7.0)] * 5
        prev = [ev(score=2.0)] * 5
        assert _d2(this, prev) >= 8.0

    def test_de_escalating_trend(self):
        this = [ev(score=1.0)] * 5
        prev = [ev(score=7.0)] * 5
        assert _d2(this, prev) <= 3.0

    def test_stable_trend(self):
        events = [ev(score=4.0)] * 5
        score = _d2(events, events)
        assert 3.5 <= score <= 5.0

    def test_no_prev_events(self):
        this = [ev(score=5.0)] * 3
        score = _d2(this, [])
        assert 0 <= score <= 10


# ── D3 ───────────────────────────────────────────────────────────────────────

class TestD3:
    def test_nuclear_threat_scores(self):
        events = [ev("Iran nuclear weapon threat issued by officials")]
        assert _d3(events) > 0

    def test_natanz_attack_high(self):
        events = [ev("Natanz facility bombed and damaged in overnight strike")]
        assert _d3(events) >= 4.0

    def test_enrichment_suspension_negative(self):
        events = [ev("Iran announces enrichment suspended under IAEA supervision")]
        assert _d3(events) < 0 or _d3(events) == 0  # net zero or negative

    def test_iaea_access_restored_reduces(self):
        baseline = [ev("Iran nuclear weapon threat")]
        with_deesc = [ev("Iran nuclear weapon threat"),
                      ev("IAEA inspectors return and access restored")]
        assert _d3(with_deesc) < _d3(baseline) + 0.1

    def test_empty_zero(self):
        assert _d3([]) == 0.0

    def test_capped_at_ten(self):
        events = [ev("Nuclear weapon attack, natanz bombed, IAEA access denied, "
                     "ballistic missile launched, enrichment 90%, nuclear threat")] * 5
        assert _d3(events) <= 10.0


# ── D4 ───────────────────────────────────────────────────────────────────────

class TestD4:
    def test_global_actors_high(self):
        events = [ev("Russia and China respond as NATO weighs in on Iran conflict")]
        assert _d4(events) >= 9

    def test_gulf_only_medium(self):
        events = [ev("Saudi Arabia and UAE close airspace over Iran tensions")]
        score = _d4(events)
        assert 4 <= score <= 8

    def test_three_proxies_adds_score(self):
        events = [ev("Hezbollah, Hamas and Houthi all launch coordinated attacks")]
        score = _d4(events)
        assert score >= 6

    def test_proxy_ceasefire_reduces(self):
        base = [ev("Hezbollah Hamas Houthi active, Saudi Arabia involved")]
        with_cf = base + [ev("Hezbollah ceasefire announced, Hamas ceasefire pause")]
        assert _d4(with_cf) < _d4(base)

    def test_empty_returns_base(self):
        assert _d4([]) == 3.0  # just the Iran+Israel+US baseline


# ── D5 ───────────────────────────────────────────────────────────────────────

class TestD5:
    def test_default_neutral(self):
        assert _d5([]) == 5.0

    def test_active_talks_low(self):
        events = [ev("Iran nuclear negotiations underway in Vienna")]
        assert _d5(events) <= 3.0

    def test_expelled_diplomats_high(self):
        events = [ev("Iran expels European diplomats, persona non grata declared")]
        assert _d5(events) >= 8.0

    def test_war_declared_max(self):
        events = [ev("Iran declares war on Israel in formal statement")]
        assert _d5(events) == 10.0

    def test_most_recent_dominates(self):
        events = [
            {"title": "Iran declares war", "summary": "", "event_score": 0,
             "published": "2026-04-03T10:00:00"},
            {"title": "Iran nuclear talks underway in Vienna", "summary": "", "event_score": 0,
             "published": "2026-04-03T12:00:00"},  # more recent
        ]
        # More recent de-escalation should win
        assert _d5(events) <= 3.0


# ── compute_score integration ────────────────────────────────────────────────

class TestComputeScore:
    @pytest.fixture(autouse=True)
    def tmp_db(self, monkeypatch, tmp_path):
        db = str(tmp_path / "test.db")
        monkeypatch.setattr("config.DB_PATH", db)
        import monitor.storage as storage
        monkeypatch.setattr(storage, "DB_PATH", db)
        storage.init_db()

    def test_returns_valid_structure(self):
        result = compute_score()
        assert "score" in result
        assert "dimensions" in result
        assert set(result["dimensions"]) == {"d1", "d2", "d3", "d4", "d5"}
        assert 0 <= result["score"] <= 100

    def test_no_events_gives_low_score(self):
        result = compute_score()
        assert result["score"] < 40  # no data → low tension baseline

    def test_nuclear_override_triggers(self, monkeypatch):
        # Patch _d3 to return 8.0
        import monitor.scorer as scorer
        monkeypatch.setattr(scorer, "_d3", lambda evs: 8.0)
        result = compute_score()
        assert result["nuclear_override"] is True
        assert result["score"] >= 70.0
