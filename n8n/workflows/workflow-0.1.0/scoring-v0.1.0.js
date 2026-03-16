// ============================================================
// SCORING MODULE v0.1.0 — n8n Code Node
// IDN-StockNews Market Briefing Pipeline
// ============================================================
// Four ranking signals:
//   1. Recency scoring   (exponential decay)      — UNCHANGED
//   2. Ticker matching   (dictionary-based NER)    — UNCHANGED
//   3. Keyword boost     (financial event lexicon) — NEW
//   4. Final score       (combined formula)        — NEW
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
    fallback: 15,      // neutral fallback for missing / malformed pubDate
  },
  ticker: {
    maxScore: 35,      // cap for total ticker score
  },
  keyword: {
    maxScore: 15,      // cap for keyword score (= highest tier)
  },
};

// Decay constant: λ = ln(2) / halfLife
const DECAY_LAMBDA = Math.LN2 / CONFIG.recency.halfLife;

// ────────────────────────────────────────────────────────────
// WATCHLIST — Tiered LQ45 Tickers
// ────────────────────────────────────────────────────────────
// Weights are heuristic engineering values representing
// approximate market importance. They are NOT derived from
// any quantitative model or empirical research.
// ────────────────────────────────────────────────────────────

const WATCHLIST = {
  // Tier A (15 pts) — major market movers
  BBCA: 15, BBRI: 15, BMRI: 15, TLKM: 15, ASII: 15,
  BBNI: 15, GOTO: 15, AMMN: 15, BREN: 15, BYAN: 15,

  // Tier B (10 pts) — large liquid stocks
  ADRO: 10, PTBA: 10, ANTM: 10, MDKA: 10, INDF: 10,
  ICBP: 10, UNVR: 10, KLBF: 10, SMGR: 10, INTP: 10,
  BRIS: 10,

  // Tier C (5 pts) — secondary thematic stocks
  EXCL: 5, MTEL: 5, BUKA: 5,
};

// ────────────────────────────────────────────────────────────
// COMPILED TICKER REGEX (single pass, O(n))
// ────────────────────────────────────────────────────────────

const TICKER_PATTERN = new RegExp(
  '\\b(' + Object.keys(WATCHLIST).join('|') + ')\\b',
  'gi'
);

// ────────────────────────────────────────────────────────────
// KEYWORD TIERS — Financial Event Lexicon
// ────────────────────────────────────────────────────────────
// This is a heuristic financial event lexicon, NOT a sentiment
// model. It detects market-impacting event categories such as
// corporate actions, earnings, and analyst coverage.
//
// Scoring rule: return the HIGHEST matching tier only.
// Tiers are checked from high → low; first match wins.
// This avoids double-counting when an article mentions
// keywords from multiple tiers.
//
// The tier weights are heuristic engineering choices
// representing estimated relevance for financial news ranking.
// ────────────────────────────────────────────────────────────

const KEYWORD_TIERS = [
  {
    name: 'high',
    pts: 15,
    words: [
      'dividen', 'dividend',
      'stock split', 'pemecahan saham',
      'merger', 'akuisisi', 'takeover',
      'ipo', 'rights issue', 'buyback',
      'default', 'gagal bayar',
      'bangkrut', 'pailit',
      'suspensi', 'delisting',
      'bi rate', 'suku bunga',
    ],
  },
  {
    name: 'medium',
    pts: 8,
    words: [
      'laba bersih', 'pendapatan',
      'laporan keuangan', 'earnings',
      'profit', 'revenue',
      'rups', 'dividend payout',
      'eps', 'roe',
    ],
  },
  {
    name: 'low',
    pts: 4,
    words: [
      'rekomendasi', 'target harga',
      'price target', 'upgrade', 'downgrade',
      'outlook', 'analis',
    ],
  },
];

