"""
Astro LLM configuration — model routing, paths, constants.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # astro_app/
PROMPT_PACK = PROJECT_ROOT / "1.0"
CORE_PROMPTS_DIR = PROMPT_PACK / "prompts" / "core"
FEATURE_PROMPTS_DIR = PROMPT_PACK / "prompts" / "features"


# ── Model tiers ────────────────────────────────────────────────────
class ModelTier(str, Enum):
    DAILY = "daily"       # fast, cheap — daily surfaces
    STANDARD = "standard" # balanced — most reads
    PREMIUM = "premium"   # deep — birth chart, union deep read


TIER_TO_MODEL: dict[ModelTier, str] = {
    ModelTier.DAILY: os.getenv("MODEL_DAILY", "claude-haiku-4-5-20251001"),
    ModelTier.STANDARD: os.getenv("MODEL_STANDARD", "claude-sonnet-4-6"),
    ModelTier.PREMIUM: os.getenv("MODEL_PREMIUM", "claude-opus-4-6"),
}


# ── Surface → model routing ───────────────────────────────────────
class Surface(str, Enum):
    NOW_COLLAPSED = "now_collapsed"
    NOW_EXPANDED = "now_expanded"
    MANDALA_CARDS = "mandala_cards"
    MANDALA_DEEP_READ = "mandala_deep_read"
    UNION_SNAPSHOT = "union_snapshot"
    UNION_DEEP_READ = "union_deep_read"
    BIRTH_CHART_CORE = "birth_chart_core"
    WEEKLY_OVERVIEW = "weekly_overview"
    MONTHLY_OVERVIEW = "monthly_overview"
    CHART_REVEAL = "chart_reveal"


SURFACE_TO_TIER: dict[Surface, ModelTier] = {
    Surface.NOW_COLLAPSED: ModelTier.DAILY,
    Surface.NOW_EXPANDED: ModelTier.DAILY,
    Surface.MANDALA_CARDS: ModelTier.STANDARD,
    Surface.MANDALA_DEEP_READ: ModelTier.STANDARD,
    Surface.UNION_SNAPSHOT: ModelTier.STANDARD,
    Surface.UNION_DEEP_READ: ModelTier.PREMIUM,
    Surface.BIRTH_CHART_CORE: ModelTier.PREMIUM,
    Surface.WEEKLY_OVERVIEW: ModelTier.STANDARD,
    Surface.MONTHLY_OVERVIEW: ModelTier.STANDARD,
    Surface.CHART_REVEAL: ModelTier.STANDARD,
}

# Feature prompt file mapping
SURFACE_TO_PROMPT_FILE: dict[Surface, str] = {
    Surface.NOW_COLLAPSED: "now_collapsed.txt",
    Surface.NOW_EXPANDED: "now_expanded.txt",
    Surface.MANDALA_CARDS: "mandala_cards.txt",
    Surface.MANDALA_DEEP_READ: "mandala_deep_read.txt",
    Surface.UNION_SNAPSHOT: "union_snapshot.txt",
    Surface.UNION_DEEP_READ: "union_deep_read.txt",
    Surface.BIRTH_CHART_CORE: "birth_chart_core.txt",
    Surface.WEEKLY_OVERVIEW: "weekly_overview.txt",
    Surface.MONTHLY_OVERVIEW: "monthly_overview.txt",
    Surface.CHART_REVEAL: "chart_reveal.txt",
}


# ── Max tokens per surface ─────────────────────────────────────────
SURFACE_MAX_TOKENS: dict[Surface, int] = {
    Surface.NOW_COLLAPSED: 300,
    Surface.NOW_EXPANDED: 600,
    Surface.MANDALA_CARDS: 1200,
    Surface.MANDALA_DEEP_READ: 500,
    Surface.UNION_SNAPSHOT: 400,
    Surface.UNION_DEEP_READ: 1500,
    Surface.BIRTH_CHART_CORE: 12000,  # Sacred life study: nested yogas, forces, timing, phases
    Surface.WEEKLY_OVERVIEW: 800,
    Surface.MONTHLY_OVERVIEW: 1000,
    Surface.CHART_REVEAL: 300,
}


def get_model(surface: Surface) -> str:
    """Return the model ID for a given surface."""
    tier = SURFACE_TO_TIER[surface]
    return TIER_TO_MODEL[tier]


def get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
    return key
