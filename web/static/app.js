/* ═══════════════════════════════════════════════════════════════
   Astro Web — Frontend Logic
   ═══════════════════════════════════════════════════════════════ */

// ── State ─────────────────────────────────────────────────────
let userData = null;   // { name, birth_date, birth_time, lat, lng }
let chartData = null;  // chart summary from /api/chart
let nowData = null;    // { collapsed, expanded }
let mandalaData = null;
let unionData = null;

const SIGNS = [
  'ARIES','TAURUS','GEMINI','CANCER','LEO','VIRGO',
  'LIBRA','SCORPIO','SAGITTARIUS','CAPRICORN','AQUARIUS','PISCES'
];

// ── Screens ───────────────────────────────────────────────────
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

// ── Onboarding Steps ──────────────────────────────────────────
function showStep(n) {
  document.querySelectorAll('.ob-step').forEach(s => s.classList.remove('active'));
  const step = document.querySelector(`.ob-step[data-step="${n}"]`);
  if (step) step.classList.add('active');
}

document.getElementById('btn-step1').addEventListener('click', () => {
  showStep(2);
  // Initialize time picker after step becomes visible
  setTimeout(initTimePicker, 50);
});
document.getElementById('btn-step2').addEventListener('click', () => showStep(3));
document.getElementById('btn-unsure-time').addEventListener('click', () => {
  document.getElementById('ob-time').value = '12:00';
  // Snap picker to 12:00 PM visually
  const hourCol = document.getElementById('tp-hour');
  const minuteCol = document.getElementById('tp-minute');
  const ampmCol = document.getElementById('tp-ampm');
  scrollToValue(hourCol, '12');
  scrollToValue(minuteCol, '0');
  scrollToValue(ampmCol, 'PM');
  showStep(3);
});

// ── iOS-style Time Picker ─────────────────────────────────
function initTimePicker() {
  const hourCol = document.getElementById('tp-hour');
  const minuteCol = document.getElementById('tp-minute');
  const ampmCol = document.getElementById('tp-ampm');

  if (hourCol.children.length > 0) return; // already initialized

  // Build hour items (1-12)
  for (let h = 1; h <= 12; h++) {
    const item = document.createElement('div');
    item.className = 'tp-item';
    item.textContent = h;
    item.dataset.value = h;
    hourCol.appendChild(item);
  }

  // Build minute items (00-59)
  for (let m = 0; m <= 59; m++) {
    const item = document.createElement('div');
    item.className = 'tp-item';
    item.textContent = String(m).padStart(2, '0');
    item.dataset.value = m;
    minuteCol.appendChild(item);
  }

  // Build AM/PM
  ['AM', 'PM'].forEach(p => {
    const item = document.createElement('div');
    item.className = 'tp-item';
    item.textContent = p;
    item.dataset.value = p;
    ampmCol.appendChild(item);
  });

  // Setup scroll snap detection for each column
  [hourCol, minuteCol, ampmCol].forEach(col => {
    col.addEventListener('scroll', () => handlePickerScroll(col));
    // Click to scroll to item
    col.querySelectorAll('.tp-item').forEach(item => {
      item.addEventListener('click', () => {
        item.scrollIntoView({ block: 'center', behavior: 'smooth' });
      });
    });
  });

  // Default to 8:00 PM (matching wireframe)
  setTimeout(() => {
    scrollToValue(hourCol, '8');
    scrollToValue(minuteCol, '0');
    scrollToValue(ampmCol, 'PM');
    updateTimeInput();
  }, 100);
}

function scrollToValue(col, val) {
  const items = col.querySelectorAll('.tp-item');
  items.forEach(item => item.classList.remove('selected'));
  for (const item of items) {
    if (item.dataset.value === val) {
      item.scrollIntoView({ block: 'center', behavior: 'instant' });
      item.classList.add('selected');
      break;
    }
  }
}

function handlePickerScroll(col) {
  clearTimeout(col._scrollTimer);
  col._scrollTimer = setTimeout(() => {
    const items = col.querySelectorAll('.tp-item');
    const colRect = col.getBoundingClientRect();
    const centerY = colRect.top + colRect.height / 2;

    let closest = null;
    let closestDist = Infinity;

    items.forEach(item => {
      const itemRect = item.getBoundingClientRect();
      const itemCenter = itemRect.top + itemRect.height / 2;
      const dist = Math.abs(itemCenter - centerY);
      if (dist < closestDist) {
        closestDist = dist;
        closest = item;
      }
    });

    // Update selected styling
    items.forEach(item => item.classList.remove('selected'));
    if (closest) {
      closest.classList.add('selected');
      updateTimeInput();
    }
  }, 60);
}

