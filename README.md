# 📈 IDN-StockNews — Market Briefing

An automated Indonesian stock market briefing system powered by **n8n**. Collects news from RSS feeds and financial APIs, processes and summarises them, then delivers structured briefings via Telegram.

---

## 📁 Project Structure

```
IDN-StockNews/
├── .github/                   GitHub Actions CI + issue templates
├── config/
│   └── rss-sources.json       RSS feed registry (4 active sources)
├── data/
│   └── n8n/                   Persisted n8n data (bind mount)
├── docs/
│   ├── architecture/          System design overview
│   ├── workflows/             Per-workflow guides
│   ├── api/                   External API setup (Telegram, etc.)
│   └── deployment/            VPS + production deployment guide
├── examples/                  Sample payloads (RSS items, Telegram messages)
├── infra/
│   ├── nginx/                 Reverse proxy config
│   └── vps/                   VPS bootstrap script
├── n8n/
│   ├── code-nodes/            Custom n8n code nodes
│   └── workflows/             Importable n8n workflow JSON files
├── scripts/
│   ├── setup/                 First-run helpers
│   ├── utils/                 Health checks + validation
│   └── deploy/                Production deployment scripts
├── tests/
│   ├── fixtures/              Sample data for offline testing
│   ├── integration/           End-to-end pipeline tests
│   └── unit/                  Unit tests for helper functions
├── docker-compose.yml         n8n + PostgreSQL service definitions
├── .env.example               Template environment variables
└── .env                       Your actual secrets (git-ignored)
```

> **Note:** PostgreSQL data is stored in a named Docker volume (`postgres_data`), not a host directory.

---

## 🚀 Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/Fadliirjiyansy/IDN-StockNews.git
cd IDN-StockNews
cp .env.example .env
# Edit .env with your Telegram token, API keys, etc.
```

### 2. Start services (n8n + PostgreSQL)

```bash
docker compose up -d
```

### 3. Import workflows

Open `http://localhost:5678` → **Workflows** → **Import** → upload files from `n8n/workflows/`

### 4. Configure Telegram

1. Go to **Credentials** → **Add Credential** → **Telegram**
2. Paste your Bot Token from @BotFather
3. Open the **Send to Telegram** node and set your Chat ID

### 5. Test the pipeline

Open **Market Briefing - Full Pipeline** and click **Test workflow** — check your Telegram for the briefing!

---

## 📋 Workflows

| Workflow | File | Status |
|----------|------|--------|
| Full Pipeline | `n8n/workflows/Workflow-0.0.1/market-briefing-pipeline.json` | ✅ Active |
| Scoring v0.1.0 | `n8n/workflows/workflow-0.1.0/workflow-0.1.0.json` | ✅ Ready |
| Test Workflow | `n8n/workflows/Workflow-0.0.1/test-workflow.json` | ✅ Ready |

---

## ⏰ Schedule

When activated, the pipeline runs automatically:

| Time (WIB) | Edition |
|------------|---------|
| **08:55** | 🌅 Morning Edition (before market open) |
| **16:05** | 🌆 Afternoon Edition (after market close) |

---

## 🧪 Tests

```bash
# Unit tests
python3 tests/unit/test_helpers.py

# Integration tests (requires running n8n)
python3 tests/integration/test_pipeline.py
```

---

## 📚 Docs

- [Architecture Overview](docs/architecture/overview.md)
- [Event Tracker Database Tables](docs/event-tracker/database-tables.md)
- [Pipeline Workflow Guide](docs/workflows/market-briefing-pipeline.md)
- [Telegram Bot Setup](docs/api/telegram-setup.md)
- [VPS Deployment](docs/deployment/vps-deployment.md)
- [Docker Setup Guide](docs/n8n-docker-setup.md)

---

## License

MIT
