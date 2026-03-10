# 📈 IDN-StockNews — Market Briefing

An automated Indonesian stock market briefing system powered by **n8n**. Collects news from RSS feeds and financial APIs, processes and summarises them, then delivers structured briefings via Telegram.

---

## 📁 Project Structure

```
IDN-StockNews/
├── .github/                   GitHub Actions CI + issue templates
├── config/
│   ├── .env.example           ← copy to .env and fill in values
│   └── rss-sources.json       RSS feed registry
├── docs/
│   ├── architecture/          System design overview
│   ├── workflows/             Per-workflow guides
│   ├── api/                   External API setup (Telegram, etc.)
│   └── deployment/            VPS + production deployment guide
├── examples/                  Sample payloads (RSS items, Telegram messages)
├── infra/
│   ├── docker/                docker-compose.yml
│   ├── nginx/                 Reverse proxy config
│   └── vps/                   VPS bootstrap script
├── n8n/
│   └── workflows/             Importable n8n workflow JSON files
├── scripts/
│   ├── setup/                 First-run helpers
│   ├── utils/                 Health checks + validation
│   └── deploy/                Production deployment scripts
├── tests/
│   ├── fixtures/              Sample data for offline testing
│   ├── integration/           End-to-end pipeline tests
│   └── unit/                  Unit tests for helper functions
└── workflows/                 Workflow documentation
```

---

## 🚀 Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/Fadliirjiyansy/IDN-StockNews.git
cd IDN-StockNews
cp config/.env.example config/.env
# Edit config/.env with your Telegram token, API keys, etc.
```

### 2. Start n8n

```bash
cd infra/docker
docker compose --env-file ../../config/.env up -d
```

### 3. Import workflows

Open `http://localhost:5678` → **Workflows** → **Import** → upload files from `n8n/workflows/`

### 4. Run the test

Open **Market Briefing - Test Workflow** and hit **Execute** — you should see `✅ Test passed!`

---

## 📋 Workflows

| Workflow | File | Status |
|----------|------|--------|
| Test Workflow | `n8n/workflows/test-workflow.json` | ✅ Ready |
| RSS Fetcher | _coming soon_ | 🔧 Planned |
| Telegram Sender | _coming soon_ | 🔧 Planned |

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
- [Telegram Bot Setup](docs/api/telegram-setup.md)
- [VPS Deployment](docs/deployment/vps-deployment.md)
- [Test Workflow Guide](docs/workflows/test-workflow.md)

---

## License

MIT