function updateTimeInput() {
  const hourEl = document.querySelector('#tp-hour .tp-item.selected');
  const minEl = document.querySelector('#tp-minute .tp-item.selected');
  const ampmEl = document.querySelector('#tp-ampm .tp-item.selected');

  if (!hourEl || !minEl || !ampmEl) return;

  let hour = parseInt(hourEl.dataset.value);
  const minute = parseInt(minEl.dataset.value);
  const ampm = ampmEl.dataset.value;

  // Convert to 24h for the hidden input
  if (ampm === 'AM' && hour === 12) hour = 0;
  else if (ampm === 'PM' && hour !== 12) hour += 12;

  const timeStr = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
  document.getElementById('ob-time').value = timeStr;
}

// ── Geocoding (place → lat/lng) ──────────────────────────────
function setupGeocode(placeId, latId, lngId) {
  const placeInput = document.getElementById(placeId);
  if (!placeInput) return;

  let timer = null;
  let dropdown = null;

  function removeDropdown() {
    if (dropdown) { dropdown.remove(); dropdown = null; }
  }

  placeInput.addEventListener('input', () => {
    clearTimeout(timer);
    const q = placeInput.value.trim();
    if (q.length < 3) { removeDropdown(); return; }

    timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/geocode?q=${encodeURIComponent(q)}`);
        const json = await res.json();
        if (!json.ok || !json.results.length) { removeDropdown(); return; }

        removeDropdown();
        dropdown = document.createElement('div');
        dropdown.className = 'geo-dropdown';
        json.results.forEach(r => {
          const item = document.createElement('div');
          item.className = 'geo-item';
          item.textContent = r.display;
          item.addEventListener('click', () => {
            placeInput.value = r.display;
            document.getElementById(latId).value = parseFloat(r.lat).toFixed(4);
            document.getElementById(lngId).value = parseFloat(r.lng).toFixed(4);
            removeDropdown();
          });
          dropdown.appendChild(item);
        });
        placeInput.parentElement.style.position = 'relative';
        placeInput.parentElement.appendChild(dropdown);
      } catch (e) { /* silently fail */ }
    }, 400);
  });

  // Close dropdown when clicking outside
  document.addEventListener('click', (e) => {
    if (!placeInput.contains(e.target) && (!dropdown || !dropdown.contains(e.target))) {
      removeDropdown();
    }
  });
}

setupGeocode('ob-place', 'ob-lat', 'ob-lng');
setupGeocode('u-place', 'u-lat', 'u-lng');

// ── Generate (final onboarding step) ──────────────────────────
document.getElementById('btn-generate').addEventListener('click', async () => {
  const btn = document.getElementById('btn-generate');
  setLoading(btn, true);

  userData = {
    name: document.getElementById('ob-name').value,
    birth_date: document.getElementById('ob-dob').value,
    birth_time: document.getElementById('ob-time').value,
    lat: document.getElementById('ob-lat').value,
    lng: document.getElementById('ob-lng').value,
  };

  if (!userData.name || !userData.birth_date || !userData.birth_time || !userData.lat || !userData.lng) {
    toast('Please fill in all fields before generating.', true);
    setLoading(btn, false);
    return;
  }

  try {
    const res = await api('/api/chart', userData);
    chartData = res.chart;
    showRevealScreen();
    // Fetch LLM-generated reveal content in background
    loadRevealContent();
  } catch (e) {
    toast('Could not compute chart: ' + e.message, true);
    setLoading(btn, false);
  }
});

// ── Reveal Screen ─────────────────────────────────────────────
function showRevealScreen() {
  const c = chartData;

  // Headline — show fallback while LLM loads
  const headlineEl = document.getElementById('reveal-headline');
  headlineEl.textContent = generateRevealHeadline(c);
  headlineEl.classList.add('reveal-loading');

  // Signs
  const signsEl = document.getElementById('reveal-signs');
  const sunSign = findSunSign(c);
  signsEl.innerHTML = `
    <span class="sign-chip">☉ ${sunSign}</span>
    <span class="sign-chip">☽ ${c.moon.sign}</span>
    <span class="sign-chip">↑ ${c.lagna_sign || c.moon.sign}</span>
  `;

  // Arrived text — show fallback while LLM loads
  const arrivedEl = document.getElementById('reveal-arrived');
  const d = new Date(userData.birth_date);
  const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  arrivedEl.textContent = `Soul arrived on ${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;

  // Traits — show fallback while LLM loads
  const traits = generateTraits(c);
  const list = document.getElementById('traits-list');
  list.innerHTML = traits.map(t => `<li>${t}</li>`).join('');
  list.classList.add('reveal-loading');

  // Draw wheel
  drawZodiacWheel('wheel-canvas', c);

  showScreen('reveal');
}

async function loadRevealContent() {
  try {
    const res = await api('/api/chart-reveal', userData);
    if (res.reveal) {
      const r = res.reveal;

      // Update headline with LLM content
      const headlineEl = document.getElementById('reveal-headline');
      headlineEl.textContent = r.headline;
      headlineEl.classList.remove('reveal-loading');
      headlineEl.classList.add('reveal-ready');

      // Update traits
      if (r.traits && r.traits.length === 3) {
        const list = document.getElementById('traits-list');
        list.innerHTML = r.traits.map(t => `<li>${t}</li>`).join('');
        list.classList.remove('reveal-loading');
        list.classList.add('reveal-ready');
      }

      // Update soul line
      if (r.soul_line) {
        const arrivedEl = document.getElementById('reveal-arrived');
        arrivedEl.textContent = r.soul_line;
      }
    }
  } catch (e) {
    // Silently keep the fallback content — no toast needed
    console.warn('Chart reveal LLM failed, using fallback:', e.message);
    document.getElementById('reveal-headline').classList.remove('reveal-loading');
    document.getElementById('traits-list').classList.remove('reveal-loading');
  }
}

function findSunSign(c) {
  if (c.planets && c.planets.Sun) return c.planets.Sun.sign;
  return c.moon.sign; // fallback
}

function generateRevealHeadline(c) {
  const moon = c.moon.sign;
  const nak = c.moon.nakshatra;
  const headlines = {
    'Capricorn': 'You are someone who builds quietly and endures deeply.',
    'Cancer': 'You are someone who feels everything and protects what matters.',
    'Scorpio': 'You are someone who sees beneath surfaces and transforms through intensity.',
    'Pisces': 'You are someone who dissolves boundaries and finds meaning in the unseen.',
    'Aries': 'You are someone who moves first and reflects later.',
    'Taurus': 'You are someone who values beauty, steadiness, and what endures.',
    'Gemini': 'You are someone who thinks in motion and speaks in layers.',
    'Leo': 'You are someone who leads through presence and feels through the heart.',
    'Virgo': 'You are someone who refines everything and serves with quiet precision.',
    'Libra': 'You are someone who seeks harmony and weighs every truth.',
    'Sagittarius': 'You are someone who reaches for meaning and refuses to stay small.',
    'Aquarius': 'You are someone who thinks ahead of their time and cares deeply in unusual ways.',
  };
  return headlines[moon] || 'You are someone who feels deeply but reveals slowly.';
}

function generateTraits(c) {
  const moon = c.moon.sign;
  const traitMap = {
    'Capricorn': ['You seek structure within depth', 'You protect what matters quietly', 'You appear steadier than you feel'],
    'Cancer': ['You nurture before you think', 'You feel the room before you enter', 'You remember what others forget'],
    'Scorpio': ['You see what others miss', 'You protect your inner world fiercely', 'You transform through letting go'],
    'Pisces': ['You absorb the world around you', 'You dream in meaning', 'You heal through presence'],
    'Aries': ['You lead through instinct', 'You move before permission', 'You burn brightest under pressure'],
    'Taurus': ['You value what lasts', 'You seek beauty in stillness', 'You ground others by your presence'],
    'Gemini': ['You process by speaking', 'You hold many truths at once', 'You adapt faster than most'],
    'Leo': ['You shine when you stop performing', 'You lead from the heart', 'You need to be truly seen'],
    'Virgo': ['You notice what others miss', 'You serve through refinement', 'You heal through understanding'],
    'Libra': ['You seek harmony', 'You protect your inner world', 'You appear softer than you are'],
    'Sagittarius': ['You follow meaning over comfort', 'You teach through experience', 'You grow by expanding'],
    'Aquarius': ['You think ahead of your time', 'You care in unconventional ways', 'You need freedom to connect'],
  };
  return traitMap[moon] || ['You feel deeply', 'You grow through challenge', 'You are learning to trust your own rhythm'];
}

// ── Explore More → Main App ───────────────────────────────────
document.getElementById('btn-explore').addEventListener('click', () => {
  showScreen('app');
  loadNow();
});

// ═══════════════════════════════════════════════════════════════
// TAB NAVIGATION
// ═══════════════════════════════════════════════════════════════

document.querySelectorAll('.btab').forEach(tab => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.tab;

    document.querySelectorAll('.btab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');

    document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
    document.getElementById(`tab-${target}`).classList.add('active');

    // Lazy load tab content
    if (target === 'now' && !nowData) loadNow();
    if (target === 'mandala' && !mandalaData) loadMandala();
  });
});

