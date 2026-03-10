# System Architecture

## Overview

IDN-StockNews is an automated market briefing pipeline built on n8n. It collects Indonesian and global stock news from RSS feeds and APIs, processes and summarizes them, then delivers structured briefings via Telegram.

## High-Level Flow

```
RSS Sources / APIs
       │
       ▼
 [n8n Scheduler]  ← runs at market open/close
       │
       ▼
 [RSS Fetcher]    ← fetch & deduplicate articles
       │
       ▼
 [Filter & Rank]  ← relevance scoring per ticker
       │
       ▼
 [AI Summarizer]  ← optional OpenAI summarization
       │
       ▼
 [Formatter]      ← build Telegram-ready message
       │
       ▼
 [Telegram Sender] → delivery to channel/group
```

## Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| Workflow Engine | n8n (self-hosted) | Orchestrate all automation |
| News Sources | RSS + HTTP Request | Fetch raw articles |
| Summarization | OpenAI API (optional) | Condense long articles |
| Delivery | Telegram Bot API | Send briefings |
| Infra | Docker + nginx | Container runtime + reverse proxy |

## Data Flow Diagram

See `architecture-diagram.png` (to be added).

## Design Principles

- **Stateless workflows** — each run is independent; no persistent state between runs
- **Fail-safe delivery** — errors in one source don't block others
- **Modular** — each workflow handles one responsibility
- **Local-first** — runs on a VPS or local Docker without external dependencies
