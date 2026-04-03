import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from monitor.classifier import is_relevant, classify_severity, extract_tags


def make_entry(title="", summary=""):
    return {"title": title, "summary": summary}


class TestIsRelevant:
    def test_iran_military_is_relevant(self):
        e = make_entry(title="Iran fires ballistic missile toward Israel")
        assert is_relevant(e)

    def test_iran_no_conflict_not_relevant(self):
        e = make_entry(title="Iran celebrates Nowruz", summary="Cultural celebrations in Tehran")
        assert not is_relevant(e)

    def test_conflict_no_iran_not_relevant(self):
        e = make_entry(title="US conducts airstrike in Syria")
        assert not is_relevant(e)

    def test_irgc_sanctions_relevant(self):
        e = make_entry(title="US imposes new sanctions on IRGC commanders")
        assert is_relevant(e)

    def test_nuclear_deal_relevant(self):
        e = make_entry(title="Iran nuclear talks collapse as uranium enrichment accelerates")
        assert is_relevant(e)

    def test_hezbollah_iran_relevant(self):
        e = make_entry(
            title="Iran-backed Hezbollah launches rockets",
            summary="Iranian proxy forces escalate attacks",
        )
        assert is_relevant(e)


class TestClassifySeverity:
    def test_nuclear_is_critical(self):
        e = make_entry(title="Iran crosses nuclear threshold with 90% uranium enrichment")
        assert classify_severity(e) == "critical"

    def test_airstrike_is_critical(self):
        e = make_entry(title="Israeli airstrike on Iranian military base")
        assert classify_severity(e) == "critical"

    def test_missile_is_high(self):
        e = make_entry(title="Iran test-fires new ballistic missile")
        assert classify_severity(e) == "high"

    def test_sanctions_is_high(self):
        e = make_entry(title="US Treasury imposes sweeping sanctions on Iran")
        assert classify_severity(e) == "high"

    def test_tensions_is_medium(self):
        e = make_entry(title="Rising tension between Iran and Gulf states", summary="Diplomatic warning issued")
        assert classify_severity(e) == "medium"

    def test_low_when_no_keywords(self):
        e = make_entry(title="Iran and Turkey discuss trade routes")
        assert classify_severity(e) == "low"


class TestExtractTags:
    def test_nuclear_tag(self):
        e = make_entry(title="Iran uranium enrichment at Natanz facility")
        tags = extract_tags(e)
        assert "nuclear" in tags

    def test_multiple_tags(self):
        e = make_entry(
            title="IRGC drone attack on US military base",
            summary="Pentagon responds with sanctions threat",
        )
        tags = extract_tags(e)
        assert "drone" in tags
        assert "irgc" in tags
        assert "us" in tags

    def test_proxy_tag(self):
        e = make_entry(title="Houthi forces fire at Red Sea shipping")
        tags = extract_tags(e)
        assert "proxy" in tags
