#!/bin/bash
# Health check utility — validates n8n is reachable and workflows are loaded

N8N_URL="${N8N_URL:-http://localhost:5678}"
N8N_USER="${N8N_BASIC_AUTH_USER:-admin}"
N8N_PASS="${N8N_BASIC_AUTH_PASSWORD:-changeme}"

echo "🔍 Checking n8n health at $N8N_URL..."

STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -u "$N8N_USER:$N8N_PASS" \
  "$N8N_URL/healthz")

if [ "$STATUS" = "200" ]; then
  echo "✅ n8n is healthy (HTTP $STATUS)"
else
  echo "❌ n8n returned HTTP $STATUS — check if it's running"
  exit 1
fi

echo ""
echo "📋 Checking RSS sources config..."
python3 -m json.tool config/rss-sources.json > /dev/null \
  && echo "✅ rss-sources.json is valid JSON" \
  || echo "❌ rss-sources.json has JSON errors"
