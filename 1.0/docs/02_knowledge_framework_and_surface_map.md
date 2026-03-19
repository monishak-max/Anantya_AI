# Document 2: Knowledge Framework and Product Surface Map

## Purpose
Define how the astrology systems work together, what each system is allowed to influence, what remains internal vs member-facing, and how those systems map onto the product surfaces: Now, Mandala, Union, and the deeper premium reads.

---

# Part I: The knowledge stack

## 1. Jyotish
**Role:** Primary astrology engine

### Internal job
- Determine core pattern, placement logic, timing, activation, house emphasis, graha influence, sign context, aspect dynamics, and natal structure.
- Power all chart-based precision.

### May influence member-facing output
- yes, heavily

### Best used for
- daily astro signature
- current activations
- weekly/monthly timing
- natal readings
- compatibility foundations

### Internal components
- lagna
- moon sign
- grahas
- bhavas
- rashis
- nakshatras
- yogas
- dashas / antardashas
- transits / gochar
- divisional charts where premium depth is appropriate

---

## 2. Nakshatra layer
**Role:** Soul texture and subtle emotional layer

### Internal job
- Add nuance, intimacy, and spiritual-psychological depth.
- Refine tone, sensitivity, instinct, desire patterns, and relational signatures.

### May influence member-facing output
- yes, often translated rather than named

### Best used for
- emotional tone in Now
- Mandala card language
- natal soul patterning
- Union chemistry and subtle bond quality

### Frontend note
Use sparingly in free surfaces. Use more explicitly in premium readings.

---

## 3. Dasha systems
**Role:** Life chapter and karmic timing layer

### Internal job
- Explain why a theme is ripening now.
- Differentiate passing weather from a larger chapter.

### May influence member-facing output
- yes, especially in premium and period-based reads

### Best used for
- monthly overviews
- Mandala prioritization
- birth chart timing narratives
- compatibility chapters when relationship timing matters

### Frontend note
Avoid raw technical exposition in short surfaces. Translate into chapter language such as:
- a season of consolidation
- a chapter of visibility
- a chapter of emotional restructuring

---

## 4. Gochar / transits
**Role:** Present-moment weather layer

### Internal job
- Detect what is active right now or in the selected period.

### May influence member-facing output
- yes, directly

### Best used for
- Now
- Mandala cards
- weekly overview
- monthly overview

### Frontend note
This is the main engine for immediacy.

---

## 5. Dharma
**Role:** Ethical compass

### Internal job
- Determine the wisest orientation, not just the likely pattern.
- Convert astrology into right relationship with life.

### May influence member-facing output
- yes, but often as guidance rather than as the word “dharma” itself

### Best used for
- action prompts
- reflection prompts
- guidance language
- closing orientation in deeper reads

### Frontend note
This is a core hidden spine of the product. It should shape the voice even when unnamed.

---

## 6. Karma
**Role:** Pattern and consequence layer

### Internal job
- Explain recurrence, inherited tendencies, meaningful friction, and ripening themes.

### May influence member-facing output
- yes, but with care

### Best used for
- natal chart growth edges
- Union bond meaning
- deep-read explanations of recurring life patterns

### Frontend note
Never use karma as punishment language.

---

## 7. Gunas
**Role:** State-of-consciousness layer

### Internal job
- Classify inner tone: clarity, restlessness, heaviness, receptivity, inertia, expansion.

### May influence member-facing output
- yes, mostly as psychological translation

### Best used for
- resistance sections
- emotional weather
- guidance tone
- daily reflection prompts

### Frontend note
Usually translate rather than label.
For example:
- not “tamas is high”
- but “the pull may be toward numbness or delay”

---

## 8. Purusharthas
**Role:** Life-aim balancing layer

### Internal job
- Identify what dimension of life is being emphasized: duty, material stability, love/pleasure, or liberation.

### May influence member-facing output
- yes, often implicitly

### Best used for
- longer overviews
- birth chart synthesis
- Mandala prioritization

### Frontend note
This is especially useful in premium interpretation and strategic overviews.

---

## 9. Spiritual psychology
**Role:** Meaning-making and inner growth layer

### Internal job
- Translate astrological signals into self-awareness, steadiness, and growth.

### May influence member-facing output
- yes, strongly

### Best used for
- reflection prompts
- resistance framing
- guidance paragraphs
- closing integration sections

### Frontend note
This is where the app feels like an Aatman spinoff rather than a horoscope machine.

---

## 10. Relational interpretation / compatibility logic
**Role:** Union layer

### Internal job
- Evaluate chart-to-chart interplay, attraction, ease, tension, emotional rhythm, value alignment, and karmic charge.

### May influence member-facing output
- yes, directly

### Best used for
- Union snapshot
- Union deep read
- compatibility upsell

