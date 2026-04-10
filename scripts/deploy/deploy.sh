#!/bin/bash
# Production deployment script
set -e

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "🚀 Deploying FinancialReportNews..."

# Pull latest images
docker compose -f "$REPO_ROOT/docker-compose.yml" pull

# Restart with zero downtime
docker compose -f "$REPO_ROOT/docker-compose.yml" up -d --force-recreate

echo "✅ Deployment complete!"
docker compose -f "$REPO_ROOT/docker-compose.yml" ps
