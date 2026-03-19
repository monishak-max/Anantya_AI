"""
Astro Web — Flask server connecting the beautiful frontend to the LLM pipeline.
"""
import os
import sys
import json
import traceback
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import date

from flask import Flask, render_template, request, jsonify

# Add parent dir so we can import the llm package
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)  # So .env and cache paths resolve correctly

from llm.pipeline import AstroPipeline

app = Flask(__name__)
pipeline = AstroPipeline(cache_enabled=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chart", methods=["POST"])
def get_chart():
    """Return natal chart summary (no LLM call)."""
    try:
        data = request.json
        summary = pipeline.get_chart_summary(
            name=data["name"],
            birth_date=date.fromisoformat(data["birth_date"]),
            birth_time=data["birth_time"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
        )
        return jsonify({"ok": True, "chart": summary})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/chart-reveal", methods=["POST"])
def generate_chart_reveal():
    """Generate LLM-powered chart reveal — headline, traits, soul line."""
    try:
        data = request.json
        result = pipeline.generate_chart_reveal(
            name=data["name"],
            birth_date=date.fromisoformat(data["birth_date"]),
            birth_time=data["birth_time"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
        )
        return jsonify({
            "ok": True,
            "reveal": result.data,
            "model": result.model,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/now", methods=["POST"])
def generate_now():
    """Generate Now collapsed + expanded."""
    try:
        data = request.json
        args = dict(
            name=data["name"],
            birth_date=date.fromisoformat(data["birth_date"]),
            birth_time=data["birth_time"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
        )

        collapsed = pipeline.generate_now_collapsed(**args)
        expanded = pipeline.generate_now_expanded(**args)

        return jsonify({
            "ok": True,
            "collapsed": collapsed.data,
            "expanded": expanded.data,
            "model": collapsed.model,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/mandala", methods=["POST"])
def generate_mandala():
    """Generate Mandala activation cards."""
    try:
        data = request.json
        result = pipeline.generate_mandala_cards(
            name=data["name"],
            birth_date=date.fromisoformat(data["birth_date"]),
            birth_time=data["birth_time"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
        )
        return jsonify({
            "ok": True,
            "cards": result.data.get("cards", []),
            "model": result.model,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/union", methods=["POST"])
def generate_union():
    """Generate Union compatibility snapshot."""
    try:
        data = request.json
        result = pipeline.generate_union_snapshot(
            name=data["name"],
            birth_date=date.fromisoformat(data["birth_date"]),
            birth_time=data["birth_time"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
            partner_name=data["partner_name"],
            partner_birth_date=date.fromisoformat(data["partner_birth_date"]),
            partner_birth_time=data["partner_birth_time"],
            partner_lat=float(data["partner_lat"]),
            partner_lng=float(data["partner_lng"]),
        )
        return jsonify({
            "ok": True,
            "union": result.data,
            "model": result.model,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/birth-chart", methods=["POST"])
def generate_birth_chart():
    """Generate premium birth chart reading."""
    try:
        data = request.json
        result = pipeline.generate_birth_chart(
            name=data["name"],
            birth_date=date.fromisoformat(data["birth_date"]),
            birth_time=data["birth_time"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
        )
        return jsonify({
            "ok": True,
            "birth_chart": result.data,
            "model": result.model,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/geocode", methods=["GET"])
def geocode():
    """Proxy to OpenStreetMap Nominatim for place → lat/lng lookup."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"ok": True, "results": []})
    try:
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
            "q": q, "format": "json", "limit": "5"
        })
        req = urllib.request.Request(url, headers={"User-Agent": "AstroApp/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        results = [
            {"display": r["display_name"], "lat": r["lat"], "lng": r["lon"]}
            for r in data
        ]
        return jsonify({"ok": True, "results": results})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("\n  ✦  Astro Web — http://localhost:5001\n")
    app.run(debug=True, port=5001)
