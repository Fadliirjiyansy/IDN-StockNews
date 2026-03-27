# 🐳 n8n + PostgreSQL — Docker Environment

Production-ready Docker setup for **n8n** workflow automation backed by **PostgreSQL**.

## 📁 Structure

```
IDN-StockNews/
├── docker-compose.yml    # Service definitions (root level)
├── .env.example          # Template environment variables
├── .env                  # Your actual secrets (git-ignored)
├── data/
│   └── n8n/              # Persisted n8n data (bind mount)
├── infra/
│   ├── nginx/n8n.conf    # Reverse proxy config (for production)
│   └── vps/bootstrap.sh  # VPS setup script
└── n8n/
    ├── code-nodes/       # Custom n8n code nodes
    └── workflows/        # Exported n8n workflows
```

> **Note:** PostgreSQL data is stored in a named Docker volume (`postgres_data`), not a host bind mount.

## 🚀 Quick Start

### 1. Prerequisites

- Docker Engine ≥ 20.10
- Docker Compose v2 (ships with Docker Engine)

```bash
# Verify installation
docker --version
docker compose version
```

### 2. Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Generate a secure encryption key
openssl rand -hex 32

# Edit .env — paste the key and set your passwords
nano .env
```

> ⚠️ **Never commit `.env`** — it contains secrets and is already git-ignored.

### 3. Start Services

```bash
# Start in detached mode
docker compose up -d

# Watch logs (Ctrl+C to exit)
docker compose logs -f
```

### 4. Open n8n

Navigate to **http://localhost:5678** and create your first account.

## 🔧 Useful Commands

| Command | Description |
|---|---|
| `docker compose up -d` | Start all services |
| `docker compose down` | Stop all services |
| `docker compose down -v` | Stop & **delete volumes** (⚠️ data loss) |
| `docker compose logs -f n8n` | Follow n8n logs |
| `docker compose logs -f postgres` | Follow Postgres logs |
| `docker compose restart n8n` | Restart n8n only |
| `docker compose pull` | Pull latest images |
| `docker compose up -d --force-recreate` | Recreate containers |

## 💾 Backups

### Database

```bash
# Export
docker exec idn-stocknews-postgres pg_dump -U n8n n8n > backup_$(date +%Y%m%d).sql

# Import
cat backup_20260317.sql | docker exec -i idn-stocknews-postgres psql -U n8n n8n
```

### n8n Data

```bash
# The data/n8n/ directory contains files, custom nodes, etc.
tar -czf n8n_data_backup.tar.gz data/n8n/
```

## 🔒 Production Checklist

When deploying to a VPS:

- [ ] **Change all passwords** in `.env` (use strong, unique values)
- [ ] **Generate encryption key** — `openssl rand -hex 32`
- [ ] **Set up a reverse proxy** with HTTPS (see `infra/nginx/n8n.conf`)
- [ ] **Update `.env`**:
  - `N8N_HOST` → your domain (e.g. `n8n.yourdomain.com`)
  - `N8N_PROTOCOL` → `https`
  - `WEBHOOK_URL` → `https://n8n.yourdomain.com`
- [ ] **Enable firewall** — only expose ports 80/443
- [ ] **Set up automated backups** via cron
- [ ] **Enable basic auth** (optional extra layer in `docker-compose.yml`)

### Reverse Proxy (Nginx)

An existing config is provided at `infra/nginx/n8n.conf`. To set up:

```bash
# Install certbot for free HTTPS
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d n8n.yourdomain.com
```

### Reverse Proxy (Traefik — alternative)

Add Traefik as a service in `docker-compose.yml` with labels on the n8n service:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.n8n.rule=Host(`n8n.yourdomain.com`)"
  - "traefik.http.routers.n8n.tls.certresolver=letsencrypt"
```

## 🌐 Timezone

Set to `Asia/Jakarta` by default. Change `GENERIC_TIMEZONE` in `.env` to adjust.

## 📝 Notes

- **Data persistence**: n8n data is stored in `./data/n8n/` on the host. PostgreSQL data is in a named Docker volume (`postgres_data`). Running `docker compose down -v` **will erase all Postgres data**.
- **Updates**: Run `docker compose pull && docker compose up -d` to update to latest images.
- **Scaling**: This setup is designed for single-node. For HA, see [n8n queue mode](https://docs.n8n.io/hosting/scaling/queue-mode/).
