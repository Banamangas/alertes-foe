# Discord Bot — Alertes FOE

A Discord bot that automatically sends scheduled messages to a specific channel. Built for Forge of Empires guild alerts, with even/odd week support and Paris timezone.

## Features

- **Thursday Messages**: Alternates between even and odd week messages at 7:55 AM Paris time
- **Tuesday Messages**: Weekly message at 8:00 AM Paris time
- **Sunday Messages**: Weekly message at 6:00 PM Paris time
- **Timezone Support**: All times are in Paris timezone (Europe/Paris), DST-aware
- **Duplicate Prevention**: Tracks sent dates to avoid double-sending
- **Test Commands**: Admin commands to trigger messages manually
- **Status Monitoring**: Check bot status and last sent times via Discord command

## Schedule

| Day | Time (Paris) | Notes |
|-----|-------------|-------|
| Thursday | 07:55 AM | Even weeks: QI alert — Odd weeks: GBG alert |
| Tuesday | 08:00 AM | Weekly |
| Sunday | 06:00 PM | Weekly |

## Prerequisites

1. Python 3.11+
2. A Discord bot token ([Discord Developer Portal](https://discord.com/developers/applications))
3. The target Discord channel ID

## Setup

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application", then go to the "Bot" section
3. Click "Reset Token" and copy your bot token (keep it secret)
4. Under "Privileged Gateway Intents", enable **Message Content Intent**

### 2. Invite the Bot to Your Server

1. Go to "OAuth2" > "URL Generator"
2. Select scope: `bot`
3. Select permissions: `Send Messages`, `Read Messages`
4. Open the generated URL and authorize the bot on your server

### 3. Get the Channel ID

1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
2. Right-click the target channel and click "Copy ID"

### 4. Configure Environment

```bash
cp config.env.example .env
```

Edit `.env` with your values:

```env
DISCORD_TOKEN=your_bot_token_here
CHANNEL_ID=your_channel_id_here

# Timezone in pytz format (defaults to Europe/Paris)
TIMEZONE=Europe/Paris

THURSDAY_EVEN_MESSAGE=Your even-week Thursday message (QI)
THURSDAY_ODD_MESSAGE=Your odd-week Thursday message (GBG)
TUESDAY_MESSAGE=Your Tuesday message
SUNDAY_MESSAGE=Your Sunday message
```

### 5. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Deployment

### Linux (systemd) — Production

Create `/etc/systemd/system/discord-bot.service`:

```ini
[Unit]
Description=Discord Bot Alertes
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/discord_bots/alertes-foe
ExecStart=/home/ubuntu/discord_bots/alertes-foe/venv/bin/python3 /home/ubuntu/discord_bots/alertes-foe/discord_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable discord-bot
sudo systemctl start discord-bot
```

Check status and logs:

```bash
sudo systemctl status discord-bot
journalctl -u discord-bot -f
```

### Windows

1. Install Python 3.11+ and add it to PATH
2. Create and activate a virtual environment:
   ```bat
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copy and fill in `.env` as described above
4. Run the bot:
   ```bat
   python discord_bot.py
   ```

To run the bot automatically on startup, use Task Scheduler:
- Trigger: At log on
- Action: `python discord_bot.py` in the project directory
- Set it to restart on failure

## Commands

- `!status` — Show bot status, current time, and last sent dates
- `!test_message <day>` — Manually trigger a message (admin only)
  - Example: `!test_message thursday`, `!test_message tuesday`, `!test_message sunday`
- `!help_bot` — Show available commands

## Week Calculation

ISO week numbers are used to determine even/odd weeks:
- **Even weeks** (2, 4, 6, 8, …): Quantum Incursions (QI) alert
- **Odd weeks** (1, 3, 5, 7, …): Guild Battlegrounds (GBG) alert

## Troubleshooting

**Bot not responding**
- Verify the token in `.env` is correct and not expired
- Check that the bot has `Send Messages` permission in the target channel
- Confirm the `CHANNEL_ID` is correct

**Messages not sending**
- Run `!status` in Discord to check connectivity
- Look at logs: `journalctl -u discord-bot -f` (Linux) or the console output (Windows)

**Timezone issues**
- The bot uses `pytz` for timezone handling — daylight saving time is automatic

## License

MIT
