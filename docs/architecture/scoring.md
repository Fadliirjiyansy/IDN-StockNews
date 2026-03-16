# Scoring Module — Architecture Reference

## Overview

The scoring module computes two ranking signals per article inside an **n8n Code node**:

| Signal | Model | Max | Purpose |
|--------|-------|-----|---------|
| **Recency** | Exponential decay `maxScore × e^(−λ×Δh)` | 30 | Freshness ranking |
| **Ticker** | Dictionary NER with word-boundary regex | 35 | Relevance to watchlist stocks |

## Recency Scoring

```
score = 30 × e^(−λ × hoursAgo)
λ = ln(2) / 6 ≈ 0.1155
```

**Half-life = 6 hours**: score drops to 50% after 6h, 25% after 12h, 6.25% after 24h.

This is the standard exponential-decay formula applied as a **heuristic engineering choice** for news freshness.

| Edge Case | Behavior |
|-----------|----------|
| Missing / malformed `pubDate` | Neutral fallback = 15 (50% of max) |
| Future timestamp | Clamped to Δh = 0 → full score |

## Ticker Matching

Uses a **single compiled regex** built from all watchlist tickers:

```
/\b(BBCA|BBRI|BMRI|...)\b/gi
```

Single-pass O(n) scan regardless of watchlist size.

### Watchlist Tiers

Weights are **heuristic values representing market importance**, not derived from a quantitative model.

| Tier | Weight | Count | Examples |
|------|--------|-------|---------|
| A | 15 | 10 | BBCA, BBRI, BMRI, TLKM, ASII |
| B | 10 | 11 | ADRO, PTBA, ANTM, INDF, UNVR |
| C | 5 | 3 | EXCL, MTEL, BUKA |

## Configuration

All parameters are in the `CONFIG` object at the top of `scoring.js`:

```js
CONFIG.recency.halfLife  // 6 (hours)
CONFIG.recency.maxScore  // 30
CONFIG.recency.fallback  // 15
CONFIG.ticker.maxScore   // 35
```

## Pipeline Position

```
RSS ingest → deduplication → scoring module → ranking → Telegram
```

## File

[scoring.js](file:///c:/Users/Muhammad Fadli/Documents/Side Project/market-briefing/n8n/code-nodes/scoring.js)
