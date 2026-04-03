import logging
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

from monitor.storage import get_events, get_stats, get_latest_score, get_score_history

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/events")
def api_events():
    limit    = min(int(request.args.get("limit", 100)), 500)
    severity = request.args.get("severity") or None
    source   = request.args.get("source")   or None
    return jsonify(get_events(limit=limit, severity=severity, source=source))


@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


@app.route("/api/score")
def api_score():
    record = get_latest_score()
    if not record:
        return jsonify({"score": None, "message": "No score computed yet"}), 404
    # Unpack dimensions stored as flat columns
    record["dimensions"] = {
        "d1": record.pop("d1"),
        "d2": record.pop("d2"),
        "d3": record.pop("d3"),
        "d4": record.pop("d4"),
        "d5": record.pop("d5"),
    }
    return jsonify(record)


@app.route("/api/score/history")
def api_score_history():
    days = min(int(request.args.get("days", 30)), 365)
    return jsonify(get_score_history(days=days))


def run_dashboard(port: int = 5000, debug: bool = False):
    app.run(host="0.0.0.0", port=port, debug=debug)