// ═══════════════════════════════════════════════════════════════
// NOW TAB
// ═══════════════════════════════════════════════════════════════

async function loadNow() {
  if (!userData) return;
  const loading = document.querySelector('.now-loading');
  const content = document.querySelector('.now-content');
  loading.style.display = 'flex';
  content.style.display = 'none';

  try {
    const res = await api('/api/now', userData);
    nowData = res;
    renderNow(res);
    loading.style.display = 'none';
    content.style.display = 'block';
  } catch (e) {
    loading.querySelector('p').textContent = 'Could not load. ' + e.message;
  }
}

function renderNow(data) {
  const c = data.collapsed;
  const e = data.expanded;

  document.getElementById('now-sig').textContent = c.astro_signature;
  document.getElementById('now-headline').textContent = c.headline;
  document.getElementById('now-support').textContent = c.support_text;
  document.getElementById('now-do-today').textContent = c.do_today;
  document.getElementById('now-reflection').textContent = `"${c.reflection}"`;

  // Expanded
  document.getElementById('exp-sig').textContent = e.astro_signature;
  document.getElementById('exp-opening').textContent = e.opening_paragraph;
  document.getElementById('exp-what-this-means').textContent = e.what_this_means_body;
  document.getElementById('exp-resistance').textContent = e.resistance_body;
  document.getElementById('exp-guidance').textContent = e.guidance_body;
  document.getElementById('exp-anchor').textContent = e.closing_anchor || '';

  // Draw sky arc
  drawSkyArc();
}

