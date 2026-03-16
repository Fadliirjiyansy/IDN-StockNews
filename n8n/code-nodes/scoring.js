// ============================================================
// SCORING MODULE — n8n Code Node
// IDN-StockNews Market Briefing Pipeline
// ============================================================
// Two ranking signals:
//   1. Recency scoring  (exponential decay)
//   2. Ticker matching  (dictionary-based NER Lite)
//
// Pure JavaScript — no external dependencies.
// Paste this entire file into an n8n Code node.
// ============================================================

// ────────────────────────────────────────────────────────────
// CONFIGURATION
// ────────────────────────────────────────────────────────────

const CONFIG = {
  recency: {
    halfLife: 6,       // hours — score drops to 50% after this duration
    maxScore: 30,      // maximum recency score
    fallback: 15,      // neutral fallback for missing / malformed pubDate (50% of maxScore)
  },
  ticker: {
    maxScore: 35,      // cap for total ticker score
  },
};

// Decay constant: λ = ln(2) / halfLife
// At t = halfLife → e^(−λ·t) = e^(−ln2) = 0.5 → score = maxScore × 0.5
const DECAY_LAMBDA = Math.LN2 / CONFIG.recency.halfLife;

// ────────────────────────────────────────────────────────────
// WATCHLIST — Tiered LQ45 Tickers
// ────────────────────────────────────────────────────────────
// Weights are heuristic engineering values representing
// approximate market importance. They are NOT derived from
// any quantitative model or empirical research.
//
// Tier A (15 pts) — major market movers
// Tier B (10 pts) — large liquid stocks
// Tier C  (5 pts) — secondary thematic stocks
// ────────────────────────────────────────────────────────────

const WATCHLIST = {
  // Tier A — major market movers
  BBCA: 15, BBRI: 15, BMRI: 15, TLKM: 15, ASII: 15,
  BBNI: 15, GOTO: 15, AMMN: 15, BREN: 15, BYAN: 15,

  // Tier B — large liquid stocks
  ADRO: 10, PTBA: 10, ANTM: 10, MDKA: 10, INDF: 10,
  ICBP: 10, UNVR: 10, KLBF: 10, SMGR: 10, INTP: 10,
  BRIS: 10,

  // Tier C — secondary thematic stocks
  EXCL: 5, MTEL: 5, BUKA: 5,
};

// ────────────────────────────────────────────────────────────
// COMPILED TICKER REGEX (single pass)
// ────────────────────────────────────────────────────────────
// One regex with all tickers joined by alternation.
// The engine scans the text once — O(n) in text length
// regardless of watchlist size, vs O(n × m) if we ran one
// regex per ticker.
// ────────────────────────────────────────────────────────────

const TICKER_PATTERN = new RegExp(
  '\\b(' + Object.keys(WATCHLIST).join('|') + ')\\b',
  'gi'
);

// ────────────────────────────────────────────────────────────
// SIGNAL 1: RECENCY SCORING
// ────────────────────────────────────────────────────────────
// Model: score = maxScore × e^(−λ × Δh)
//
// λ   = ln(2) / halfLife
// Δh  = hours since publication
//
// This is the standard exponential-decay formula (same as
// radioactive half-life). Applied here as a heuristic for
// news freshness — the half-life is a tunable parameter.
// ────────────────────────────────────────────────────────────

/**
 * Compute recency score for a publication date.
 *
 * @param {string|null|undefined} pubDate  ISO date string
 * @param {Date}                  [now]    Reference time (defaults to current time)
 * @returns {number}              Score rounded to 2 decimal places
 */
