#!/bin/bash
# First-run setup helper
set -e

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "🔧 IDN-StockNews First-Run Setup"
echo "================================="

# Check .env exists
if [ ! -f "$REPO_ROOT/.env" ]; then
  echo "📋 Creating .env from example..."
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  echo "⚠️  Please edit .env and fill in your values, then re-run this script."
  exit 0
fi

echo "✅ .env found"

# Check Docker
if ! command -v docker &> /dev/null; then
  echo "❌ Docker not found. Please install Docker first."
  exit 1
fi

echo "✅ Docker found: $(docker --version)"

# Start n8n
echo "🐳 Starting n8n..."
cd "$REPO_ROOT"
docker compose up -d

echo ""
echo "✅ n8n is running at http://localhost:5678"
echo "👉 Import workflows from n8n/workflows/ to get started."
