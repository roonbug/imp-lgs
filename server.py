#!/usr/bin/env python3
"""
Reference data-collection server for the Japanese Vocabulary Learning Study.

Responsibilities
----------------
1. Serve the experiment (study.html) and the img/ stimuli over http://localhost,
   which is a *secure context* — required for the Fullscreen API and clean fetch()
   uploads used by study.html.
2. Accept POSTed trial data at /api/data and persist it two ways:
     - one raw JSON file per submission  ->  data/<pid>_s<session>_<timestamp>.json
     - flattened per-trial rows appended ->  data/trials.csv
3. Provide /api/export to download the combined trials.csv.

Run
---
    pip install -r requirements.txt
    python server.py            # then open http://localhost:5000

No database; everything is written to the ./data directory next to this file.
"""

import csv
import json
import os
import re
from datetime import datetime, timezone

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TRIALS_CSV = os.path.join(DATA_DIR, "trials.csv")
EVENTS_CSV = os.path.join(DATA_DIR, "proctor_events.csv")
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__, static_folder=None)
CORS(app)  # allow the page to POST even if hosted from a different origin

# Column order for the flattened per-trial CSV (matches study.html trial records).
TRIAL_FIELDS = [
    "participant_id", "session", "study_version", "phase", "block", "trial_index",
    "item_id", "english", "romaji", "category", "condition", "has_image",
    "test_type", "direction", "prompt_onset_ts", "response_ts", "rt_ms",
    "response_raw", "response_normalized", "correct", "edit_distance",
    "confidence_or_jol", "mcq_options", "mcq_choice", "spacing_lag",
    "focus_lost_during_trial", "timestamp_iso",
]
EVENT_FIELDS = ["participant_id", "session", "event_type", "ts", "t_ms", "phase", "details"]

_SAFE = re.compile(r"[^A-Za-z0-9_-]")


def _safe(s, default="anon"):
    s = _SAFE.sub("_", str(s or default))
    return s[:64] or default


def _append_csv(path, fieldnames, rows):
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            w.writeheader()
        for r in rows:
            # serialize list/dict cells (e.g. mcq_options) as compact JSON
            out = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
                   for k, v in r.items()}
            w.writerow(out)


@app.route("/api/data", methods=["POST"])
def collect():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or "trials" not in payload:
        return jsonify(status="error", message="expected JSON with a 'trials' array"), 400

    pid = _safe(payload.get("participant_id"))
    session = _safe(payload.get("session", 1))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # 1) raw JSON, one file per submission (never overwritten)
    raw_path = os.path.join(DATA_DIR, f"{pid}_s{session}_{stamp}.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # 2) flattened trial rows
    trials = payload.get("trials") or []
    _append_csv(TRIALS_CSV, TRIAL_FIELDS, trials)

    # 3) proctoring events
    events = payload.get("proctor_events") or []
    ev_rows = [{"participant_id": payload.get("participant_id"),
                "session": payload.get("session"), **e} for e in events]
    _append_csv(EVENTS_CSV, EVENT_FIELDS, ev_rows)

    return jsonify(status="ok", saved=os.path.basename(raw_path), n_trials=len(trials))


@app.route("/api/export", methods=["GET"])
def export():
    if not os.path.exists(TRIALS_CSV):
        return jsonify(status="empty", message="no data collected yet"), 404
    with open(TRIALS_CSV, encoding="utf-8") as f:
        body = f.read()
    return Response(body, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=trials.csv"})


# ---- static hosting of the experiment + stimuli --------------------------
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "study.html")


@app.route("/<path:path>")
def static_files(path):
    # serve study.html, img/*, etc. Blocks traversal outside BASE_DIR via send_from_directory.
    return send_from_directory(BASE_DIR, path)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print(f"Serving study at http://localhost:{port}  (data -> {DATA_DIR})")
    app.run(host="0.0.0.0", port=port, debug=False)
