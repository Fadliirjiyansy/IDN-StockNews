# Telegram Bot Setup

## 1. Create a Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **API token** provided

## 2. Get Your Chat ID

1. Start a conversation with your bot
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find the `"chat":{"id":...}` field — that is your `TELEGRAM_CHAT_ID`

## 3. Configure in n8n

1. In n8n, go to **Settings → Credentials**
2. Add a new **Telegram** credential
3. Paste your bot token

## 4. Configure in .env

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-your-token
TELEGRAM_CHAT_ID=-1001234567890
```

## Testing

Send a test message via n8n's Telegram node to confirm the connection.