// ────────────────────────────────────────────────────────────
// SIGNAL 1: RECENCY SCORING (UNCHANGED)
// ────────────────────────────────────────────────────────────
// Model: score = maxScore × e^(−λ × Δh)
// λ = ln(2) / halfLife, Δh = hours since publication
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
// SIGNAL 2: TICKER MATCHING (UNCHANGED)
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

  const text = ((title || '') + ' ' + (content || '')).toUpperCase();

  // Reset regex lastIndex (global flag maintains state)
  TICKER_PATTERN.lastIndex = 0;

  const found = new Set();
  let match;
  while ((match = TICKER_PATTERN.exec(text)) !== null) {
    found.add(match[1]);
  }

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
// SIGNAL 3: KEYWORD BOOST (Financial Event Lexicon)  — NEW
// ────────────────────────────────────────────────────────────
// Scans title + content for market-impacting financial events.
//
// This is a heuristic keyword lexicon — NOT sentiment analysis.
// It returns the HIGHEST matching tier score only (no summing
// across tiers) to avoid inflating scores when an article
// mentions keywords from multiple tiers about the same event.
//
// Matching is case-insensitive, using indexOf on lowercased
// text for simplicity and speed (no regex needed since these
// are literal phrases).
// ────────────────────────────────────────────────────────────

/**
 * Detect financial event keywords and return the highest tier score.
 *
 * @param {string}       title    Article title
 * @param {string|null}  content  Article body (may be null)
 * @returns {{ score: number, keyword: string|null }}
 */
function keywordScore(title, content) {
  // Defensive: combine and lowercase
  const text = ((title || '') + ' ' + (content || '')).toLowerCase();

  // Check tiers from highest to lowest; return on first match
  for (const tier of KEYWORD_TIERS) {
    for (const word of tier.words) {
      if (text.indexOf(word) !== -1) {
        return { score: tier.pts, keyword: word };
      }
    }
  }

  // No match
  return { score: 0, keyword: null };
}

// ────────────────────────────────────────────────────────────
// FINAL SCORE — Combined Formula  — NEW
// ────────────────────────────────────────────────────────────
// finalScore = recencyScore + tickerScore + keywordScore
//
//   | Signal   | Max |
//   |----------|-----|
//   | Recency  | 30  |
//   | Ticker   | 35  |
//   | Keyword  | 15  |
//   | TOTAL    | 80  |
//
// The weights represent heuristic importance for financial
// news ranking — they are engineering choices, not derived
// from any optimization or empirical evaluation.
// ────────────────────────────────────────────────────────────

/**
 * Compute the final combined score for an article.
 *
 * @param {number} rScore   Recency score
 * @param {number} tScore   Ticker score
 * @param {number} kScore   Keyword score
 * @returns {number}         Combined score rounded to 2 decimals
 */
function finalScore(rScore, tScore, kScore) {
  return Math.round((rScore + tScore + kScore) * 100) / 100;
}

// ────────────────────────────────────────────────────────────
// n8n CODE NODE ENTRY POINT
// ────────────────────────────────────────────────────────────
// Uncomment the block below when pasting into an n8n Code node.
// ────────────────────────────────────────────────────────────

/*
const items = $input.all();
const now = new Date();

const scored = items.map(item => {
  const a = item.json;

  const rScore  = recencyScore(a.pubDate, now);
  const tResult = tickerMatch(a.title, a.content);
  const kResult = keywordScore(a.title, a.content);
  const fScore  = finalScore(rScore, tResult.score, kResult.score);

  return {
    json: {
      title:        a.title   || '',
      link:         a.link    || '',
      pubDate:      a.pubDate || null,
      source:       a.source  || '',
      recencyScore: rScore,
      tickerScore:  tResult.score,
      tickers:      tResult.tickers,
      keywordScore: kResult.score,
      matchedKeyword: kResult.keyword,
      finalScore:   fScore,
    },
  };
});

scored.sort((a, b) => b.json.finalScore - a.json.finalScore);
return scored.slice(0, 10);
*/

