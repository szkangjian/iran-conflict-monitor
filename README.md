# Iran Conflict Monitor

A real-time news monitoring dashboard that tracks conflict-related events involving Iran. Fetches from multiple RSS feeds and optionally NewsAPI, classifies event severity, stores results in SQLite, and serves a dark-mode web dashboard.

## Features

- **Multi-source RSS ingestion** — Reuters, BBC, Al Jazeera, AP, Guardian, Times of Israel, Jerusalem Post
- **NewsAPI support** — optional additional coverage with an API key
- **Automatic relevance filtering** — only events mentioning Iran + conflict keywords pass through
- **Severity classification** — `critical / high / medium / low` based on keyword rules
- **Tag extraction** — nuclear, missile, drone, sanctions, diplomacy, proxy, IRGC, etc.
- **Telegram alerts** — push notifications for high/critical events (optional)
- **Web dashboard** — dark-mode UI with filters, search, live stats, and auto-refresh
- **Background scheduler** — configurable fetch interval via `.env`

## Quick Start

```bash
# 1. Clone and enter the repo
git clone https://github.com/szkangjian/iran-conflict-monitor.git
cd iran-conflict-monitor

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure (optional)
cp .env.example .env
# Edit .env to add NEWS_API_KEY, TELEGRAM_*, etc.

# 5. Run
python main.py
# Dashboard: http://localhost:5000
```

## Usage

```
python main.py              # Full mode: fetch + scheduler + dashboard
python main.py --fetch-once # Single fetch cycle, no dashboard
python main.py --dashboard  # Dashboard only, no scheduler
python main.py --port 8080  # Custom port
```

## Configuration

Copy `.env.example` to `.env` and set:

| Variable | Default | Description |
|---|---|---|
| `NEWS_API_KEY` | — | Optional NewsAPI.org key |
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot token for alerts |
| `TELEGRAM_CHAT_ID` | — | Telegram chat/channel ID |
| `FETCH_INTERVAL_MINUTES` | `15` | How often to fetch news |
| `DASHBOARD_PORT` | `5000` | Web dashboard port |
| `LOG_LEVEL` | `INFO` | `DEBUG / INFO / WARNING / ERROR` |

## Project Structure

```
iran_conflict_monitor/
├── config.py                  # All settings and keyword lists
├── main.py                    # Entry point
├── requirements.txt
├── monitor/
│   ├── fetcher.py             # RSS + NewsAPI ingestion
│   ├── classifier.py          # Relevance filter, severity, tags
│   ├── storage.py             # SQLite layer
│   └── alerts.py             # Telegram notifications
├── dashboard/
│   ├── app.py                 # Flask API + routes
│   └── templates/index.html   # Single-page dashboard
├── data/                      # SQLite database (gitignored)
├── logs/                      # Log files (gitignored)
└── tests/
    ├── test_classifier.py
    └── test_storage.py
```

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Adding Sources

Edit `RSS_FEEDS` in `config.py` to add any RSS feed:

```python
RSS_FEEDS = [
    ...
    {"name": "My Feed", "url": "https://example.com/rss"},
]
```

## Adding Keywords

Extend `IRAN_KEYWORDS`, `CONFLICT_KEYWORDS`, and the severity keyword lists in `config.py` to tune relevance and classification.
