#!/bin/sh
# =============================================================================
# Import n8n credentials from environment variables
# Runs once after n8n is healthy. Safe to re-run (idempotent by credential ID).
# =============================================================================
set -e

echo "▶ Generating credentials JSON from environment..."

node -e "
const fs = require('fs');

const creds = [
  {
    id: 'frn-telegram-bot',
    name: 'Telegram Bot - FinancialReportNews',
    type: 'telegramApi',
    data: {
      accessToken: process.env.TELEGRAM_BOT_TOKEN
    }
  }
];

if (!process.env.TELEGRAM_BOT_TOKEN) {
  console.error('ERROR: TELEGRAM_BOT_TOKEN is not set. Skipping import.');
  process.exit(1);
}

fs.writeFileSync('/tmp/frn-credentials.json', JSON.stringify(creds, null, 2));
console.log('  ✔ telegram.telegramApi credential prepared');
"

echo "▶ Importing credentials into n8n (userId: ${N8N_OWNER_USER_ID})..."

n8n import:credentials \
  --input=/tmp/frn-credentials.json \
  --userId="${N8N_OWNER_USER_ID}"

rm -f /tmp/frn-credentials.json

echo "✅ Credentials imported successfully."
