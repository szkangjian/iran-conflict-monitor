import os
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
FETCH_INTERVAL_MINUTES = int(os.getenv("FETCH_INTERVAL_MINUTES", "15"))
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "events.db")

# RSS feeds to monitor
RSS_FEEDS = [
    {"name": "Reuters World", "url": "https://feeds.reuters.com/reuters/worldNews"},
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "AP Top News", "url": "https://rsshub.app/apnews/topics/apf-topnews"},
    {"name": "Guardian World", "url": "https://www.theguardian.com/world/rss"},
    {"name": "Times of Israel", "url": "https://www.timesofisrael.com/feed/"},
    {"name": "Jerusalem Post", "url": "https://www.jpost.com/rss/rssfeedsfrontpage.aspx"},
]

# Keywords for relevance filtering (case-insensitive)
IRAN_KEYWORDS = [
    "iran", "iranian", "tehran", "irgc", "islamic revolutionary guard",
    "khamenei", "raisi", "pezeshkian", "zarif", "nuclear deal", "jcpoa",
    "strait of hormuz", "persian gulf",
]

CONFLICT_KEYWORDS = [
    "attack", "strike", "missile", "drone", "airstrike", "bomb", "explosion",
    "military", "troops", "sanctions", "war", "conflict", "weapon", "nuclear",
    "threat", "retaliation", "escalation", "ceasefire", "hostage", "proxy",
    "hezbollah", "hamas", "houthi", "israel", "idf", "us military", "pentagon",
    "mossad", "cia", "assassination", "ballistic", "hypersonic", "uranium",
    "enrichment", "centrifuge", "natanz", "fordo",
]

# Severity classification rules
SEVERITY_CRITICAL_KEYWORDS = [
    "nuclear", "ballistic missile", "hypersonic", "war declared", "invasion",
    "assassination", "explosion", "airstrike", "strike on", "attacked",
]

SEVERITY_HIGH_KEYWORDS = [
    "missile", "drone attack", "military operation", "troops deployed",
    "sanctions", "escalation", "threat", "hostage", "seized",
]

SEVERITY_MEDIUM_KEYWORDS = [
    "tension", "warning", "protest", "arrested", "detained", "spy",
    "diplomatic", "negotiations", "talks",
]
