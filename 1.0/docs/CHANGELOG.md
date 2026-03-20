# v1.4 code update changelog

## Core prompt system
- Rewrote the 5 core prompts to encode the gold-standard reasoning hierarchy.
- Added explicit handling rules for yogas, remedies, gemstones, modifiers, and conflict resolution.
- Sharpened Anantya's persona so it reads like a serious astrologer translated into refined modern language.
- Removed em dashes from the prompt pack.

## Input schemas
- Added hidden reasoning fields to `UserProfile` for dominant themes, hierarchy summary, conflict summary, confidence summary, navamsha summary, and birth panchanga summary.
- Added `ContextModifier` to support optional remedies, gemstones, life-stage context, maturity, and environmental modifiers.
- Added `PanchangaContext` and `PeriodWindow` for translated timing texture.
- Extended `PlanetPlacement` with `navamsha_sign`.
- Extended `YogaInfo` with strength, activation status, and relevance.
- Enriched `UnionInput` and `PeriodOverviewInput` with deeper internal context.

## Bridge layer
- Rebuilt bridge summaries so the model receives chart hierarchy rather than raw factor sprawl.
- Added translated dominant themes, hierarchy summary, conflict-resolution summary, confidence summary, navamsha summary, and panchanga summaries.
- Added yoga evaluation heuristics for strength and activation status.
- Added optional external modifier coercion and pass-through.
- Added richer relationship summary and growth-edge inputs for union surfaces.
- Fixed weekly/monthly overview construction by providing `period_start`, `period_end`, `period_focus_summary`, and `key_windows`.

## Pipeline
- Added optional `external_modifiers` to all generation methods.
- Updated cache keys to account for modifiers and deeper surface payloads.
- Updated weekly/monthly generation to pass the correct target date into the bridge.
- Updated union deep read to use the deeper input mode.
- Extended chart summary output with `navamsha_sign`.

## Style guard
- Restored a light but real specificity requirement for chart reveal.
- Expanded anchor collection to use dominant themes, hierarchy summaries, panchanga summaries, period focus notes, key windows, relationship summaries, and shared growth edges.

## Web layer
- Added endpoints for mandala deep read, union deep read, weekly overview, and monthly overview.
- Added pass-through support for `external_modifiers` in API payloads.

## Package hygiene
- Removed `.env`, `.cache`, and `__pycache__` from the prepared package.
- Removed the stale `Anantya_v1.3_Test_Report.pdf` from the prepared package.

- added present -> past -> future chart-language framework so birth chart readings begin from the member's life now, then trace roots and future arc
- added hidden input summaries for present-centered framing, past patterning, and future arc
- tightened birth-chart prompt and schema guidance to avoid static birth-time narration
