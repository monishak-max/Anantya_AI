# Team handoff for v1.4

This update is the first pass that turns Anantya from a better-written astrology product into a more coherent astrologer mind.

## What changed conceptually
1. The model now receives explicit hierarchy guidance instead of a flatter chart payload.
2. Yogas are treated as weighted and activation-aware, not as decorative labels.
3. Remedies and gemstones can now be passed in as optional modifiers without being allowed to dominate the reading.
4. Navamsha and panchanga now have a more meaningful internal role.
5. Union and period surfaces are structurally richer and less underpowered.

## What the team should QA live
- Does chart reveal stay piercing without becoming generic or flattering?
- Do birth chart sections feel unified by a single life logic?
- Does the dasha chapter clearly outrank day-level transit weather?
- Do yoga mentions feel earned and translated?
- If modifier context is passed, does the model treat it as secondary rather than as the main explanation?
- Do weekly and monthly surfaces feel like real horizons instead of stitched daily notes?

## Suggested next implementation pass after live QA
- tighten prompt language on any surfaces that still drift toward feel-good copy
- add fuller synastry-specific bridge data if union deep read still feels underpowered
- add stronger confidence scoring if the model still overstates mixed charts