// ────────────────────────────────────────────────────────────
// SELF-TEST RUNNER
// ────────────────────────────────────────────────────────────
// Run with: node scoring-v0.1.0.js
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

  // ── Recency Tests (unchanged) ──────────────────────────

  console.log('\n── Recency Scoring ──');

  const t0 = recencyScore('2026-03-16T15:00:00+07:00', now);
  assert('0h ago → 30.00', t0, 30);

  const t3 = recencyScore('2026-03-16T12:00:00+07:00', now);
  assert('3h ago → ~21.21', approx(t3, 21.21, 0.02), true);

  const t6 = recencyScore('2026-03-16T09:00:00+07:00', now);
  assert('6h ago → 15.00', t6, 15);

  const t12 = recencyScore('2026-03-16T03:00:00+07:00', now);
  assert('12h ago → ~7.50', approx(t12, 7.5, 0.01), true);

  const t24 = recencyScore('2026-03-15T15:00:00+07:00', now);
  assert('24h ago → ~1.88', approx(t24, 1.88, 0.01), true);

  assert('null pubDate → 15', recencyScore(null, now), 15);
  assert('undefined pubDate → 15', recencyScore(undefined, now), 15);
  assert('malformed date → 15', recencyScore('not-a-date', now), 15);

  const tFuture = recencyScore('2026-03-16T17:00:00+07:00', now);
  assert('future +2h → 30', tFuture, 30);

  // ── Ticker Tests (unchanged) ───────────────────────────

  console.log('\n── Ticker Matching ──');

  const r1 = tickerMatch('BBCA dan BBRI naik setelah laporan laba kuat', null);
  assert('two tickers in title', r1.tickers.sort(), ['BBCA', 'BBRI']);
  assert('two Tier-A tickers score = 30', r1.score, 30);

  const r2 = tickerMatch('Pasar saham menguat hari ini', null);
  assert('no tickers → empty', r2.tickers, []);
  assert('no tickers → score 0', r2.score, 0);

  const r3 = tickerMatch('ASII catat rekor penjualan', null);
  assert('single ticker', r3.tickers, ['ASII']);
  assert('single Tier-A ticker score = 15', r3.score, 15);

  const r4 = tickerMatch('BBCA BBRI TLKM rally kuat', null);
  assert('3 tickers score capped at 35', r4.score, 35);

  const r5 = tickerMatch('BBCA naik tajam, saham BBCA diborong asing', null);
  assert('repeated ticker counted once', r5.tickers, ['BBCA']);
  assert('repeated ticker score = 15', r5.score, 15);

  const r6 = tickerMatch('mBBCAx dan yBBRIz', null);
  assert('embedded in word → no match', r6.tickers, []);

  const r7 = tickerMatch('Laporan keuangan', 'Emiten GOTO rilis laporan');
  assert('ticker in content', r7.tickers, ['GOTO']);

  const r8 = tickerMatch('GOTO update terbaru', null);
  assert('null content handled', r8.tickers, ['GOTO']);

  const r9 = tickerMatch('BBCA dan ADRO dan EXCL naik', null);
  assert('mixed tiers: tickers', r9.tickers.sort(), ['ADRO', 'BBCA', 'EXCL']);
  assert('mixed tiers: score = 15+10+5 = 30', r9.score, 30);

  // ── Keyword Tests (NEW) ────────────────────────────────

  console.log('\n── Keyword Boost ──');

  // High tier: dividen
  const k1 = keywordScore('BBCA umumkan dividen besar', null);
  assert('high tier: "dividen" → 15', k1.score, 15);
  assert('high tier: matched keyword', k1.keyword, 'dividen');

  // High tier: merger in content
  const k2 = keywordScore('Aksi korporasi emiten', 'Rencana merger dengan anak usaha');
  assert('high tier: "merger" in content → 15', k2.score, 15);

  // Medium tier: laba bersih
  const k3 = keywordScore('Laba bersih naik 20 persen', null);
  assert('medium tier: "laba bersih" → 8', k3.score, 8);
  assert('medium tier: matched keyword', k3.keyword, 'laba bersih');

  // Medium tier: earnings
  const k4 = keywordScore('Quarterly earnings beat expectations', null);
  assert('medium tier: "earnings" → 8', k4.score, 8);

  // Low tier: rekomendasi
  const k5 = keywordScore('Rekomendasi saham hari ini', null);
  assert('low tier: "rekomendasi" → 4', k5.score, 4);

  // Low tier: target harga
  const k6 = keywordScore('Analis naikkan target harga BBCA', null);
  assert('low tier: "target harga" → 4', k6.score, 4);

  // No keyword match
  const k7 = keywordScore('Pasar saham menguat hari ini', null);
  assert('no keywords → 0', k7.score, 0);
  assert('no keywords → null keyword', k7.keyword, null);

  // Highest tier wins when multiple tiers match
  // "dividen" (high=15) + "laba bersih" (medium=8) → returns 15
  const k8 = keywordScore('BBCA umumkan dividen setelah laba bersih naik', null);
  assert('multi-tier: highest wins → 15', k8.score, 15);
  assert('multi-tier: matched "dividen"', k8.keyword, 'dividen');

  // Case insensitive
  const k9 = keywordScore('DIVIDEN BESAR UNTUK PEMEGANG SAHAM', null);
  assert('case insensitive → 15', k9.score, 15);

  // Null content
  const k10 = keywordScore('IPO saham baru', null);
  assert('null content handled, "ipo" → 15', k10.score, 15);

  // Empty title
  const k11 = keywordScore('', 'Ada rencana buyback saham emiten');
  assert('empty title, keyword in content → 15', k11.score, 15);

  // Both null/empty
  const k12 = keywordScore('', null);
  assert('empty title + null content → 0', k12.score, 0);

  // ── Final Score Tests (NEW) ────────────────────────────

  console.log('\n── Final Score ──');

  // Full combination: recent + ticker + keyword
  const f1 = finalScore(30, 15, 15);
  assert('30 + 15 + 15 = 60', f1, 60);

  // Max possible
  const f2 = finalScore(30, 35, 15);
  assert('max: 30 + 35 + 15 = 80', f2, 80);

  // No signals
  const f3 = finalScore(0, 0, 0);
  assert('all zero → 0', f3, 0);

  // Fallback recency + no ticker + medium keyword
  const f4 = finalScore(15, 0, 8);
  assert('15 + 0 + 8 = 23', f4, 23);

  // ── Integration Test (NEW) ─────────────────────────────

  console.log('\n── Integration ──');

  // Full article: "BBCA umumkan dividen besar setelah laba bersih naik", 1h ago
  const article = {
    title: 'BBCA umumkan dividen besar setelah laba bersih naik',
    content: 'PT Bank Central Asia Tbk (BBCA) mengumumkan pembagian dividen.',
    pubDate: '2026-03-16T14:00:00+07:00',
    source: 'kontan-market',
  };

  const aRecency = recencyScore(article.pubDate, now);
  const aTicker  = tickerMatch(article.title, article.content);
  const aKeyword = keywordScore(article.title, article.content);
  const aFinal   = finalScore(aRecency, aTicker.score, aKeyword.score);

  assert('integration: ticker = BBCA', aTicker.tickers, ['BBCA']);
  assert('integration: tickerScore = 15', aTicker.score, 15);
  assert('integration: keyword = "dividen"', aKeyword.keyword, 'dividen');
  assert('integration: keywordScore = 15', aKeyword.score, 15);
  assert('integration: recency ≈ 26.73', approx(aRecency, 26.73, 0.02), true);
  assert('integration: finalScore ≈ 56.73', approx(aFinal, 56.73, 0.02), true);

  // Article with no ticker, no keyword
  const article2 = {
    title: 'Kondisi ekonomi global membaik',
    content: 'Para ekonom menilai outlook positif.',
    pubDate: '2026-03-16T12:00:00+07:00',
  };

  const a2Recency = recencyScore(article2.pubDate, now);
  const a2Ticker  = tickerMatch(article2.title, article2.content);
  const a2Keyword = keywordScore(article2.title, article2.content);
  const a2Final   = finalScore(a2Recency, a2Ticker.score, a2Keyword.score);

  assert('no-ticker article: tickers = []', a2Ticker.tickers, []);
  assert('no-ticker article: tickerScore = 0', a2Ticker.score, 0);
  // "outlook" is a low-tier keyword
  assert('low-keyword article: keyword = "outlook"', a2Keyword.keyword, 'outlook');
  assert('low-keyword article: keywordScore = 4', a2Keyword.score, 4);
  assert('no-ticker article: finalScore ≈ 25.21', approx(a2Final, 25.21, 0.02), true);

  // ── Summary ────────────────────────────────────────────

  console.log(`\n── Results: ${passed} passed, ${failed} failed ──\n`);
  if (failed > 0) process.exit(1);
}

// Run tests when executed directly via Node.js
if (typeof require !== 'undefined' && require.main === module) {
  runTests();
}
