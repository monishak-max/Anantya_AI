"""
End-to-end test runner — real birth data → computation → LLM → reading.

Usage:
    cd astro_app
    python -m llm.run_test                         # Now collapsed (default)
    python -m llm.run_test now_expanded             # Now expanded
    python -m llm.run_test mandala_cards            # Mandala cards
    python -m llm.run_test union_snapshot           # Union
    python -m llm.run_test birth_chart_core         # Birth chart (premium, uses Opus)
    python -m llm.run_test all                      # All surfaces
    python -m llm.run_test chart                    # Just show chart data, no LLM call
"""
from __future__ import annotations

import json
import sys
import os
import logging
from datetime import date

# Ensure imports work from astro_app root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.pipeline import AstroPipeline
from llm.core.generator import GenerationResult

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


# ── Test birth data ────────────────────────────────────────────────
# Edit these to test with different profiles

USER = {
    "name": "Dhairya",
    "birth_date": date(1998, 1, 15),
    "birth_time": "10:30",
    "lat": 19.0760,   # Mumbai
    "lng": 72.8777,
}

PARTNER = {
    "name": "Priya",
    "birth_date": date(1999, 7, 22),
    "birth_time": "14:15",
    "lat": 28.6139,   # Delhi
    "lng": 77.2090,
}


# ── Pretty printer ─────────────────────────────────────────────────

def print_result(result: GenerationResult):
    print(f"\n{'='*60}")
    print(f"  SURFACE: {result.surface}")
    print(f"  MODEL:   {result.model}")
    print(f"  TIME:    {result.generation_time_ms}ms")
    print(f"  RETRIES: {result.retry_count}")
    print(f"{'='*60}\n")

    # Print the reading
    print(json.dumps(result.data, indent=2, ensure_ascii=False))

    # Quality report
    print(f"\n{'─'*40}")
    print("  QUALITY REPORT")
    print(f"{'─'*40}")

    if result.word_count_warnings:
        print("  Word count warnings:")
        for w in result.word_count_warnings:
            print(f"    ⚠ {w}")
    else:
        print("  Word counts: all within range")

    if result.style_violations:
        print("  Style violations:")
        for v in result.style_violations:
            icon = "🔴" if v.severity == "critical" else "🟡"
            print(f"    {icon} [{v.type.value}] {v.field_name}: {v.detail}")
    else:
        print("  Style: clean")

    if result.is_clean:
        print("\n  ✅ CLEAN — no issues")
    elif result.has_critical:
        print("\n  ❌ CRITICAL issues present")
    else:
        print("\n  ⚠️  Minor warnings only")

    print()


# ── Main ───────────────────────────────────────────────────────────

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "now_collapsed"

    pipeline = AstroPipeline()
    u = USER

    # Chart-only mode (no LLM call)
    if mode == "chart":
        summary = pipeline.get_chart_summary(u["name"], u["birth_date"], u["birth_time"], u["lat"], u["lng"])
        print(json.dumps(summary, indent=2, default=str))
        return

    # Surface generation
    surface_map = {
        "now_collapsed": lambda: pipeline.generate_now_collapsed(
            u["name"], u["birth_date"], u["birth_time"], u["lat"], u["lng"]
        ),
        "now_expanded": lambda: pipeline.generate_now_expanded(
            u["name"], u["birth_date"], u["birth_time"], u["lat"], u["lng"]
        ),
        "mandala_cards": lambda: pipeline.generate_mandala_cards(
            u["name"], u["birth_date"], u["birth_time"], u["lat"], u["lng"]
        ),
        "union_snapshot": lambda: pipeline.generate_union_snapshot(
            u["name"], u["birth_date"], u["birth_time"], u["lat"], u["lng"],
            PARTNER["name"], PARTNER["birth_date"], PARTNER["birth_time"], PARTNER["lat"], PARTNER["lng"],
        ),
        "birth_chart_core": lambda: pipeline.generate_birth_chart(
            u["name"], u["birth_date"], u["birth_time"], u["lat"], u["lng"]
        ),
    }

    if mode == "all":
        surfaces_to_run = list(surface_map.keys())
    elif mode in surface_map:
        surfaces_to_run = [mode]
    else:
        print(f"Unknown mode: {mode}")
        print(f"Available: {list(surface_map.keys()) + ['all', 'chart']}")
        return

    for surface_name in surfaces_to_run:
        print(f"\n🔮 Generating {surface_name}...")
        result = surface_map[surface_name]()
        print_result(result)


if __name__ == "__main__":
    main()
