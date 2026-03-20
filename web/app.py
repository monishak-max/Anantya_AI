"""Astro Web - Flask server connecting the frontend to the LLM pipeline."""
import os
import sys
import json
import traceback
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import date

from flask import Flask, render_template, request, jsonify

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from llm.pipeline import AstroPipeline

app = Flask(__name__)
pipeline = AstroPipeline(cache_enabled=True)


def _modifiers(data: dict) -> list[dict] | None:
    modifiers = data.get("external_modifiers")
    return modifiers if isinstance(modifiers, list) else None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chart", methods=["POST"])
def get_chart():
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
    try:
        data = request.json
        result = pipeline.generate_chart_reveal(
            name=data["name"],
            birth_date=date.fromisoformat(data["birth_date"]),
            birth_time=data["birth_time"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
            external_modifiers=_modifiers(data),
        )
        return jsonify({"ok": True, "reveal": result.data, "model": result.model})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/now", methods=["POST"])
def generate_now():
    try:
        data = request.json
        args = dict(
            name=data["name"],
            birth_date=date.fromisoformat(data["birth_date"]),
            birth_time=data["birth_time"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
            external_modifiers=_modifiers(data),
        )
        collapsed = pipeline.generate_now_collapsed(**args)
        expanded = pipeline.generate_now_expanded(**args)
        return jsonify({"ok": True, "collapsed": collapsed.data, "expanded": expanded.data, "model": collapsed.model})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/mandala", methods=["POST"])
def generate_mandala():
    try:
        data = request.json
        result = pipeline.generate_mandala_cards(
            name=data["name"],
            birth_date=date.fromisoformat(data["birth_date"]),
            birth_time=data["birth_time"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
            external_modifiers=_modifiers(data),
        )
        return jsonify({"ok": True, "cards": result.data.get("cards", []), "model": result.model})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/mandala-deep", methods=["POST"])
def generate_mandala_deep():
    try:
        data = request.json
        result = pipeline.generate_mandala_deep_read(
            name=data["name"],
            birth_date=date.fromisoformat(data["birth_date"]),
            birth_time=data["birth_time"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
            activation_planet=data.get("activation_planet", "Saturn"),
            external_modifiers=_modifiers(data),
        )
        return jsonify({"ok": True, "deep_read": result.data, "model": result.model})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/union", methods=["POST"])
def generate_union():
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
            external_modifiers=_modifiers(data),
        )
        return jsonify({"ok": True, "union": result.data, "model": result.model})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/union-deep", methods=["POST"])
def generate_union_deep():
    try:
        data = request.json
        result = pipeline.generate_union_deep_read(
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
            external_modifiers=_modifiers(data),
        )
        return jsonify({"ok": True, "union_deep": result.data, "model": result.model})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/birth-chart", methods=["POST"])
def generate_birth_chart():
    try:
        data = request.json
        result = pipeline.generate_birth_chart(
            name=data["name"],
            birth_date=date.fromisoformat(data["birth_date"]),
            birth_time=data["birth_time"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
            external_modifiers=_modifiers(data),
        )
        return jsonify({"ok": True, "birth_chart": result.data, "model": result.model})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/weekly-overview", methods=["POST"])
def generate_weekly_overview():
    try:
        data = request.json
        result = pipeline.generate_weekly_overview(
            name=data["name"],
            birth_date=date.fromisoformat(data["birth_date"]),
            birth_time=data["birth_time"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
            external_modifiers=_modifiers(data),
        )
        return jsonify({"ok": True, "weekly": result.data, "model": result.model})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/monthly-overview", methods=["POST"])
def generate_monthly_overview():
    try:
        data = request.json
        result = pipeline.generate_monthly_overview(
            name=data["name"],
            birth_date=date.fromisoformat(data["birth_date"]),
            birth_time=data["birth_time"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
            external_modifiers=_modifiers(data),
        )
        return jsonify({"ok": True, "monthly": result.data, "model": result.model})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/geocode", methods=["GET"])
def geocode():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"ok": True, "results": []})
    try:
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": q, "format": "json", "limit": "5"})
        req = urllib.request.Request(url, headers={"User-Agent": "AstroApp/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        results = [{"display": r["display_name"], "lat": r["lat"], "lng": r["lon"]} for r in data]
        return jsonify({"ok": True, "results": results})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("\n  ✦  Astro Web - http://localhost:5001\n")
    app.run(debug=True, port=5001, host="0.0.0.0")