function recencyScore(pubDate, now) {
  const { maxScore, fallback } = CONFIG.recency;

  // Missing pubDate → neutral fallback
  if (!pubDate) return fallback;

  const pubMs = Date.parse(pubDate);

  // Malformed date → neutral fallback
  if (Number.isNaN(pubMs)) return fallback;

  const nowMs = (now instanceof Date ? now : new Date()).getTime();
  const hoursAgo = (nowMs - pubMs) / 3_600_000; // ms → hours

  // Future timestamp → clamp to 0 hours (full score)
  const deltaH = Math.max(0, hoursAgo);

  // Exponential decay: maxScore × e^(−λ × Δh)
  const score = maxScore * Math.exp(-DECAY_LAMBDA * deltaH);

  return Math.round(score * 100) / 100;
}

// ────────────────────────────────────────────────────────────
// SIGNAL 2: TICKER MATCHING (Dictionary NER Lite)
// ────────────────────────────────────────────────────────────
// 1. Concatenate title + content
// 2. Run compiled regex (single pass, case-insensitive)
// 3. Deduplicate via Set
// 4. Sum weights, cap at maxTickerScore
// ────────────────────────────────────────────────────────────

/**
 * Detect tickers in article text and compute ticker score.
 *
 * @param {string}            title    Article title
 * @param {string|null}       content  Article body (may be null)
 * @returns {{ score: number, tickers: string[] }}
 */
function tickerMatch(title, content) {
  const { maxScore } = CONFIG.ticker;

  // Defensive: ensure we have at least an empty string
  const text = ((title || '') + ' ' + (content || '')).toUpperCase();

  // Reset regex lastIndex (global flag maintains state)
  TICKER_PATTERN.lastIndex = 0;

  // Collect unique matches
  const found = new Set();
  let match;
  while ((match = TICKER_PATTERN.exec(text)) !== null) {
    found.add(match[1]); // already uppercase from toUpperCase()
  }

  // Sum weights with cap
  const tickers = Array.from(found);
  let rawScore = 0;
  for (const t of tickers) {
    rawScore += WATCHLIST[t] || 0;
  }

  return {
    score: Math.min(rawScore, maxScore),
    tickers,
  };
}

// ────────────────────────────────────────────────────────────
// n8n CODE NODE ENTRY POINT
// ────────────────────────────────────────────────────────────
// Uncomment the block below when pasting into an n8n Code node.
// It reads all input items, enriches each with scores, and
// returns them.
// ────────────────────────────────────────────────────────────

/*
const items = $input.all();
const now = new Date();

const results = items.map(item => {
  const article = item.json;

  const rScore = recencyScore(article.pubDate, now);
  const tResult = tickerMatch(article.title, article.content);

  return {
    json: {
      title:        article.title   || '',
      link:         article.link    || '',
      pubDate:      article.pubDate || null,
      source:       article.source  || '',
      recencyScore: rScore,
      tickerScore:  tResult.score,
      tickers:      tResult.tickers,
      totalScore:   Math.round((rScore + tResult.score) * 100) / 100,
    },
  };
});

return results;
*/

// ────────────────────────────────────────────────────────────
// SELF-TEST RUNNER
// ────────────────────────────────────────────────────────────
// Run with: node scoring.js
// Tests assert expected outputs for both signals.
// ────────────────────────────────────────────────────────────

