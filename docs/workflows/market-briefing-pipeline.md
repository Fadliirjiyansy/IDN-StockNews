# Market Briefing — Full Pipeline

## Workflow: Market Briefing - Full Pipeline

**File:** `n8n/workflows/market-briefing-pipeline.json`

## Purpose

Complete end-to-end pipeline that fetches Indonesian stock market news from 4 RSS sources, deduplicates, ranks by relevance, formats into a Telegram-ready message, and sends it to your Telegram channel.

## Flow

```
Schedule Trigger (08:55 + 16:05 WIB) / Manual Trigger
    ├→ Fetch Kontan (RSS)
    ├→ Fetch Bisnis (RSS)
    ├→ Fetch Detik (RSS)
    └→ Fetch Reuters (RSS)
         ↓
    Merge Group A (Kontan + Bisnis)
    Merge Group B (Detik + Reuters)
         ↓
    Merge All Feeds
         ↓
    Deduplicate & Filter (last 24h, unique URLs)
         ↓
    Score & Rank (top 10 by category relevance)
         ↓
    Format Telegram Message (Markdown)
         ↓
    Send to Telegram ✈️
```

## Setup Instructions

### 1. Configure Telegram Credentials in n8n

1. Open n8n at `http://localhost:5678`
2. Go to **Credentials** → **Add Credential** → search **Telegram**
3. Paste your **Bot Token** (from @BotFather)
4. Save the credential

### 2. Import the Workflow

1. Go to **Workflows** → **Import from File**
2. Select `n8n/workflows/market-briefing-pipeline.json`
3. Open the **Send to Telegram** node
4. Set your **Chat ID** (e.g. `-1001234567890`)
5. Select your Telegram credential from step 1

### 3. Test

1. Click **Test workflow** (uses Manual Trigger)
2. Check your Telegram chat for the briefing message

### 4. Activate

1. Toggle the workflow to **Active** (top-right switch)
2. The Schedule Trigger will fire at:
   - **08:55 WIB** — Morning Edition (before market open)
   - **16:05 WIB** — Afternoon Edition (after market close)

## Nodes (13 total)

| # | Node | Type | Purpose |
|---|------|------|---------|
| 1 | Manual Trigger | trigger | For testing |
| 2 | Schedule Trigger | trigger | Auto-run at 08:55 & 16:05 WIB |
| 3–6 | Fetch Kontan/Bisnis/Detik/Reuters | RSS Read | Fetch news articles |
| 7–8 | Merge Group A/B | Merge | Combine feeds pairwise |
| 9 | Merge All Feeds | Merge | Combine both groups |
| 10 | Deduplicate & Filter | Code | Remove duplicates, filter 24h |
| 11 | Score & Rank | Code | Rank by category, take top 10 |
| 12 | Format Telegram Message | Code | Build Markdown message |
| 13 | Send to Telegram | Telegram | Deliver to channel |

## Expected Output

```
📈 *IDN Market Briefing — Morning Edition*
🕘 11 March 2026 | 08:55 WIB

*Top News:*
1. BBCA Catat Laba Bersih Rp 48,6 Triliun — Kontan
2. IHSG Dibuka Menguat 0,5% di Awal Sesi — Bisnis
3. Bank Indonesia Pertahankan Suku Bunga 5,75% — Detik
...

---
_Powered by IDN-StockNews_
```
