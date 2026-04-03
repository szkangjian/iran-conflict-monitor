import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import datetime, timezone


@pytest.fixture(autouse=True)
def tmp_db(monkeypatch, tmp_path):
    db = str(tmp_path / "test.db")
    monkeypatch.setattr("config.DB_PATH", db)
    import monitor.storage as storage
    monkeypatch.setattr(storage, "DB_PATH", db)
    storage.init_db()
    yield db


def _event(**kwargs):
    base = {
        "guid": "test-guid-1",
        "title": "Test Event",
        "summary": "Summary text",
        "url": "https://example.com/1",
        "source": "Test Source",
        "published": datetime.now(timezone.utc).isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "severity": "high",
        "tags": "nuclear,irgc",
    }
    base.update(kwargs)
    return base


def test_upsert_new_event():
    from monitor.storage import upsert_event
    assert upsert_event(_event()) is True


def test_upsert_duplicate_ignored():
    from monitor.storage import upsert_event
    ev = _event()
    upsert_event(ev)
    assert upsert_event(ev) is False


def test_get_events_returns_inserted():
    from monitor.storage import upsert_event, get_events
    upsert_event(_event())
    events = get_events()
    assert len(events) == 1
    assert events[0]["title"] == "Test Event"


def test_get_events_severity_filter():
    from monitor.storage import upsert_event, get_events
    upsert_event(_event(guid="g1", severity="high"))
    upsert_event(_event(guid="g2", severity="low"))
    high = get_events(severity="high")
    assert len(high) == 1
    assert high[0]["severity"] == "high"


def test_get_stats():
    from monitor.storage import upsert_event, get_stats
    upsert_event(_event(guid="g1", severity="critical"))
    upsert_event(_event(guid="g2", severity="high"))
    stats = get_stats()
    assert stats["total"] == 2
    assert stats["by_severity"].get("critical") == 1


def test_mark_alerted():
    from monitor.storage import upsert_event, get_unalerted_events, mark_alerted
    upsert_event(_event(severity="critical"))
    unalerted = get_unalerted_events()
    assert len(unalerted) == 1
    mark_alerted(unalerted[0]["id"])
    assert get_unalerted_events() == []