function runTests() {
  const now = new Date('2026-03-16T15:00:00+07:00');
  let passed = 0;
  let failed = 0;

  function assert(label, actual, expected) {
    const ok = JSON.stringify(actual) === JSON.stringify(expected);
    if (ok) {
      passed++;
      console.log(`  ✓ ${label}`);
    } else {
      failed++;
      console.log(`  ✗ ${label}`);
      console.log(`    expected: ${JSON.stringify(expected)}`);
      console.log(`    actual:   ${JSON.stringify(actual)}`);
    }
  }

  function approx(val, target, tolerance) {
    return Math.abs(val - target) <= tolerance;
  }

  // ── Recency Tests ──────────────────────────────────────

  console.log('\n── Recency Scoring ──');

  // Test 1: 0 hours ago → full score
  const t0 = recencyScore('2026-03-16T15:00:00+07:00', now);
  assert('0h ago → 30.00', t0, 30);

  // Test 2: 3 hours ago → ~21.21
  const t3 = recencyScore('2026-03-16T12:00:00+07:00', now);
  assert('3h ago → ~21.21', approx(t3, 21.21, 0.02), true);

  // Test 3: 6 hours ago → 15.00 (exactly half-life)
  const t6 = recencyScore('2026-03-16T09:00:00+07:00', now);
  assert('6h ago → 15.00', t6, 15);

  // Test 4: 12 hours ago → ~7.50
  const t12 = recencyScore('2026-03-16T03:00:00+07:00', now);
  assert('12h ago → ~7.50', approx(t12, 7.5, 0.01), true);

  // Test 5: 24 hours ago → ~1.88
  const t24 = recencyScore('2026-03-15T15:00:00+07:00', now);
  assert('24h ago → ~1.88', approx(t24, 1.88, 0.01), true);

  // Test 6: Missing pubDate → fallback (15)
  assert('null pubDate → 15', recencyScore(null, now), 15);
  assert('undefined pubDate → 15', recencyScore(undefined, now), 15);

  // Test 7: Malformed date → fallback (15)
  assert('malformed date → 15', recencyScore('not-a-date', now), 15);

  // Test 8: Future timestamp → full score (30)
  const tFuture = recencyScore('2026-03-16T17:00:00+07:00', now);
  assert('future +2h → 30', tFuture, 30);

  // ── Ticker Tests ───────────────────────────────────────

  console.log('\n── Ticker Matching ──');

  // Test 9: Headline with two tickers
  const r1 = tickerMatch('BBCA dan BBRI naik setelah laporan laba kuat', null);
  assert('two tickers in title', r1.tickers.sort(), ['BBCA', 'BBRI']);
  assert('two Tier-A tickers score = 30', r1.score, 30);

  // Test 10: No tickers
  const r2 = tickerMatch('Pasar saham menguat hari ini', null);
  assert('no tickers → empty', r2.tickers, []);
  assert('no tickers → score 0', r2.score, 0);

  // Test 11: Single ticker
  const r3 = tickerMatch('ASII catat rekor penjualan', null);
  assert('single ticker', r3.tickers, ['ASII']);
  assert('single Tier-A ticker score = 15', r3.score, 15);

  // Test 12: Three Tier-A tickers → capped at 35
  const r4 = tickerMatch('BBCA BBRI TLKM rally kuat', null);
  assert('3 tickers score capped at 35', r4.score, 35);

  // Test 13: Repeated ticker deduplicated
  const r5 = tickerMatch('BBCA naik tajam, saham BBCA diborong asing', null);
  assert('repeated ticker counted once', r5.tickers, ['BBCA']);
  assert('repeated ticker score = 15', r5.score, 15);

  // Test 14: Ticker embedded in word → no match
  const r6 = tickerMatch('mBBCAx dan yBBRIz', null);
  assert('embedded in word → no match', r6.tickers, []);

  // Test 15: Ticker in content, not title
  const r7 = tickerMatch('Laporan keuangan', 'Emiten GOTO rilis laporan');
  assert('ticker in content', r7.tickers, ['GOTO']);

  // Test 16: null content handled
  const r8 = tickerMatch('GOTO update terbaru', null);
  assert('null content handled', r8.tickers, ['GOTO']);

  // Test 17: Mixed tiers
  const r9 = tickerMatch('BBCA dan ADRO dan EXCL naik', null);
  assert('mixed tiers: tickers', r9.tickers.sort(), ['ADRO', 'BBCA', 'EXCL']);
  assert('mixed tiers: score = 15+10+5 = 30', r9.score, 30);

  // ── Summary ────────────────────────────────────────────

  console.log(`\n── Results: ${passed} passed, ${failed} failed ──\n`);
  if (failed > 0) process.exit(1);
}

// Run tests when executed directly via Node.js
if (typeof require !== 'undefined' && require.main === module) {
  runTests();
}
