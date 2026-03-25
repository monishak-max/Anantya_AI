"""
End-to-end pipeline: birth data → computation → LLM → validated reading.
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
from llm.engine.calculator import compute_natal_chart, compute_transits, NatalChart, TransitSnapshot
from llm.engine.bridge import (
    build_now_input,
    build_mandala_input,
    build_mandala_deep_read_input,
    build_union_input,
    build_chart_reveal_input,
    build_birth_chart_input,
    build_period_overview_input,
)
from llm.engine.rules import (
    load_rules_from_file,
    RuleEvaluator,
    RuleValidationError,
)
from llm.engine.rules.context import build_rule_context

logger = logging.getLogger("astro.pipeline")
CACHE_DIR = Path(__file__).parent / ".cache"


class AstroPipeline:
    DEFAULT_RULES_PATH = Path(__file__).parent / "engine" / "rules" / "sample_rules.json"

    def __init__(self, api_key: str | None = None, cache_enabled: bool = True, rules_path: str | Path | None = None):
        self._api_key = api_key
        self._generator: AstroGenerator | None = None
        self.cache_enabled = cache_enabled
        self._chart_cache: dict[str, NatalChart] = {}
        self._rules = self._load_rules(rules_path)
        if cache_enabled:
            CACHE_DIR.mkdir(exist_ok=True)

    def _load_rules(self, rules_path: str | Path | None = None) -> list:
        path = Path(rules_path) if rules_path else self.DEFAULT_RULES_PATH
        try:
            return load_rules_from_file(path)
        except (RuleValidationError, FileNotFoundError, Exception) as exc:
            logger.warning("Rule engine unavailable (%s): %s", type(exc).__name__, exc)
            return []

    def _evaluate_rules(self, chart: NatalChart, transits: TransitSnapshot | None = None) -> list:
        if not self._rules:
            return []
        try:
            ctx = build_rule_context(chart, transits)
            evaluator = RuleEvaluator(self._rules)
            matches = evaluator.evaluate(ctx)
            for m in matches:
                logger.debug("Rule matched: %s (priority=%d, evidence=%s)", m.rule.id, m.priority, m.evidence_summary)
            return matches
        except Exception as exc:
            logger.warning("Rule evaluation failed: %s", exc)
            return []

    @property
    def generator(self) -> AstroGenerator:
        if self._generator is None:
            self._generator = AstroGenerator(api_key=self._api_key)
        return self._generator

    def _get_chart(self, name: str, birth_date: date, birth_time: str, lat: float, lng: float) -> NatalChart:
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

    def _save_to_cache(self, surface: str, token: str, cache_date: date, result: GenerationResult):
        if not self.cache_enabled:
            return
        path = CACHE_DIR / f"{token}_{surface}_{cache_date}.json"
        payload = {
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
        path.write_text(json.dumps(payload, indent=2, default=str))
        logger.info("Cached: %s", path)

    def _load_from_cache(self, surface: str, token: str, cache_date: date) -> dict | None:
        if not self.cache_enabled:
            return None
        path = CACHE_DIR / f"{token}_{surface}_{cache_date}.json"
        if path.exists():
            logger.info("Cache hit: %s", path)
            return json.loads(path.read_text())
        return None

    def _name_payload(self, name: str, birth_date: date, birth_time: str, lat: float, lng: float, surface: str, target: date | None = None, extra: dict | None = None) -> dict:
        payload = {
            "name": name,
            "birth_date": birth_date,
            "birth_time": birth_time,
            "lat": round(lat, 4),
            "lng": round(lng, 4),
            "surface": surface,
        }
        if target is not None:
            payload["target"] = target
        if extra:
            payload.update(extra)
        return payload

    def generate_now_collapsed(self, name: str, birth_date: date, birth_time: str, lat: float, lng: float, target_date: date | None = None, external_modifiers: list[dict] | None = None) -> GenerationResult:
        target = target_date or date.today()
        token = self._cache_token(name, self._name_payload(name, birth_date, birth_time, lat, lng, "now_collapsed", target, {"modifiers": external_modifiers or []}))
        cached = self._load_from_cache("now_collapsed", token, target)
        if cached:
            return self._hydrate_cached_result(cached)
        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        transits = compute_transits(target, chart.moon_sign)
        rule_matches = self._evaluate_rules(chart, transits)
        input_data = build_now_input(chart, transits, name, external_modifiers=external_modifiers, rule_matches=rule_matches)
        result = self.generator.generate(Surface.NOW_COLLAPSED, input_data)
        self._save_to_cache("now_collapsed", token, target, result)
        return result

    def generate_now_expanded(self, name: str, birth_date: date, birth_time: str, lat: float, lng: float, target_date: date | None = None, external_modifiers: list[dict] | None = None) -> GenerationResult:
        target = target_date or date.today()
        token = self._cache_token(name, self._name_payload(name, birth_date, birth_time, lat, lng, "now_expanded", target, {"modifiers": external_modifiers or []}))
        cached = self._load_from_cache("now_expanded", token, target)
        if cached:
            return self._hydrate_cached_result(cached)
        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        transits = compute_transits(target, chart.moon_sign)
        rule_matches = self._evaluate_rules(chart, transits)
        input_data = build_now_input(chart, transits, name, external_modifiers=external_modifiers, rule_matches=rule_matches)
        result = self.generator.generate(Surface.NOW_EXPANDED, input_data)
        self._save_to_cache("now_expanded", token, target, result)
        return result

    def generate_mandala_cards(self, name: str, birth_date: date, birth_time: str, lat: float, lng: float, target_date: date | None = None, external_modifiers: list[dict] | None = None) -> GenerationResult:
        target = target_date or date.today()
        token = self._cache_token(name, self._name_payload(name, birth_date, birth_time, lat, lng, "mandala_cards", target, {"modifiers": external_modifiers or []}))
        cached = self._load_from_cache("mandala_cards", token, target)
        if cached:
            return self._hydrate_cached_result(cached)
        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        transits = compute_transits(target, chart.moon_sign)
        rule_matches = self._evaluate_rules(chart, transits)
        input_data = build_mandala_input(chart, transits, name, external_modifiers=external_modifiers, rule_matches=rule_matches)
        result = self.generator.generate(Surface.MANDALA_CARDS, input_data)
        self._save_to_cache("mandala_cards", token, target, result)
        return result

    def generate_union_snapshot(self, name: str, birth_date: date, birth_time: str, lat: float, lng: float, partner_name: str, partner_birth_date: date, partner_birth_time: str, partner_lat: float, partner_lng: float, target_date: date | None = None, external_modifiers: list[dict] | None = None) -> GenerationResult:
        target = target_date or date.today()
        token = self._cache_token(f"{name}_{partner_name}", self._name_payload(name, birth_date, birth_time, lat, lng, "union_snapshot", target, {"partner_name": partner_name, "partner_birth_date": partner_birth_date, "partner_birth_time": partner_birth_time, "partner_lat": round(partner_lat, 4), "partner_lng": round(partner_lng, 4), "modifiers": external_modifiers or []}))
        cached = self._load_from_cache("union_snapshot", token, target)
        if cached:
            return self._hydrate_cached_result(cached)
        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        partner_chart = self._get_chart(partner_name, partner_birth_date, partner_birth_time, partner_lat, partner_lng)
        transits = compute_transits(target, chart.moon_sign)
        rule_matches = self._evaluate_rules(chart, transits)
        input_data = build_union_input(chart, partner_chart, transits, name, partner_name, deep=False, external_modifiers=external_modifiers, rule_matches=rule_matches)
        result = self.generator.generate(Surface.UNION_SNAPSHOT, input_data)
        self._save_to_cache("union_snapshot", token, target, result)
        return result

    def generate_chart_reveal(self, name: str, birth_date: date, birth_time: str, lat: float, lng: float, external_modifiers: list[dict] | None = None) -> GenerationResult:
        token = self._cache_token(name, self._name_payload(name, birth_date, birth_time, lat, lng, "chart_reveal", extra={"modifiers": external_modifiers or []}))
        cached = self._load_from_cache("chart_reveal", token, birth_date)
        if cached:
            return self._hydrate_cached_result(cached)
        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        rule_matches = self._evaluate_rules(chart)
        input_data = build_chart_reveal_input(chart, name, external_modifiers=external_modifiers, rule_matches=rule_matches)
        result = self.generator.generate(Surface.CHART_REVEAL, input_data)
        self._save_to_cache("chart_reveal", token, birth_date, result)
        return result

    def generate_birth_chart(self, name: str, birth_date: date, birth_time: str, lat: float, lng: float, external_modifiers: list[dict] | None = None) -> GenerationResult:
        token = self._cache_token(name, self._name_payload(name, birth_date, birth_time, lat, lng, "birth_chart_core", extra={"modifiers": external_modifiers or []}))
        cached = self._load_from_cache("birth_chart_core", token, birth_date)
        if cached:
            return self._hydrate_cached_result(cached)
        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        rule_matches = self._evaluate_rules(chart)
        input_data = build_birth_chart_input(chart, name, external_modifiers=external_modifiers, rule_matches=rule_matches)
        result = self.generator.generate(Surface.BIRTH_CHART_CORE, input_data)
        self._save_to_cache("birth_chart_core", token, birth_date, result)
        return result

    def generate_mandala_deep_read(self, name: str, birth_date: date, birth_time: str, lat: float, lng: float, activation_planet: str = "Saturn", target_date: date | None = None, external_modifiers: list[dict] | None = None) -> GenerationResult:
        target = target_date or date.today()
        token = self._cache_token(name, self._name_payload(name, birth_date, birth_time, lat, lng, "mandala_deep_read", target, {"activation": activation_planet, "modifiers": external_modifiers or []}))
        cached = self._load_from_cache("mandala_deep_read", token, target)
        if cached:
            return self._hydrate_cached_result(cached)
        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        transits = compute_transits(target, chart.moon_sign)
        rule_matches = self._evaluate_rules(chart, transits)
        input_data = build_mandala_deep_read_input(chart, transits, name, activation_planet, external_modifiers=external_modifiers, rule_matches=rule_matches)
        result = self.generator.generate(Surface.MANDALA_DEEP_READ, input_data)
        self._save_to_cache("mandala_deep_read", token, target, result)
        return result

    def generate_union_deep_read(self, name: str, birth_date: date, birth_time: str, lat: float, lng: float, partner_name: str, partner_birth_date: date, partner_birth_time: str, partner_lat: float, partner_lng: float, target_date: date | None = None, external_modifiers: list[dict] | None = None) -> GenerationResult:
        target = target_date or date.today()
        token = self._cache_token(f"{name}_{partner_name}", self._name_payload(name, birth_date, birth_time, lat, lng, "union_deep_read", target, {"partner_name": partner_name, "partner_birth_date": partner_birth_date, "partner_birth_time": partner_birth_time, "partner_lat": round(partner_lat, 4), "partner_lng": round(partner_lng, 4), "modifiers": external_modifiers or []}))
        cached = self._load_from_cache("union_deep_read", token, target)
        if cached:
            return self._hydrate_cached_result(cached)
        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        partner_chart = self._get_chart(partner_name, partner_birth_date, partner_birth_time, partner_lat, partner_lng)
        transits = compute_transits(target, chart.moon_sign)
        rule_matches = self._evaluate_rules(chart, transits)
        input_data = build_union_input(chart, partner_chart, transits, name, partner_name, deep=True, external_modifiers=external_modifiers, rule_matches=rule_matches)
        result = self.generator.generate(Surface.UNION_DEEP_READ, input_data)
        self._save_to_cache("union_deep_read", token, target, result)
        return result

    def generate_weekly_overview(self, name: str, birth_date: date, birth_time: str, lat: float, lng: float, target_date: date | None = None, external_modifiers: list[dict] | None = None) -> GenerationResult:
        target = target_date or date.today()
        token = self._cache_token(name, self._name_payload(name, birth_date, birth_time, lat, lng, "weekly_overview", target, {"modifiers": external_modifiers or []}))
        cached = self._load_from_cache("weekly_overview", token, target)
        if cached:
            return self._hydrate_cached_result(cached)
        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        transits = compute_transits(target, chart.moon_sign)
        rule_matches = self._evaluate_rules(chart, transits)
        input_data = build_period_overview_input(chart, transits, name, "weekly", target_date=target, external_modifiers=external_modifiers, rule_matches=rule_matches)
        result = self.generator.generate(Surface.WEEKLY_OVERVIEW, input_data)
        self._save_to_cache("weekly_overview", token, target, result)
        return result

    def generate_monthly_overview(self, name: str, birth_date: date, birth_time: str, lat: float, lng: float, target_date: date | None = None, external_modifiers: list[dict] | None = None) -> GenerationResult:
        target = target_date or date.today()
        token = self._cache_token(name, self._name_payload(name, birth_date, birth_time, lat, lng, "monthly_overview", target, {"modifiers": external_modifiers or []}))
        cached = self._load_from_cache("monthly_overview", token, target)
        if cached:
            return self._hydrate_cached_result(cached)
        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        transits = compute_transits(target, chart.moon_sign)
        rule_matches = self._evaluate_rules(chart, transits)
        input_data = build_period_overview_input(chart, transits, name, "monthly", target_date=target, external_modifiers=external_modifiers, rule_matches=rule_matches)
        result = self.generator.generate(Surface.MONTHLY_OVERVIEW, input_data)
        self._save_to_cache("monthly_overview", token, target, result)
        return result

    def get_chart_summary(self, name: str, birth_date: date, birth_time: str, lat: float, lng: float) -> dict:
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
                pname: {
                    "sign": pos.sign,
                    "degree": float(pos.degree_in_sign),
                    "nakshatra": pos.nakshatra,
                    "house": int(pos.house_from_moon) if pos.house_from_moon is not None else None,
                    "retrograde": bool(pos.retrograde),
                    "navamsha_sign": pos.navamsha_sign,
                }
                for pname, pos in chart.planets.items()
            },
        }
