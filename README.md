# Discord Scheduler Bot 🤖

A Discord bot that automatically sends scheduled messages to a specific channel with different schedules and even/odd week functionality.

## Features

- **Thursday Messages**: Sends different messages on even and odd weeks at 7:55 AM Paris time
- **Tuesday Messages**: Weekly message at 8:00 AM Paris time  
- **Sunday Messages**: Weekly message at 6:00 PM Paris time
- **Timezone Support**: All times are in Paris timezone (Europe/Paris)
- **Duplicate Prevention**: Prevents sending the same message multiple times per day
- **Test Commands**: Admin commands to test messages manually
- **Status Monitoring**: Check bot status and last sent messages

## Prerequisites

1. **Python 3.11+** installed on your system
2. **Discord Bot Token** (see setup instructions below)
3. **Discord Channel ID** where messages will be sent

## Setup Instructions

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section in the left sidebar
4. Click "Add Bot" 
5. Copy the bot token (keep this secret!)
6. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
   - Server Members Intent (optional)

### 2. Invite Bot to Your Server

1. Go to the "OAuth2" > "URL Generator" section
2. Select scopes: `bot`
3. Select bot permissions: `Send Messages`, `Read Messages`, `Use Slash Commands`
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot

### 3. Get Channel ID

1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
2. Right-click on the channel where you want messages sent
3. Click "Copy ID"

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment

1. Copy the example config file:
   ```bash
   cp config.env.example .env
   ```

2. Edit the `.env` file with your values:
   ```env
   DISCORD_TOKEN=your_actual_bot_token_here
   CHANNEL_ID=your_channel_id_here
   
   # Customize your messages
   THURSDAY_EVEN_MESSAGE=Message for even weeks on Thursday
   THURSDAY_ODD_MESSAGE=Message for odd weeks on Thursday  
   TUESDAY_MESSAGE=Your Tuesday message
   SUNDAY_MESSAGE=Your Sunday message
   ```

### 6. Run the Bot

```bash
python discord_bot.py
```

## Schedule

| Day | Time | Message Type |
|-----|------|--------------|
| Thursday | 07:55 AM | Even/Odd week alternating messages |
| Tuesday | 08:00 AM | Weekly message |
| Sunday | 06:00 PM | Weekly message |

*All times are in Paris timezone (Europe/Paris)*

## Commands

- `!status` - Check bot status, current time, and last sent messages
- `!test_message <day>` - Test a message manually (Admin only)
  - Examples: `!test_message thursday`, `!test_message tuesday`, `!test_message sunday`
- `!help_bot` - Show help information

## Week Calculation

The bot uses ISO week numbers to determine even/odd weeks:
- **Even weeks**: Week numbers 2, 4, 6, 8, etc.
- **Odd weeks**: Week numbers 1, 3, 5, 7, etc.

## Error Handling

The bot includes comprehensive error handling:
- Missing environment variables
- Channel not found
- Network errors
- Permission errors
- Invalid commands

## Deployment

### Deploy on Render (Recommended)

Render is a cloud platform that offers free hosting for Discord bots. Here's how to deploy:

#### Step 1: Prepare Your Repository
1. Make sure your code is in a GitHub repository
2. Ensure you have these files in your repo:
   - `discord_bot.py` (your main bot file)
   - `requirements.txt` (dependencies)
   - `keep_alive.py` (web server for Render)

#### Step 2: Create Render Account
1. Go to [render.com](https://render.com) and sign up
2. Connect your GitHub account

#### Step 3: Create Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure the service:
   - **Name**: `discord-bot-yourname` (must be unique)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python discord_bot.py`
   - **Plan**: Select "Free" (sufficient for Discord bots)

#### Step 4: Set Environment Variables
In the Render dashboard, go to "Environment" and add:
```
DISCORD_TOKEN=your_actual_bot_token_here
CHANNEL_ID=your_channel_id_here
THURSDAY_EVEN_MESSAGE=Your even week Thursday message
THURSDAY_ODD_MESSAGE=Your odd week Thursday message
TUESDAY_MESSAGE=Your Tuesday message
SUNDAY_MESSAGE=Your Sunday message
```

#### Step 5: Deploy
1. Click "Create Web Service"
2. Render will automatically build and deploy your bot
3. The bot should start running within a few minutes

#### Step 6: Keep Bot Alive
The `keep_alive.py` file creates a web server that prevents Render from putting your bot to sleep. Make sure this line is in your `discord_bot.py`:
```python
keep_alive()  # This should be called before bot.run()
```

#### Important Notes for Render:
- ✅ **Free tier**: 750 hours/month (enough for continuous running)
- ✅ **Auto-restart**: Render automatically restarts if your bot crashes
- ✅ **Logs**: View real-time logs in the Render dashboard
- ⚠️ **Sleep mode**: Free services may sleep after 15 minutes of inactivity (keep_alive prevents this)
- ⚠️ **Build time**: Initial deployment takes 2-3 minutes

### Other Deployment Options

#### Windows (Task Scheduler)
1. Create a batch file that runs the Python script
2. Use Task Scheduler to run it at startup
3. Set it to restart on failure

#### Linux (systemd)
1. Create a systemd service file
2. Enable and start the service
3. Configure auto-restart

#### Docker (Optional)
A Dockerfile can be added for containerized deployment.

## Troubleshooting

### Bot Not Responding
- Check if the bot token is correct
- Verify the bot has permissions in the target channel
- Ensure the channel ID is correct

### Messages Not Sending
- Check bot permissions (Send Messages)
- Verify the channel exists and bot can access it
- Check console logs for error messages

### Render Deployment Issues

#### Bot Won't Start on Render
1. **Check Build Logs**: In Render dashboard → Logs → Build logs
2. **Verify Environment Variables**: Make sure all required env vars are set
3. **Check Start Command**: Should be `python discord_bot.py`
4. **Python Version**: Ensure using Python 3.8+ in Render settings

#### Bot Goes Offline After 15 Minutes
- **Solution**: Make sure `keep_alive()` is called in your code
- **Check**: Verify `keep_alive.py` file exists in your repository
- **Auto-ping**: The bot includes auto-ping functionality to stay awake

#### Build Failures
- **Requirements**: Make sure `requirements.txt` includes all dependencies:
  ```
  discord.py>=2.3.0
  python-dotenv>=1.0.0
  pytz>=2023.3
  flask==3.0.2
  requests==2.31.0
  ```
- **File Structure**: Ensure all files are in the repository root

#### Environment Variable Errors
- **Missing Token**: `DISCORD_TOKEN not found` → Add token in Render environment settings
- **Missing Channel**: `CHANNEL_ID not found` → Add channel ID in Render environment settings
- **Format**: Don't use quotes around values in Render environment variables

#### Logs and Monitoring
- **View Logs**: Render Dashboard → Your Service → Logs
- **Real-time**: Logs update in real-time to help debug issues
- **Bot Status**: Use `!status` command in Discord to check if bot is responsive

### General Issues

#### Timezone Issues
- The bot uses `pytz` for accurate timezone handling
- All times are automatically converted to Paris timezone
- Daylight saving time is handled automatically

#### Permission Issues
- Bot needs "Send Messages" permission in target channel
- Bot needs "Read Message History" for some features
- Make sure the bot has the authorization to post in the channel you want it to post.
- Check Discord server permissions if commands don't work

## Contributing

Feel free to submit issues or pull requests to improve the bot!

## License

This project is open source and available under the MIT License. 