### Frontend note
The narrative matters more than the score.

---

# Part II: Product surface map

## Surface 1: Now
**Purpose:** Give the member one elegant, emotionally legible thesis for the day.

### Backend inputs
- current transits
- chart-specific house impacts if user data exists
- moon state / emotional weather
- dasha relevance if significant
- guna translation for resistance / posture
- dharma for guidance

### Content blocks
- astro signature line
- headline
- support paragraph
- do today
- reflection

### Product rule
One clear signal. No clutter.

---

## Surface 2: Expanded Now
**Purpose:** Deepen the daily signal without becoming dense.

### Backend inputs
- same as Now, but with fuller interpretation

### Content blocks
- opening paragraph
- what this means
- possible resistance
- wise posture / movement
- optional anchor line

### Product rule
This should feel like a deeper breath, not a report.

---

## Surface 3: Mandala cards
**Purpose:** Show the member’s top active influences as short premium cards.

### Backend inputs
- strongest current transits
- current house activations
- dasha-chapter relevance
- natal sensitivity points
- time-window weighting

### Content blocks per card
- activation title
- time window
- one-line theme
- short explanation
- optional CTA / read more

### Product rule
Each card should feel like translated astrology, not raw astrology.

---

## Surface 4: Mandala deep read
**Purpose:** Expand one activation into a richer but still elegant interpretation.

### Backend inputs
- detailed transit / dasha / natal interaction data
- house / graha / nakshatra nuance
- purushartha emphasis
- dharmic guidance

### Content blocks
- title
- activation summary
- life area explanation
- likely emotional expression
- guidance / timing advice

### Product rule
Readable in under a minute.

---

## Surface 5: Union snapshot
**Purpose:** Give a beautiful first read of the bond between two people.

### Backend inputs
- compatibility layer
- emotional rhythm
- communication fit
- karmic pull
- practical harmony / friction

### Content blocks
- one-line bond summary
- emotional dynamic
- one core support
- one core friction
- invitation to explore deeper

### Product rule
Human and intimate, never transactional.

---

## Surface 6: Union deep read
**Purpose:** Deliver a fuller compatibility / influence interpretation.

### Backend inputs
- traditional compatibility signals
- chart interplay
- nakshatra interplay
- karmic and emotional patterning
- long-term influence themes

### Content blocks
- overall dynamic
- emotional rhythm
- communication
- affection / attraction
- values and life path fit
- friction zones
- karmic lesson
- growth potential
- guidance

### Product rule
Do not reduce this to a match score.

---

## Surface 7: Birth chart core
**Purpose:** Provide a modern Janam Patri for the member.

### Backend inputs
- full natal structure
- house/sign/planet analysis
- nakshatra nuance
- dasha orientation
- dharma / karma / purushartha synthesis

### Content blocks
- essence
- temperament
- emotional nature
- relationships
- vocation
- blessings
- growth edges
- spiritual orientation
- integration

### Product rule
Modern expression, traditional depth.

---

## Surface 8: Weekly / monthly overview
**Purpose:** Give a strategic view of the coming period.

### Backend inputs
- major transits
- dasha chapter weighting
- period priorities
- likely life themes
- guidance orientation

### Content blocks
- opening summary
- top themes
- work / purpose
- relationships
- inner state
- timing notes
- guidance

### Product rule
This should feel broader and more strategic than Now.

---

# Part III: Member-facing vs internal-only guidance

## Usually internal-only
- raw graha/bhava mechanics in short-form surfaces
- technical dasha labels in casual reads
- heavy Sanskrit terminology when not necessary
- low-confidence micro-prediction
- deterministic logic paths

## Sometimes member-facing
- karma
- dharma
- nakshatra
- Jyotish

## More acceptable in premium depth
- grahas
- bhavas
- dashas
- lagna
- nakshatra names
- selected yogas
- divisional references

---

# Part IV: Global audience translation layer

## Principle
Ancient source, modern expression.

## Delivery rules
- beauty first
- clarity second
- depth over time
- no cultural gatekeeping
- no overloading the user with Sanskrit early
- do not sound like a textbook or temple pamphlet

## Preferred frontend language
Use words like:
- energy
- timing
- season
- rhythm
- readiness
- transition
- grounding
- emotional weather
- alignment
- visibility
- soft pressure
- opening
- closure

## Terms to pace carefully
- karma
- dharma
- nakshatra
- Jyotish
- dasha
- guna
- purushartha

## Tone rule
The user should never feel they need prior Hindu knowledge to feel the wisdom.

---

# Part V: Final operating principle
The member should not feel they are reading many systems.
They should feel one beautiful intelligence.

Backend: layered, Sanskritic, precise.
Frontend: modern, elegant, uplifting, emotionally clear.
