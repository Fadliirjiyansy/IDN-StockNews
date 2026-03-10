#!/bin/bash
# Production deployment script
set -e

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/infra/docker/docker-compose.yml"
ENV_FILE="$REPO_ROOT/config/.env"

echo "🚀 Deploying IDN-StockNews..."

# Pull latest images
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull

# Restart with zero downtime
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --force-recreate

echo "✅ Deployment complete!"
docker compose -f "$COMPOSE_FILE" ps
