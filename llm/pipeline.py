"""
End-to-end pipeline: birth data → computation → LLM → validated reading.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
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
    build_chart_essence,
    build_birth_chart_yogas_input,
    build_birth_chart_forces_input,
    build_birth_chart_timing_input,
    build_birth_chart_synthesis_input,
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
        """Generate birth chart using parallel split-and-merge architecture.

        Splits the monolithic birth chart into 4 parallel sections:
        - Yogas (Sonnet)
        - Shaping Forces (Sonnet)
        - Timing + Life Phases (Sonnet)
        - Synthesis / Narrative Frame (Opus)

        Falls back to monolithic generation on failure.
        """
        token = self._cache_token(name, self._name_payload(name, birth_date, birth_time, lat, lng, "birth_chart_core", extra={"modifiers": external_modifiers or []}))
        cached = self._load_from_cache("birth_chart_core", token, birth_date)
        if cached:
            return self._hydrate_cached_result(cached)

        chart = self._get_chart(name, birth_date, birth_time, lat, lng)
        rule_matches = self._evaluate_rules(chart)

        try:
            result = self._generate_birth_chart_parallel(chart, name, rule_matches, external_modifiers)
        except Exception as exc:
            logger.warning("Parallel birth chart failed (%s), falling back to monolithic", exc)
            input_data = build_birth_chart_input(chart, name, external_modifiers=external_modifiers, rule_matches=rule_matches)
            result = self.generator.generate(Surface.BIRTH_CHART_CORE, input_data)

        self._save_to_cache("birth_chart_core", token, birth_date, result)
        return result

    def _generate_birth_chart_parallel(
        self,
        chart: NatalChart,
        name: str,
        rule_matches: list,
        external_modifiers: list[dict] | None = None,
    ) -> GenerationResult:
        """3+1 architecture: run content sections in parallel, then synthesis sees their actual output.

        Phase 1 (parallel): Yogas + Forces + Timing run simultaneously on Sonnet (~20-25s)
        Phase 2 (sequential): Synthesis runs on Opus WITH the actual prose from Phase 1 (~25-30s)

        Total: ~45-55s. Only ~5-10s slower than full parallel, but zero coherence risk.
        Synthesis genuinely references the exact words the other sections wrote.
        """
        essence = build_chart_essence(chart)
        start = time.monotonic()

        # Build Phase 1 inputs (lightweight, no I/O)
        yogas_input = build_birth_chart_yogas_input(chart, essence, rule_matches)
        forces_input = build_birth_chart_forces_input(chart, essence, rule_matches)
        timing_input = build_birth_chart_timing_input(chart, essence)

        # Phase 1: Yogas + Forces + Timing in parallel
        gen = self.generator
        logger.info("[birth_chart_3+1] Phase 1: generating yogas, forces, timing in parallel...")
        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="bc_content") as pool:
            yogas_future = pool.submit(
                gen.generate, Surface.BIRTH_CHART_YOGAS, yogas_input,
                0.7, 1,  # temperature, max_style_retries
            )
            forces_future = pool.submit(
                gen.generate, Surface.BIRTH_CHART_FORCES, forces_input,
                0.7, 1,
            )
            timing_future = pool.submit(
                gen.generate, Surface.BIRTH_CHART_TIMING, timing_input,
                0.7, 1,
            )

        yogas_result = yogas_future.result()
        forces_result = forces_future.result()
        timing_result = timing_future.result()

        phase1_ms = int((time.monotonic() - start) * 1000)
        logger.info("[birth_chart_3+1] Phase 1 done in %dms. Starting Phase 2 (synthesis with actual content)...", phase1_ms)

        # Phase 2: Build synthesis input WITH actual prose from Phase 1
        synthesis_input = build_birth_chart_synthesis_input(
            chart, essence, external_modifiers, rule_matches,
        )
        # Inject the actual generated content so synthesis sees real prose, not just names
        synthesis_input.completed_yogas_prose = self._extract_section_prose(yogas_result.data, "yogas")
        synthesis_input.completed_forces_prose = self._extract_section_prose(forces_result.data, "forces")
        synthesis_input.completed_timing_prose = self._extract_section_prose(timing_result.data, "timing")

        synthesis_result = gen.generate(Surface.BIRTH_CHART_SYNTHESIS, synthesis_input, 0.7, 1)

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Merge into single BirthChartCore-compatible dict
        merged = self._merge_birth_chart_sections(
            yogas_result, forces_result, timing_result, synthesis_result,
        )

        # Post-merge validation on full combined output
        input_for_guard = build_birth_chart_input(chart, name, external_modifiers=external_modifiers, rule_matches=rule_matches)
        input_dict = input_for_guard.model_dump()
        all_violations = gen.guard.check(merged, "birth_chart_core", input_dict)
        val_failures = gen.validator.validate(merged, "birth_chart_core")
        if val_failures:
            for f in val_failures:
                logger.warning("[birth_chart_parallel] Validation: %s — %s", f.check, f.detail)

        # Aggregate metadata
        all_results = [yogas_result, forces_result, timing_result, synthesis_result]
        all_warnings: list[str] = []
        total_retries = 0
        for r in all_results:
            all_warnings.extend(r.word_count_warnings)
            total_retries += r.retry_count

        model_label = f"{synthesis_result.model}+{yogas_result.model}"
        logger.info(
            "[birth_chart_parallel] Done in %dms (yogas=%dms, forces=%dms, timing=%dms, synthesis=%dms, retries=%d)",
            elapsed_ms,
            yogas_result.generation_time_ms,
            forces_result.generation_time_ms,
            timing_result.generation_time_ms,
            synthesis_result.generation_time_ms,
            total_retries,
        )

        return GenerationResult(
            surface="birth_chart_core",
            data=merged,
            model=model_label,
            word_count_warnings=all_warnings,
            style_violations=all_violations,
            generation_time_ms=elapsed_ms,
            retry_count=total_retries,
        )

    @staticmethod
    def _extract_section_prose(data: dict, section_type: str) -> str:
        """Extract a compact prose summary from a completed section's output.

        This is fed to synthesis so it can reference the actual words written
        by the yoga/force/timing sections, not just the names.
        """
        parts = []
        if section_type == "yogas":
            for key in ("great_yogas", "finer_yogas"):
                for item in data.get(key, []):
                    name = item.get("name", "")
                    cap = item.get("sacred_capacity", "")
                    if name and cap:
                        parts.append(f"{name}: {cap[:150]}")
        elif section_type == "forces":
            for item in data.get("deeper_shaping_forces", []):
                name = item.get("name", "")
                cap = item.get("sacred_capacity", "")
                if name and cap:
                    parts.append(f"{name}: {cap[:150]}")
        elif section_type == "timing":
            for item in data.get("great_timing_currents", []):
                name = item.get("name", "")
                body = item.get("chapter_body", "")
                if name and body:
                    parts.append(f"{name}: {body[:150]}")
        return "\n".join(parts)

    @staticmethod
    def _merge_birth_chart_sections(
        yogas: GenerationResult,
        forces: GenerationResult,
        timing: GenerationResult,
        synthesis: GenerationResult,
    ) -> dict:
        """Mechanically merge 4 section outputs into a BirthChartCore dict."""
        merged = {}

        # Synthesis fields (narrative + SDUI)
        for field in (
            "title", "opening_promise", "entrusted_beauty", "central_knot",
            "present_threshold", "love", "work", "embodiment", "closing_destiny",
            # SDUI fields
            "phase_insight_title", "affirmation", "polarity_left", "polarity_right",
        ):
            merged[field] = synthesis.data.get(field, "")
        # insights is a list, handle separately
        merged["insights"] = synthesis.data.get("insights")

        # Structured section fields
        merged["great_yogas"] = yogas.data.get("great_yogas", [])
        merged["finer_yogas"] = yogas.data.get("finer_yogas", [])
        merged["deeper_shaping_forces"] = forces.data.get("deeper_shaping_forces", [])
        merged["great_timing_currents"] = timing.data.get("great_timing_currents", [])
        merged["life_phases"] = timing.data.get("life_phases", [])

        return merged

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
