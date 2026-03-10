# VPS Deployment Guide

## Requirements

- Ubuntu 22.04 LTS VPS (minimum 1 vCPU, 2GB RAM)
- Docker + Docker Compose installed
- Domain pointed to your VPS IP (for nginx + HTTPS)

## Steps

### 1. Clone the repo

```bash
git clone https://github.com/Fadliirjiyansy/IDN-StockNews.git
cd IDN-StockNews
```

### 2. Configure environment

```bash
cp config/.env.example config/.env
nano config/.env   # fill in all values
```

### 3. Start services

```bash
cd infra/docker
docker compose up -d
```

### 4. Configure nginx (production)

```bash
sudo cp infra/nginx/n8n.conf /etc/nginx/sites-available/n8n
sudo ln -s /etc/nginx/sites-available/n8n /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 5. Enable HTTPS with Certbot

```bash
sudo certbot --nginx -d your-domain.com
```

### 6. Import workflows

1. Open `https://your-domain.com`
2. Go to **Workflows** → **Import**
3. Upload all JSON files from `n8n/workflows/`

## Maintenance

```bash
# View logs
docker compose logs -f n8n

# Update n8n
docker compose pull && docker compose up -d

# Backup data
tar -czf n8n_backup_$(date +%Y%m%d).tar.gz n8n_data/
```
