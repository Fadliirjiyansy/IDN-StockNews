# Telegram Bot Setup

## 1. Create a Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **Bot Token** provided

## 2. Get Your Chat ID

1. Add your bot to a group/channel, or message it directly
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Send a message to the bot, then refresh the URL
4. Find `"chat":{"id": ...}` — that's your Chat ID

## 3. Configure in n8n

1. Go to **Credentials** → **New Credential** → **Telegram API**
2. Paste your Bot Token
3. Save and reference the credential in Telegram nodes

## 4. Add to .env

```env
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## Test the Bot

Send a test message via curl:

```bash
curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d chat_id=<CHAT_ID> \
  -d text="✅ Market Briefing bot is connected!"
```
