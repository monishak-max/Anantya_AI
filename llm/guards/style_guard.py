"""
Style Guard — post-generation quality check.
Adapted from Aatman's style_guard.py for Astro's editorial (non-conversational) context.

Checks for:
1. Tone violations (fear, determinism, therapy-speak, generic horoscope)
2. Jargon leakage (raw Sanskrit/Jyotish terms that should be translated)
3. Red line violations (death, curses, catastrophe predictions)
4. Word count compliance per field
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ViolationType(str, Enum):
    DETERMINISTIC = "deterministic"        # "you will", "this will happen"
    FEAR_INDUCING = "fear_inducing"        # catastrophe, doom language
    THERAPY_SPEAK = "therapy_speak"        # "your feelings are valid", etc.
    GENERIC_HOROSCOPE = "generic_horoscope"  # filler, vague positivity
    JARGON_LEAKAGE = "jargon_leakage"     # raw Sanskrit without translation
    RED_LINE = "red_line"                  # death, curses, etc.
    ROBOTIC = "robotic"                    # "as an AI", "I'm a language model"
    EXCLAMATION_HEAVY = "exclamation_heavy"  # too many !
    EM_DASH = "em_dash"                    # overused AI writing tic
    WORD_COUNT = "word_count"              # outside target range
    LOW_SPECIFICITY = "low_specificity"    # reading could apply to anyone


@dataclass
class Violation:
    type: ViolationType
    field_name: str
    detail: str
    severity: str = "warning"  # "warning" or "critical"


# ── Pattern lists ──────────────────────────────────────────────────

DETERMINISTIC_PATTERNS = [
    r"\byou will\b",
    r"\bthis will happen\b",
    r"\byou are destined\b",
    r"\bfated to\b",
    r"\bthe stars say\b",
    r"\bthe planets decree\b",
    r"\byour fate is\b",
    r"\binevitably\b",
    r"\bcertainly will\b",
    r"\bwithout doubt\b",
    r"\bguaranteed\b",
]

FEAR_PATTERNS = [
    r"\bcatastroph",
    r"\bdoom\b",
    r"\bcurse[ds]?\b",
    r"\bmalefic\b.*\bdestroy",
    r"\bterrible\b",
    r"\bdisaster\b",
    r"\birreversible\b",
    r"\bhopeless\b",
    r"\bpunishment\b",
    r"\bsuffer(ing)?\b",
]

THERAPY_SPEAK = [
    r"your feelings are valid",
    r"i'?m really sorry to hear",
    r"that must be (so |really )?hard",
    r"it'?s okay to feel",
    r"sending you (love|light|energy)",
    r"you deserve (better|more|love)",
    r"stay strong",
    r"things will get better",
    r"everything happens for a reason",
    r"trust the process",
    r"the universe has a plan",
]

GENERIC_HOROSCOPE = [
    r"today is a good day for",
    r"lucky number",
    r"lucky color",
    r"compatible signs?:",
    r"horoscope says",
    r"stars align for",
    r"cosmic energy (is |will )?bring",
    r"the universe wants you to",
    r"manifest your",
    r"abundance is coming",
    r"expect good news",
]

# Raw Jyotish terms that should be translated for the frontend
JARGON_TERMS = [
    r"\btrine\b",
    r"\bsextile\b",
    r"\bin opposition\b",  # "opposition" alone is common English; "in opposition" is astro
    r"\bplanetary conjunction\b",  # "conjunction" alone is common English
    r"\bsquare aspect\b",  # "square" alone is common English; "square aspect" is astro
    r"\blagna\b",
    r"\bbhava\b",
    r"\bgraha\b",
    r"\brashi\b",
    r"\bdrishti\b",
    r"\bavastha\b",
    r"\bdigbala\b",
    r"\bshadbala\b",
    r"\bvimshottari\b",
    r"\bmahadasha\b",
    r"\bantardasha\b",
    r"\bpratyantar\b",
    r"\bgochar\b",
    r"\bashtakavarga\b",
    r"\byoga\b(?! (mat|class|practice|studio))",  # allow casual yoga
    r"\bkuja dosha\b",
    r"\bmangal dosha\b",
    r"\bkaal sarp\b",
    r"\bsade ?sati\b",
]

RED_LINE_PATTERNS = [
    r"\bdeath\b",
    r"\bdie\b",
    r"\bdying\b",
    r"\bkill\b",
    r"\bsuicid",
    r"\bcurse\b",
    r"\bblack magic\b",
    r"\bevil eye\b",
    r"\bsoulmate certainty\b",
    r"\byour soulmate is\b",
    r"\bdestined partner\b",
    r"\bfated love\b",
    r"\byou will (get |become )?(pregnant|sick|ill)\b",
    r"\byou will have \d+ child",
    r"\bdiagnos(e[ds]?|is|tic)\b",
    r"\bdepression\b",
    r"\banxiety disorder\b",
    r"\bmental illness\b",
    r"\bcancer (treatment|patient|cell|tumor|diagnos|screen)",  # disease context only, not zodiac Cancer
    r"\bheart attack\b",
    r"\bdiabetes\b",
]

ROBOTIC_PATTERNS = [
    r"as an ai\b",
    r"as a language model",
    r"i don'?t have (personal )?(feelings|emotions|opinions)",
    r"i'?m (just )?a (computer|bot|machine|program)",
]


# ── Guard implementation ───────────────────────────────────────────

class AstroStyleGuard:
    """
    Single-pass style guard for generated readings.
    Returns violations found — the caller decides whether to retry.
    """

    def check(
        self,
        output: dict,
        surface: str = "",
        input_data: dict | None = None,
    ) -> list[Violation]:
        """
        Check all text fields in the output dict for violations.

        Args:
            output: The generated reading as a dict
            surface: Surface name for context
            input_data: Optional input data dict — used for specificity check

        Returns list of Violation objects.
        """
        violations = []

        # Flatten: handle nested structures (like mandala_cards.cards[])
        flat_fields = self._flatten(output)

        # Premium surfaces may use some Sanskrit terms (yoga, nakshatra names)
        # when they are being explained/translated in context.
        premium_surfaces = {"birth_chart_core", "union_deep_read", "mandala_deep_read"}

        for field_name, text in flat_fields.items():
            if not isinstance(text, str):
                continue

            violations += self._check_field(field_name, text, surface in premium_surfaces)

        # Specificity check: does the reading reference the member's actual chart?
        if input_data:
            violations += self._check_specificity(flat_fields, input_data, surface)

        return violations

    def has_critical(self, violations: list[Violation]) -> bool:
        return any(v.severity == "critical" for v in violations)

    def has_retry_worthy(self, violations: list[Violation]) -> bool:
        """Determine if any violations warrant a retry.

        LOW_SPECIFICITY is only retry-worthy at 'critical' severity (long-form surfaces).
        For short-form surfaces it stays a warning -- the LLM physically cannot echo
        anchor phrases in 55-100 words of poetic output.
        """
        hard_retry_types = {
            ViolationType.JARGON_LEAKAGE,
            ViolationType.EM_DASH,
            ViolationType.RED_LINE,
            ViolationType.ROBOTIC,
        }
        for v in violations:
            if v.severity == "critical":
                return True
            if v.type in hard_retry_types:
                return True
        return False

    def _check_field(self, field_name: str, text: str, is_premium: bool = False) -> list[Violation]:
        violations = []
        text_lower = text.lower()

        # Deterministic language
        for pattern in DETERMINISTIC_PATTERNS:
            if re.search(pattern, text_lower):
                violations.append(Violation(
                    type=ViolationType.DETERMINISTIC,
                    field_name=field_name,
                    detail=f"Deterministic language: '{re.search(pattern, text_lower).group()}'",
                    severity="warning",
                ))
                break

        # Fear-inducing
        for pattern in FEAR_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                # Allow negated fear words ("not punishment", "never suffering")
                start = match.start()
                prefix = text_lower[max(0, start - 12):start].strip()
                if any(prefix.endswith(neg) for neg in ("not", "never", "without", "beyond", "no")):
                    continue
                violations.append(Violation(
                    type=ViolationType.FEAR_INDUCING,
                    field_name=field_name,
                    detail=f"Fear language: '{match.group()}'",
                    severity="warning",
                ))
                break

        # Therapy-speak
        for pattern in THERAPY_SPEAK:
            if re.search(pattern, text_lower):
                violations.append(Violation(
                    type=ViolationType.THERAPY_SPEAK,
                    field_name=field_name,
                    detail=f"Therapy-speak: '{re.search(pattern, text_lower).group()}'",
                    severity="warning",
                ))
                break

        # Generic horoscope filler
        for pattern in GENERIC_HOROSCOPE:
            if re.search(pattern, text_lower):
                violations.append(Violation(
                    type=ViolationType.GENERIC_HOROSCOPE,
                    field_name=field_name,
                    detail=f"Generic horoscope: '{re.search(pattern, text_lower).group()}'",
                    severity="warning",
                ))
                break

        # Jargon leakage (only flag if no translation nearby)
        # Premium surfaces (birth chart, deep reads) are allowed to use certain
        # Sanskrit terms like "yoga" when explaining them in context.
        premium_allowed = {r"\byoga\b(?! (mat|class|practice|studio))"}
        for pattern in JARGON_TERMS:
            if is_premium and pattern in premium_allowed:
                continue
            match = re.search(pattern, text_lower)
            if match:
                term = match.group()
                # Allow if it appears in quotes, parentheses, or with a dash/colon
                # (likely being defined/translated)
                context_window = text_lower[max(0, match.start()-40):match.end()+40]
                if any(c in context_window for c in ('(', '"', '\u2014', ' -- ', ': ')):
                    continue
                violations.append(Violation(
                    type=ViolationType.JARGON_LEAKAGE,
                    field_name=field_name,
                    detail=f"Untranslated jargon: '{term}'",
                    severity="warning",
                ))
                break

        # Red lines (CRITICAL)
        for pattern in RED_LINE_PATTERNS:
            if re.search(pattern, text_lower):
                violations.append(Violation(
                    type=ViolationType.RED_LINE,
                    field_name=field_name,
                    detail=f"Red line violation: '{re.search(pattern, text_lower).group()}'",
                    severity="critical",
                ))
                break

        # Robotic tells
        for pattern in ROBOTIC_PATTERNS:
            if re.search(pattern, text_lower):
                violations.append(Violation(
                    type=ViolationType.ROBOTIC,
                    field_name=field_name,
                    detail=f"Robotic language: '{re.search(pattern, text_lower).group()}'",
                    severity="critical",
                ))
                break

        # Exclamation overuse
        excl_count = text.count("!")
        if excl_count > 1:
            violations.append(Violation(
                type=ViolationType.EXCLAMATION_HEAVY,
                field_name=field_name,
                detail=f"{excl_count} exclamation marks",
                severity="warning",
            ))

        # Em dash usage (both em dash U+2014 and en dash U+2013 used as em dash)
        em_dash_count = text.count("\u2014") + text.count(" \u2013 ")
        if em_dash_count > 0:
            violations.append(Violation(
                type=ViolationType.EM_DASH,
                field_name=field_name,
                detail=f"{em_dash_count} em dash(es) found",
                severity="warning",
            ))

        return violations

    def _check_specificity(
        self,
        flat_fields: dict[str, str],
        input_data: dict,
        surface: str,
    ) -> list[Violation]:
        """
        Check that the reading stays meaningfully anchored to this chart.

        Unlike the first version of this guard, this does NOT require the output to
        leak raw chart markers like sign names or dasha labels. It looks first for
        translated anchors supplied in the input payload, and only then uses raw
        markers as secondary evidence.
        """
        violations = []

        all_text = " ".join(flat_fields.values()).lower()
        if not all_text.strip():
            return violations

        translated_anchors = self._collect_translated_anchors(input_data)
        matched_anchors = [a for a in translated_anchors if self._anchor_matches(a, all_text)]

        raw_markers = self._collect_raw_markers(input_data)
        raw_hits = {m for m in raw_markers if m in all_text}

        # Short-form surfaces (< 100 words total) get lower thresholds --
        # you can't echo many anchors in 55-100 words of poetic output.
        # Long-form surfaces need more evidence of chart grounding.
        min_anchor_thresholds = {
            "now_collapsed": 1,
            "now_expanded": 1,
            "mandala_cards": 1,
            "mandala_deep_read": 2,
            "union_snapshot": 1,
            "union_deep_read": 2,
            "birth_chart_core": 3,
            "weekly_overview": 1,
            "monthly_overview": 1,
            "chart_reveal": 1,
        }
        threshold = min_anchor_thresholds.get(surface, 1)

        enough_translated = len(matched_anchors) >= threshold
        enough_raw = len(raw_hits) >= max(1, threshold)

        if not enough_translated and not enough_raw:
            missing_sample = [a[:80] + ("..." if len(a) > 80 else "") for a in translated_anchors[:3]]
            detail = (
                f"Only {len(matched_anchors)} translated anchor(s) matched and {len(raw_hits)} raw marker(s) matched. "
                f"Expected at least {threshold} translated anchors for {surface}. "
                f"Missing examples: {', '.join(missing_sample)}"
            )
            violations.append(Violation(
                type=ViolationType.LOW_SPECIFICITY,
                field_name="(whole reading)",
                detail=detail,
                severity="warning",
            ))

        return violations

    def _collect_translated_anchors(self, input_data: dict) -> list[str]:
        user = input_data.get("user", {}) or {}
        today = input_data.get("today", {}) or {}
        partner = input_data.get("partner", {}) or {}

        anchors = []
        for value in [
            user.get("natal_signature_summary"),
            user.get("current_chapter_summary"),
            today.get("today_focus_summary"),
        ]:
            if value:
                anchors.append(value)

        anchors.extend(user.get("interpretive_anchors") or [])
        anchors.extend(user.get("dominant_themes") or [])
        for value in [
            user.get("reasoning_hierarchy_summary"),
            user.get("conflict_resolution_summary"),
            user.get("confidence_summary"),
            user.get("navamsha_summary"),
            user.get("panchanga_birth_summary"),
            (today.get("panchanga") or {}).get("translated_summary"),
            input_data.get("relationship_summary"),
            input_data.get("period_focus_summary"),
        ]:
            if value:
                anchors.append(value)
        anchors.extend(today.get("active_life_areas") or [])
        anchors.extend(today.get("interpretive_anchors") or [])
        for window in today.get("timing_windows") or []:
            if window.get("note"):
                anchors.append(window["note"])
        for window in input_data.get("key_windows") or []:
            if window.get("note"):
                anchors.append(window["note"])

        if partner.get("current_chapter_summary"):
            anchors.append(partner["current_chapter_summary"])
        if partner.get("natal_signature_summary"):
            anchors.append(partner["natal_signature_summary"])
        anchors.extend(partner.get("dominant_themes") or [])
        anchors.extend(partner.get("interpretive_anchors") or [])
        anchors.extend(input_data.get("shared_growth_edges") or [])

        # Deduplicate while preserving order
        out = []
        seen = set()
        for anchor in anchors:
            key = anchor.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(anchor)
        return out

    def _collect_raw_markers(self, input_data: dict) -> set[str]:
        markers = set()
        user = input_data.get("user", {}) or {}
        moon = user.get("natal_moon", {}) or {}
        dasha = user.get("dasha", {}) or {}
        today = input_data.get("today", {}) or {}
        today_moon = today.get("moon", {}) or {}
        partner = input_data.get("partner", {}) or {}

        for value in [moon.get("sign"), moon.get("nakshatra"), dasha.get("mahadasha"), dasha.get("antardasha")]:
            if value:
                markers.add(str(value).lower())

        for value in [today_moon.get("sign"), today_moon.get("nakshatra")]:
            if value:
                markers.add(str(value).lower())

        lagna = user.get("lagna", {}) or {}
        if lagna.get("sign"):
            markers.add(str(lagna["sign"]).lower())

        for planet in (user.get("planets") or []):
            if planet.get("planet"):
                markers.add(str(planet["planet"]).lower())

        for transit in today.get("significant_transits", []):
            if transit.get("planet"):
                markers.add(str(transit["planet"]).lower())

        partner_moon = (partner.get("natal_moon") or {})
        if partner_moon.get("sign"):
            markers.add(str(partner_moon["sign"]).lower())

        return markers

    def _anchor_matches(self, anchor: str, all_text: str) -> bool:
        anchor_lower = anchor.lower()
        if anchor_lower in all_text:
            return True

        tokens = [t for t in re.findall(r"[a-z']+", anchor_lower) if len(t) >= 4 and t not in self._stopwords()]
        if not tokens:
            return False

        unique = set(tokens)
        matched = sum(1 for token in unique if token in all_text)

        # Fuzzy matching: for short outputs (chart_reveal, now_collapsed),
        # even 1-2 keyword hits from an anchor is meaningful.
        # For longer anchors (5+ keywords), require ~30% hit rate.
        if len(unique) <= 2:
            return matched >= 1
        elif len(unique) <= 5:
            return matched >= 2
        else:
            return matched >= max(2, len(unique) // 3)

    def _stopwords(self) -> set[str]:
        return {
            "this", "that", "with", "from", "into", "your", "their", "around", "through",
            "also", "been", "have", "more", "some", "than", "them", "they", "very", "will",
            "about", "while", "where", "what", "which", "when", "does", "each",
            "summary", "focus", "level", "present", "theme", "tone", "style",
            "chart", "person", "member",
        }

    def _flatten(self, obj: dict, prefix: str = "") -> dict[str, str]:
        """Flatten nested dicts/lists into field_name → text pairs."""
        flat = {}
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, str):
                flat[full_key] = value
            elif isinstance(value, dict):
                flat.update(self._flatten(value, full_key))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        flat.update(self._flatten(item, f"{full_key}[{i}]"))
                    elif isinstance(item, str):
                        flat[f"{full_key}[{i}]"] = item
        return flat
