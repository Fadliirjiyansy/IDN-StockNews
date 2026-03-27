#!/bin/bash
# VPS bootstrap script — run once on a fresh Ubuntu 22.04 server
set -e

echo "🚀 Setting up IDN-StockNews VPS..."

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get install -y docker-compose-plugin

# Install nginx + certbot
sudo apt-get install -y nginx certbot python3-certbot-nginx

echo "✅ VPS setup complete!"
echo "Next: clone the repo and run 'docker compose up -d' from the project root."
