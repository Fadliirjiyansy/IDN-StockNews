# VPS Deployment Guide

## Prerequisites

- Ubuntu 22.04 VPS (minimum 1 vCPU / 1 GB RAM)
- Domain name pointed at VPS IP
- SSH access

## Steps

### 1. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### 2. Clone the Repo

```bash
git clone https://github.com/Fadliirjiyansy/IDN-StockNews.git
cd IDN-StockNews
cp config/.env.example .env
nano .env   # fill in your values
```

### 3. Start Services

```bash
cd infra/docker
docker compose up -d
```

### 4. Configure Nginx

```bash
sudo cp infra/nginx/n8n.conf /etc/nginx/sites-available/n8n
sudo ln -s /etc/nginx/sites-available/n8n /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 5. SSL via Certbot

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com
```

## Verify

Open `https://yourdomain.com` — n8n login screen should appear.
