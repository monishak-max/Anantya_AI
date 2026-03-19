"""
End-to-end pipeline: birth data → computation → LLM → validated reading.

This is the main entry point for generating any reading in the app.

Usage:
    from llm.pipeline import AstroPipeline

    pipeline = AstroPipeline()
    result = pipeline.generate_now("Dhairya", date(1998, 1, 15), "10:30", 19.076, 72.878)
    print(result.data)
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import date
from pathlib import Path

from llm.core.config import Surface
from llm.guards.style_guard import Violation, ViolationType
from llm.core.generator import AstroGenerator, GenerationResult
from llm.engine.calculator import compute_natal_chart, compute_transits, NatalChart
from llm.engine.bridge import (
    build_now_input,
    build_mandala_input,
    build_mandala_deep_read_input,
    build_union_input,
    build_chart_reveal_input,
    build_birth_chart_input,
    build_period_overview_input,
)

logger = logging.getLogger("astro.pipeline")

# Local cache directory
CACHE_DIR = Path(__file__).parent / ".cache"


class AstroPipeline:
    """
    Full pipeline: birth details → astro computation → LLM generation → validated reading.

    Handles:
    - Natal chart computation (cached per user)
    - Transit computation (refreshed per day)
    - LLM generation with model routing
    - Post-generation style guard
    - Local file caching of results
    """

    def __init__(self, api_key: str | None = None, cache_enabled: bool = True):
        self._api_key = api_key
        self._generator: AstroGenerator | None = None
        self.cache_enabled = cache_enabled
        self._chart_cache: dict[str, NatalChart] = {}

        if cache_enabled:
            CACHE_DIR.mkdir(exist_ok=True)

    @property
    def generator(self) -> AstroGenerator:
        """Lazy init — only creates LLM client when first needed."""
        if self._generator is None:
            self._generator = AstroGenerator(api_key=self._api_key)
        return self._generator

    def _get_chart(
        self,
        name: str,
        birth_date: date,
        birth_time: str,
        lat: float,
        lng: float,
    ) -> NatalChart:
        """Get or compute natal chart (cached in memory per session)."""
        key = f"{birth_date}_{birth_time}_{lat}_{lng}"
        if key not in self._chart_cache:
            self._chart_cache[key] = compute_natal_chart(birth_date, birth_time, lat, lng)
        return self._chart_cache[key]

    def _cache_token(self, label: str, payload: dict) -> str:
        digest = hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:12]
        safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in label).strip("_")[:24] or "reading"
        return f"{safe}_{digest}"

    def _hydrate_cached_result(self, cached: dict) -> GenerationResult:
        style_violations = [
            Violation(
                type=ViolationType(v["type"]),
                field_name=v.get("field_name") or v.get("field") or "",
                detail=v["detail"],
                severity=v.get("severity", "warning"),
            )
            for v in cached.get("style_violations", [])
        ]
        return GenerationResult(
            surface=cached["surface"],
            data=cached["data"],
            model=cached["model"],
            word_count_warnings=cached.get("word_count_warnings", []),
            style_violations=style_violations,
            generation_time_ms=cached.get("generation_time_ms", 0),
            retry_count=cached.get("retry_count", 0),
        )

    def _save_to_cache(self, surface: str, name: str, target_date: date, result: GenerationResult):
        """Save generated reading to local JSON file."""
        if not self.cache_enabled:
            return
        filename = f"{name}_{surface}_{target_date}.json"
        path = CACHE_DIR / filename
        cache_data = {
            "surface": result.surface,
            "model": result.model,
            "generation_time_ms": result.generation_time_ms,
            "word_count_warnings": result.word_count_warnings,
            "style_violations": [
                {"type": v.type.value, "field_name": v.field_name, "detail": v.detail, "severity": v.severity}
                for v in result.style_violations
            ],
            "retry_count": result.retry_count,
            "data": result.data,
        }
        path.write_text(json.dumps(cache_data, indent=2, default=str))
        logger.info(f"Cached: {path}")

    def _load_from_cache(self, surface: str, name: str, target_date: date) -> dict | None:
        """Load a cached reading if it exists."""
        if not self.cache_enabled:
            return None
        filename = f"{name}_{surface}_{target_date}.json"
        path = CACHE_DIR / filename
        if path.exists():
            logger.info(f"Cache hit: {path}")
            return json.loads(path.read_text())
        return None

    # ── Surface-specific generators ────────────────────────────────

    def generate_now_collapsed(
        self,
        name: str,
        birth_date: date,
        birth_time: str,
        lat: float,
        lng: float,
        target_date: date | None = None,
    ) -> GenerationResult:
        """Generate the Now tab collapsed card."""
        target = target_date or date.today()

        cache_key = self._cache_token(name, {"name": name, "birth_date": birth_date, "birth_time": birth_time, "lat": round(lat, 4), "lng": round(lng, 4), "target": target, "surface": "now_collapsed"})

        # Check cache
        cached = self._load_from_cache("now_collapsed", cache_key, target)
        if cached:
            return self._hydrate_cached_result(cached)

        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        transits = compute_transits(target, chart.moon_sign)
        input_data = build_now_input(chart, transits, name)

        result = self.generator.generate(Surface.NOW_COLLAPSED, input_data)
        self._save_to_cache("now_collapsed", cache_key, target, result)
        return result

    def generate_now_expanded(
        self,
        name: str,
        birth_date: date,
        birth_time: str,
        lat: float,
        lng: float,
        target_date: date | None = None,
    ) -> GenerationResult:
        """Generate the Now tab expanded (Dive Deeper) view."""
        target = target_date or date.today()

        cache_key = self._cache_token(name, {"name": name, "birth_date": birth_date, "birth_time": birth_time, "lat": round(lat, 4), "lng": round(lng, 4), "target": target, "surface": "now_expanded"})

        cached = self._load_from_cache("now_expanded", cache_key, target)
        if cached:
            return self._hydrate_cached_result(cached)

        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        transits = compute_transits(target, chart.moon_sign)
        input_data = build_now_input(chart, transits, name)

        result = self.generator.generate(Surface.NOW_EXPANDED, input_data)
        self._save_to_cache("now_expanded", cache_key, target, result)
        return result

    def generate_mandala_cards(
        self,
        name: str,
        birth_date: date,
        birth_time: str,
        lat: float,
        lng: float,
        target_date: date | None = None,
    ) -> GenerationResult:
        """Generate Mandala activation cards."""
        target = target_date or date.today()

        cache_key = self._cache_token(name, {"name": name, "birth_date": birth_date, "birth_time": birth_time, "lat": round(lat, 4), "lng": round(lng, 4), "target": target, "surface": "mandala_cards"})

        cached = self._load_from_cache("mandala_cards", cache_key, target)
        if cached:
            return self._hydrate_cached_result(cached)

        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        transits = compute_transits(target, chart.moon_sign)
        input_data = build_mandala_input(chart, transits, name)

        result = self.generator.generate(Surface.MANDALA_CARDS, input_data)
        self._save_to_cache("mandala_cards", cache_key, target, result)
        return result

    def generate_union_snapshot(
        self,
        name: str,
        birth_date: date,
        birth_time: str,
        lat: float,
        lng: float,
        partner_name: str,
        partner_birth_date: date,
        partner_birth_time: str,
        partner_lat: float,
        partner_lng: float,
        target_date: date | None = None,
    ) -> GenerationResult:
        """Generate Union compatibility snapshot."""
        target = target_date or date.today()
        cache_key = self._cache_token(f"{name}_{partner_name}", {"name": name, "partner_name": partner_name, "birth_date": birth_date, "birth_time": birth_time, "lat": round(lat, 4), "lng": round(lng, 4), "partner_birth_date": partner_birth_date, "partner_birth_time": partner_birth_time, "partner_lat": round(partner_lat, 4), "partner_lng": round(partner_lng, 4), "target": target, "surface": "union_snapshot"})

        cached = self._load_from_cache("union_snapshot", cache_key, target)
        if cached:
            return self._hydrate_cached_result(cached)

        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        partner_chart = self._get_chart(partner_name, partner_birth_date, partner_birth_time, partner_lat, partner_lng)
        transits = compute_transits(target, chart.moon_sign)
        input_data = build_union_input(chart, partner_chart, transits, name, partner_name)

        result = self.generator.generate(Surface.UNION_SNAPSHOT, input_data)
        self._save_to_cache("union_snapshot", cache_key, target, result)
        return result

    def generate_chart_reveal(
        self,
        name: str,
        birth_date: date,
        birth_time: str,
        lat: float,
        lng: float,
    ) -> GenerationResult:
        """Generate the chart reveal — first content the member ever sees."""
        cache_key = self._cache_token(name, {"name": name, "birth_date": birth_date, "birth_time": birth_time, "lat": round(lat, 4), "lng": round(lng, 4), "surface": "chart_reveal"})

        cached = self._load_from_cache("chart_reveal", cache_key, birth_date)
        if cached:
            return self._hydrate_cached_result(cached)

        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        input_data = build_chart_reveal_input(chart, name)

        result = self.generator.generate(Surface.CHART_REVEAL, input_data)
        self._save_to_cache("chart_reveal", cache_key, birth_date, result)
        return result

    def generate_birth_chart(
        self,
        name: str,
        birth_date: date,
        birth_time: str,
        lat: float,
        lng: float,
    ) -> GenerationResult:
        """Generate premium birth chart reading (Janam Patri)."""
        cache_key = self._cache_token(name, {"name": name, "birth_date": birth_date, "birth_time": birth_time, "lat": round(lat, 4), "lng": round(lng, 4), "surface": "birth_chart_core"})

        cached = self._load_from_cache("birth_chart_core", cache_key, birth_date)
        if cached:
            return self._hydrate_cached_result(cached)

        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        input_data = build_birth_chart_input(chart, name)

        result = self.generator.generate(Surface.BIRTH_CHART_CORE, input_data)
        self._save_to_cache("birth_chart_core", cache_key, birth_date, result)
        return result

    def generate_mandala_deep_read(
        self,
        name: str,
        birth_date: date,
        birth_time: str,
        lat: float,
        lng: float,
        activation_planet: str = "Saturn",
        target_date: date | None = None,
    ) -> GenerationResult:
        """Generate Mandala deep read — zoom into one activation card."""
        target = target_date or date.today()
        cache_key = self._cache_token(name, {"name": name, "birth_date": birth_date, "birth_time": birth_time, "lat": round(lat, 4), "lng": round(lng, 4), "target": target, "activation": activation_planet, "surface": "mandala_deep_read"})

        cached = self._load_from_cache("mandala_deep_read", cache_key, target)
        if cached:
            return self._hydrate_cached_result(cached)

        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        transits = compute_transits(target, chart.moon_sign)
        input_data = build_mandala_deep_read_input(chart, transits, name, activation_planet)

        result = self.generator.generate(Surface.MANDALA_DEEP_READ, input_data)
        self._save_to_cache("mandala_deep_read", cache_key, target, result)
        return result

    def generate_union_deep_read(
        self,
        name: str,
        birth_date: date,
        birth_time: str,
        lat: float,
        lng: float,
        partner_name: str,
        partner_birth_date: date,
        partner_birth_time: str,
        partner_lat: float,
        partner_lng: float,
        target_date: date | None = None,
    ) -> GenerationResult:
        """Generate Union deep read — premium compatibility reading."""
        target = target_date or date.today()
        cache_key = self._cache_token(f"{name}_{partner_name}", {"name": name, "partner_name": partner_name, "birth_date": birth_date, "birth_time": birth_time, "lat": round(lat, 4), "lng": round(lng, 4), "partner_birth_date": partner_birth_date, "partner_birth_time": partner_birth_time, "partner_lat": round(partner_lat, 4), "partner_lng": round(partner_lng, 4), "target": target, "surface": "union_deep_read"})

        cached = self._load_from_cache("union_deep_read", cache_key, target)
        if cached:
            return self._hydrate_cached_result(cached)

        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        partner_chart = self._get_chart(partner_name, partner_birth_date, partner_birth_time, partner_lat, partner_lng)
        transits = compute_transits(target, chart.moon_sign)
        input_data = build_union_input(chart, partner_chart, transits, name, partner_name)

        result = self.generator.generate(Surface.UNION_DEEP_READ, input_data)
        self._save_to_cache("union_deep_read", cache_key, target, result)
        return result

    def generate_weekly_overview(
        self,
        name: str,
        birth_date: date,
        birth_time: str,
        lat: float,
        lng: float,
        target_date: date | None = None,
    ) -> GenerationResult:
        """Generate weekly overview."""
        target = target_date or date.today()
        cache_key = self._cache_token(name, {"name": name, "birth_date": birth_date, "birth_time": birth_time, "lat": round(lat, 4), "lng": round(lng, 4), "target": target, "surface": "weekly_overview"})

        cached = self._load_from_cache("weekly_overview", cache_key, target)
        if cached:
            return self._hydrate_cached_result(cached)

        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        transits = compute_transits(target, chart.moon_sign)
        input_data = build_period_overview_input(chart, transits, name, "weekly")

        result = self.generator.generate(Surface.WEEKLY_OVERVIEW, input_data)
        self._save_to_cache("weekly_overview", cache_key, target, result)
        return result

    def generate_monthly_overview(
        self,
        name: str,
        birth_date: date,
        birth_time: str,
        lat: float,
        lng: float,
        target_date: date | None = None,
    ) -> GenerationResult:
        """Generate monthly overview."""
        target = target_date or date.today()
        cache_key = self._cache_token(name, {"name": name, "birth_date": birth_date, "birth_time": birth_time, "lat": round(lat, 4), "lng": round(lng, 4), "target": target, "surface": "monthly_overview"})

        cached = self._load_from_cache("monthly_overview", cache_key, target)
        if cached:
            return self._hydrate_cached_result(cached)

        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        transits = compute_transits(target, chart.moon_sign)
        input_data = build_period_overview_input(chart, transits, name, "monthly")

        result = self.generator.generate(Surface.MONTHLY_OVERVIEW, input_data)
        self._save_to_cache("monthly_overview", cache_key, target, result)
        return result

    # ── Utility ────────────────────────────────────────────────────

    def get_chart_summary(
        self,
        name: str,
        birth_date: date,
        birth_time: str,
        lat: float,
        lng: float,
    ) -> dict:
        """
        Get a summary of the natal chart without generating any reading.
        Useful for debugging and onboarding confirmation.
        """
        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        transits = compute_transits(date.today(), chart.moon_sign)

        return {
            "name": name,
            "lagna_sign": chart.lagna_sign,
            "moon": {
                "sign": chart.moon_sign,
                "degree": chart.moon_degree,
                "nakshatra": chart.moon_nakshatra,
                "pada": chart.moon_nakshatra_pada,
            },
            "dasha": {
                "mahadasha": chart.mahadasha.lord,
                "antardasha": chart.antardasha.antardasha_lord,
                "maha_start": str(chart.mahadasha.start.date()),
                "maha_end": str(chart.mahadasha.end.date()),
            },
            "today_moon": {
                "sign": transits.moon_sign,
                "nakshatra": transits.moon_nakshatra,
                "house_from_natal": transits.moon_house_from_natal,
            },
            "planets": {
                name: {
                    "sign": pos.sign,
                    "degree": pos.degree_in_sign,
                    "nakshatra": pos.nakshatra,
                    "house": pos.house_from_moon,
                    "retrograde": pos.retrograde,
                }
                for name, pos in chart.planets.items()
            },
        }