// Dive Deeper → open sheet
document.getElementById('btn-dive-deeper').addEventListener('click', () => {
  document.getElementById('expanded-overlay').style.display = 'block';
});

document.getElementById('btn-close-expanded').addEventListener('click', () => {
  document.getElementById('expanded-overlay').style.display = 'none';
});

// Close on overlay click
document.getElementById('expanded-overlay')?.addEventListener('click', (e) => {
  if (e.target.id === 'expanded-overlay') {
    document.getElementById('expanded-overlay').style.display = 'none';
  }
});

// ═══════════════════════════════════════════════════════════════
// MANDALA TAB
// ═══════════════════════════════════════════════════════════════

async function loadMandala() {
  if (!userData) return;
  const loading = document.querySelector('.mandala-loading');
  const content = document.querySelector('.mandala-content');
  loading.style.display = 'flex';
  content.style.display = 'none';

  try {
    const res = await api('/api/mandala', userData);
    mandalaData = res;
    renderMandala(res);
    loading.style.display = 'none';
    content.style.display = 'block';
  } catch (e) {
    loading.querySelector('p').textContent = 'Could not load. ' + e.message;
  }
}

function renderMandala(data) {
  // Profile header
  document.getElementById('mandala-name').textContent = userData.name;
  const sunSign = chartData?.planets?.Sun?.sign || chartData?.moon?.sign || '';
  const moonSign = chartData?.moon?.sign || '';
  document.getElementById('mandala-signs').innerHTML = `
    <span>☉ ${sunSign}</span>
    <span>☽ ${moonSign}</span>
  `;
  const d = new Date(userData.birth_date);
  const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  document.getElementById('mandala-arrived').textContent =
    `Soul arrived on ${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;

  // Draw zodiac wheel
  drawZodiacWheel('mandala-canvas', chartData);

  // Cards
  const container = document.getElementById('mandala-cards');
  container.innerHTML = '';

  const planetIcons = {
    'Saturn': '🪐', 'Jupiter': '🟠', 'Mars': '🔴', 'Rahu': '🌑',
    'Ketu': '🟤', 'Venus': '💚', 'Mercury': '🟢', 'Sun': '🟡', 'Moon': '🌙'
  };

  (data.cards || []).forEach(card => {
    const planet = extractPlanet(card.activation_marker);
    const icon = planetIcons[planet] || '✦';

    const el = document.createElement('div');
    el.className = 'mandala-card';
    el.innerHTML = `
      <div class="mc-planet-icon">${icon}</div>
      <div class="mc-marker">${card.activation_marker}</div>
      <div class="mc-title">${card.card_title}</div>
      <div class="mc-body">${card.card_body}</div>
      <span class="mc-cta" data-planet="${planet}">Explore this further</span>
    `;

    // Wire the "Explore this further" button to mandala deep read
    el.querySelector('.mc-cta').addEventListener('click', async (e) => {
      e.stopPropagation();
      const activationPlanet = e.target.dataset.planet || 'Saturn';
      await loadMandalaDeepRead(activationPlanet, card);
    });

    container.appendChild(el);
  });
}

// ── Mandala Deep Read ──────────────────────────────────────────
async function loadMandalaDeepRead(planet, card) {
  // Show overlay with loading state
  let overlay = document.getElementById('mandala-deep-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'mandala-deep-overlay';
    overlay.className = 'expanded-overlay';
    overlay.innerHTML = `
      <div class="expanded-sheet">
        <button class="btn-close-sheet" id="btn-close-mandala-deep">&times;</button>
        <div class="mandala-deep-loading" style="text-align:center;padding:40px 20px;">
          <div class="loader"></div>
          <p style="margin-top:16px;color:#888;">Exploring this activation...</p>
        </div>
        <div class="mandala-deep-content" style="display:none;"></div>
      </div>
    `;
    document.body.appendChild(overlay);

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.style.display = 'none';
    });
    document.getElementById('btn-close-mandala-deep').addEventListener('click', () => {
      overlay.style.display = 'none';
    });
  }

  // Reset and show
  overlay.querySelector('.mandala-deep-loading').style.display = 'block';
  overlay.querySelector('.mandala-deep-content').style.display = 'none';
  overlay.style.display = 'block';

  try {
    const payload = {
      ...userData,
      activation_planet: planet,
    };
    const res = await api('/api/mandala-deep', payload);
    const d = res.deep_read;

    const content = overlay.querySelector('.mandala-deep-content');
    content.innerHTML = `
      <div class="deep-section">
        <h2 class="deep-title">${d.title || ''}</h2>
        <p class="deep-activation">${d.activation_summary || ''}</p>
      </div>
      <div class="deep-section">
        <div class="deep-label">Where this lands in your life</div>
        <p>${d.life_area_section || ''}</p>
      </div>
      <div class="deep-section">
        <div class="deep-label">How it may feel</div>
        <p>${d.inner_expression_section || ''}</p>
      </div>
      <div class="deep-section">
        <div class="deep-label">How to move with this</div>
        <p>${d.guidance_section || ''}</p>
      </div>
      ${d.time_note ? `<div class="deep-section"><div class="deep-label">Timing</div><p class="deep-timing">${d.time_note}</p></div>` : ''}
    `;

    overlay.querySelector('.mandala-deep-loading').style.display = 'none';
    content.style.display = 'block';
  } catch (err) {
    overlay.querySelector('.mandala-deep-loading').innerHTML =
      `<p style="color:#c44;">Could not load: ${err.message}</p>`;
  }
}

function extractPlanet(marker) {
  const planets = ['Saturn', 'Jupiter', 'Mars', 'Rahu', 'Ketu', 'Venus', 'Mercury', 'Sun', 'Moon'];
  for (const p of planets) {
    if (marker.includes(p)) return p;
  }
  return '';
}

// ═══════════════════════════════════════════════════════════════
// UNION TAB
// ═══════════════════════════════════════════════════════════════

// Click the orbs to open form
document.getElementById('union-empty').addEventListener('click', () => {
  document.getElementById('union-empty').style.display = 'none';
  document.getElementById('union-form-wrap').style.display = 'block';
});

document.getElementById('btn-union-cancel').addEventListener('click', () => {
  document.getElementById('union-form-wrap').style.display = 'none';
  document.getElementById('union-empty').style.display = 'block';
});

document.getElementById('union-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = e.target.querySelector('.btn-next');
  setLoading(btn, true);

  const payload = {
    ...userData,
    partner_name: document.getElementById('u-name').value,
    partner_birth_date: document.getElementById('u-dob').value,
    partner_birth_time: document.getElementById('u-time').value,
    partner_lat: document.getElementById('u-lat').value,
    partner_lng: document.getElementById('u-lng').value,
  };

  try {
    const res = await api('/api/union', payload);
    unionData = res;
    renderUnion(res.union);
    document.getElementById('union-form-wrap').style.display = 'none';
    document.getElementById('union-result').style.display = 'block';
  } catch (e) {
    toast('Could not generate: ' + e.message, true);
  } finally {
    setLoading(btn, false);
  }
});

function renderUnion(u) {
  document.getElementById('union-bond').textContent = u.bond_summary;
  document.getElementById('union-dynamic').textContent = u.emotional_dynamic;
  document.getElementById('union-support').textContent = u.support_line;
  document.getElementById('union-friction').textContent = u.friction_line;
  document.getElementById('union-invitation').textContent = u.invitation || '';
}

document.getElementById('btn-union-new').addEventListener('click', () => {
  document.getElementById('union-result').style.display = 'none';
  document.getElementById('union-empty').style.display = 'block';
  unionData = null;
});

// ═══════════════════════════════════════════════════════════════
// BIRTH CHART TAB
// ═══════════════════════════════════════════════════════════════

document.getElementById('btn-gen-bc').addEventListener('click', async () => {
  const btn = document.getElementById('btn-gen-bc');
  setLoading(btn, true);
  document.querySelector('.bc-loading').style.display = 'flex';
  document.getElementById('bc-intro').style.display = 'none';

  try {
    const res = await api('/api/birth-chart', userData);
    renderBirthChart(res.birth_chart);
    document.querySelector('.bc-loading').style.display = 'none';
    document.getElementById('bc-content').style.display = 'block';
  } catch (e) {
    const msg = e.message || '';
    let userMsg;
    if (msg.includes('Overloaded') || msg.includes('529')) {
      userMsg = 'Our servers are busy right now. Your sacred study takes deep computation. Please try again in a minute.';
    } else if (msg.includes('credit') || msg.includes('balance')) {
      userMsg = 'Service temporarily unavailable. Please try again shortly.';
    } else {
      userMsg = 'Something went wrong generating your birth chart. Please try again.';
    }
    const loadingEl = document.querySelector('.bc-loading');
    loadingEl.querySelector('p').textContent = userMsg;
    loadingEl.innerHTML += '<button class="btn-next" onclick="document.getElementById(\'btn-gen-bc\').click()" style="margin-top:16px"><span class="btn-text">Try Again</span></button>';
  } finally {
    setLoading(btn, false);
  }
});

function renderBirthChart(bc) {
  console.log('renderBirthChart called with:', JSON.stringify(bc).substring(0, 500));
  console.log('great_yogas:', bc.great_yogas?.length, 'first:', JSON.stringify(bc.great_yogas?.[0])?.substring(0, 200));
  const container = document.getElementById('bc-content');
  container.innerHTML = '';

  function addSection(label, text, cls = '') {
    if (!text) return;
    const div = document.createElement('div');
    div.className = `bc-section ${cls}`;
    div.innerHTML = `<div class="bc-label">${label}</div><p>${text}</p>`;
    container.appendChild(div);
  }

  function addForceList(label, forces) {
    if (!forces || !forces.length) return;
    console.log(`addForceList: ${label}, ${forces.length} items, first:`, JSON.stringify(forces[0]));
    const wrapper = document.createElement('div');
    wrapper.className = 'bc-section';
    wrapper.innerHTML = `<div class="bc-label">${label}</div>`;
    forces.forEach(f => {
      console.log(`  Force: ${f.name}, sacred_capacity length: ${(f.sacred_capacity||'').length}, keys: ${Object.keys(f)}`);
      const name = f.name || f.title || '';
      const subtitle = f.subtitle || '';
      const capacity = f.sacred_capacity || f.body || f.capacity || f.description || '';
      const distortion = f.distortion || f.shadow || '';
      const purified = f.purified_expression || '';
      let html = `<div class="bc-force"><h4>${name}</h4>`;
      if (subtitle) html += `<div class="bc-force-sub">${subtitle}</div>`;
      if (capacity) html += `<p>${distortion || purified ? '<strong>Sacred capacity:</strong> ' : ''}${capacity}</p>`;
      if (distortion) html += `<p><strong>Distortion:</strong> ${distortion}</p>`;
      if (purified) html += `<p><strong>Purified expression:</strong> ${purified}</p>`;
      html += '</div>';
      wrapper.innerHTML += html;
    });
    container.appendChild(wrapper);
  }

  function addTimingList(label, timings) {
    if (!timings || !timings.length) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'bc-section';
    wrapper.innerHTML = `<div class="bc-label">${label}</div>`;
    timings.forEach(t => {
      const name = t.name || t.title || '';
      const subtitle = t.subtitle || '';
      const body = t.chapter_body || t.body || t.sacred_capacity || t.description || '';
      let html = `<div class="bc-timing"><h4>${name}</h4>`;
      if (subtitle) html += `<div class="bc-force-sub">${subtitle}</div>`;
      if (body) html += `<p>${body}</p>`;
      html += '</div>';
      wrapper.innerHTML += html;
    });
    container.appendChild(wrapper);
  }

  function addPhaseList(label, phases) {
    if (!phases || !phases.length) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'bc-section';
    wrapper.innerHTML = `<div class="bc-label">${label}</div>`;
    phases.forEach(p => {
      const title = p.title || p.name || p.phase || '';
      const age = p.age_range || '';
      const body = p.body || '';
      let html = `<div class="bc-phase"><h4>${title}${age ? ' (' + age + ')' : ''}</h4>`;
      if (body) html += `<p>${body}</p>`;
      html += '</div>';
      wrapper.innerHTML += html;
    });
    container.appendChild(wrapper);
  }

  // v2.1 sacred study structure
  if (bc.title) addSection('', `<strong style="font-size:18px">${bc.title}</strong>`, 'opening');
  addSection('Opening Promise', bc.opening_promise, 'opening');
  addSection('Entrusted Beauty', bc.entrusted_beauty);
  addSection('Central Knot', bc.central_knot);
  addForceList('The Great Yogas', bc.great_yogas);
  addForceList('The Finer Yogas', bc.finer_yogas);
  addForceList('Deeper Shaping Forces', bc.deeper_shaping_forces);
  addTimingList('Great Timing Currents', bc.great_timing_currents);
  addPhaseList('Life Phases', bc.life_phases);
  addSection('Present Threshold', bc.present_threshold);
  addSection('Love', bc.love);
  addSection('Work', bc.work);
  addSection('Embodiment', bc.embodiment);
  addSection('Closing Destiny', bc.closing_destiny, 'closing');

  // Fallback: v1.4 flat structure (if old schema response)
  if (!bc.title && bc.opening_essence) {
    const oldSections = [
      { key: 'opening_essence', label: 'Essence', cls: 'opening' },
      { key: 'core_signature', label: 'Core Signature' },
      { key: 'temperament', label: 'Temperament' },
      { key: 'emotional_nature', label: 'Emotional Nature' },
      { key: 'key_yogas', label: 'Key Yogas' },
      { key: 'strengths_and_blessings', label: 'Strengths & Blessings' },
      { key: 'growth_edges', label: 'Growth Edges' },
      { key: 'relationship_patterning', label: 'Relationships' },
      { key: 'work_and_calling', label: 'Work & Calling' },
      { key: 'closing_integration', label: 'Integration', cls: 'closing' },
    ];
    oldSections.forEach(s => addSection(s.label, bc[s.key], s.cls || ''));
  }
}

// ═══════════════════════════════════════════════════════════════
// ZODIAC WHEEL DRAWING
// ═══════════════════════════════════════════════════════════════

function drawZodiacWheel(canvasId, chart) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const cy = h / 2;
  const r = Math.min(cx, cy) - 20;

  ctx.clearRect(0, 0, w, h);

  // Outer circle
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.strokeStyle = 'rgba(0,0,0,0.1)';
  ctx.lineWidth = 1;
  ctx.stroke();

  // Inner circle
  ctx.beginPath();
  ctx.arc(cx, cy, r * 0.65, 0, Math.PI * 2);
  ctx.strokeStyle = 'rgba(0,0,0,0.06)';
  ctx.stroke();

  // Sign labels
  ctx.font = '9px Inter, sans-serif';
  ctx.fillStyle = 'rgba(0,0,0,0.3)';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  SIGNS.forEach((sign, i) => {
    const angle = (i * 30 - 90 + 15) * Math.PI / 180;
    const lx = cx + (r + 12) * Math.cos(angle);
    const ly = cy + (r + 12) * Math.sin(angle);

    ctx.save();
    ctx.translate(lx, ly);
    ctx.rotate(angle + Math.PI / 2);
    ctx.fillText(sign, 0, 0);
    ctx.restore();
  });

  // Sign division lines
  for (let i = 0; i < 12; i++) {
    const angle = (i * 30 - 90) * Math.PI / 180;
    ctx.beginPath();
    ctx.moveTo(cx + r * 0.65 * Math.cos(angle), cy + r * 0.65 * Math.sin(angle));
    ctx.lineTo(cx + r * Math.cos(angle), cy + r * Math.sin(angle));
    ctx.strokeStyle = 'rgba(0,0,0,0.06)';
    ctx.stroke();
  }

  // Plot planets if available
  if (chart && chart.planets) {
    const planetSymbols = {
      'Sun': '☉', 'Moon': '☽', 'Mars': '♂', 'Mercury': '☿',
      'Jupiter': '♃', 'Venus': '♀', 'Saturn': '♄', 'Rahu': '☊', 'Ketu': '☋'
    };

    Object.entries(chart.planets).forEach(([name, p]) => {
      const signIdx = SIGNS.findIndex(s => s.toUpperCase() === p.sign.toUpperCase());
      if (signIdx === -1) return;

      const deg = signIdx * 30 + (p.degree || 15);
      const angle = (deg - 90) * Math.PI / 180;
      const pr = r * 0.8;
      const px = cx + pr * Math.cos(angle);
      const py = cy + pr * Math.sin(angle);

      ctx.font = '13px serif';
      ctx.fillStyle = 'rgba(0,0,0,0.55)';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(planetSymbols[name] || '•', px, py);
    });
  }
}

function drawSkyArc() {
  const canvas = document.getElementById('sky-arc-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;

  ctx.clearRect(0, 0, w, h);

  // Draw arc with signs
  const cx = w / 2;
  const cy = h + 40;
  const r = w / 2 - 20;

  ctx.beginPath();
  ctx.arc(cx, cy, r, Math.PI, 0);
  ctx.strokeStyle = 'rgba(0,0,0,0.08)';
  ctx.lineWidth = 1;
  ctx.stroke();

  // Labels along arc
  const arcSigns = ['VIRGO', 'LIBRA', 'PISCES', 'CAPRICORN', 'ARIES'];
  const positions = [-0.85, -0.6, -0.1, 0.3, 0.7];

  ctx.font = '9px Inter, sans-serif';
  ctx.fillStyle = 'rgba(0,0,0,0.25)';
  ctx.textAlign = 'center';

  arcSigns.forEach((s, i) => {
    const angle = Math.PI + positions[i] * Math.PI;
    const lx = cx + (r + 14) * Math.cos(angle);
    const ly = cy + (r + 14) * Math.sin(angle);
    ctx.save();
    ctx.translate(lx, ly);
    ctx.rotate(angle + Math.PI / 2);
    ctx.fillText(s, 0, 0);
    ctx.restore();
  });
}

// ═══════════════════════════════════════════════════════════════
// UTILITY
// ═══════════════════════════════════════════════════════════════

async function api(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  const json = await res.json();
  if (!json.ok) throw new Error(json.error || 'Unknown error');
  return json;
}

function setLoading(btn, loading) {
  const text = btn.querySelector('.btn-text');
  const loader = btn.querySelector('.btn-loading');
  if (text) text.style.display = loading ? 'none' : 'inline';
  if (loader) loader.style.display = loading ? 'inline' : 'none';
  btn.disabled = loading;
}

function toast(msg, isError = false) {
  const el = document.createElement('div');
  el.className = `toast ${isError ? 'error' : ''}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}
