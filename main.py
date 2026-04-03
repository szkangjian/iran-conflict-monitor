#!/usr/bin/env python3
"""
Iran Conflict Monitor — entry point.

Usage:
    python main.py              # Run monitor + dashboard
    python main.py --fetch-once # Single fetch cycle and exit
    python main.py --dashboard  # Dashboard only (no scheduler)
"""

import argparse
import logging
import sys
import os

from dotenv import load_dotenv

load_dotenv()

from config import FETCH_INTERVAL_MINUTES, DASHBOARD_PORT, LOG_LEVEL

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join("logs", "monitor.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


def run_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    from monitor.fetcher import run_fetch_cycle
    from monitor.alerts import send_pending_alerts

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(run_fetch_cycle, "interval", minutes=FETCH_INTERVAL_MINUTES, id="fetch")
    scheduler.add_job(send_pending_alerts, "interval", minutes=5, id="alerts")
    scheduler.start()
    logger.info("Scheduler started (fetch every %d min)", FETCH_INTERVAL_MINUTES)
    return scheduler


def main():
    parser = argparse.ArgumentParser(description="Iran Conflict Monitor")
    parser.add_argument("--fetch-once", action="store_true", help="Run one fetch cycle and exit")
    parser.add_argument("--dashboard", action="store_true", help="Start dashboard only")
    parser.add_argument("--port", type=int, default=DASHBOARD_PORT)
    args = parser.parse_args()

    from monitor.storage import init_db
    init_db()

    if args.fetch_once:
        from monitor.fetcher import run_fetch_cycle
        results = run_fetch_cycle()
        print(f"Fetch complete. New events: {results['total_new']}")
        return

    scheduler = None
    if not args.dashboard:
        # Kick off an immediate fetch before starting the scheduler
        from monitor.fetcher import run_fetch_cycle
        logger.info("Running initial fetch …")
        run_fetch_cycle()
        scheduler = run_scheduler()

    try:
        from dashboard.app import run_dashboard
        logger.info("Dashboard starting on http://0.0.0.0:%d", args.port)
        run_dashboard(port=args.port)
    finally:
        if scheduler:
            scheduler.shutdown()


if __name__ == "__main__":
    main()
