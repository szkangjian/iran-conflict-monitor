import logging
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

from monitor.storage import get_events, get_stats

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/events")
def api_events():
    limit = min(int(request.args.get("limit", 100)), 500)
    severity = request.args.get("severity") or None
    source = request.args.get("source") or None
    events = get_events(limit=limit, severity=severity, source=source)
    return jsonify(events)


@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


def run_dashboard(port: int = 5000, debug: bool = False):
    app.run(host="0.0.0.0", port=port, debug=debug)
