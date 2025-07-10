# River Permit Bot

A Telegram bot that monitors Recreation.gov for River Permit availability and sends notifications when new spots open up.

## Features

- Monitors Dearlodge and Gates of Lodore permit divisions
- Checks every minute for new availability
- Sends notifications only for NEW spots (no duplicates)
- Includes direct registration links in notifications
- Formats dates clearly (e.g., "Monday, July 15, 2025")
- Runs in Docker for easy deployment
- Automatically restarts on system boot

## Prerequisites

- Docker and Docker Compose installed
- Recreation.gov API key
- Telegram bot token
- Telegram channel ID

## Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   - `RECREATION_API_KEY`: Your Recreation.gov API key
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from @BotFather
   - `TELEGRAM_CHANNEL_ID`: Your Telegram channel ID

## Quick Start

1. Start the bot:
   ```bash
   ./docker_start.sh
   ```

2. View logs:
   ```bash
   ./docker_logs.sh
   ```

3. Stop the bot:
   ```bash
   ./docker_stop.sh
   ```

## How It Works

### First Run
On first run, the bot will:
- Check current availability for all divisions
- Send a summary message showing total available dates
- Save the current state (won't notify about these existing spots)

### Subsequent Runs
The bot will:
- Check for new availability every minute
- Compare with saved state
- Send notifications ONLY for newly available dates
- Include formatted dates and direct registration links
- Update the saved state

## Docker Configuration

The bot runs in a Docker container with:
- Automatic restart on failure
- Persistent state storage in `./data` directory
- Log rotation to prevent disk space issues
- Starts automatically when Docker starts

## Files

- `river_permit_bot.py` - Main bot script
- `Dockerfile` - Docker container configuration
- `docker-compose.yml` - Docker Compose configuration
- `data/` - Persistent storage for bot state
- `requirements.txt` - Python dependencies

## Monitoring

Check if the bot is running:
```bash
docker-compose ps
```

View recent logs:
```bash
docker-compose logs --tail=50
```

## Troubleshooting

1. **Bot not sending messages**: Check logs with `./docker_logs.sh`
2. **Container not starting**: Run `docker-compose up` (without -d) to see errors
3. **Reset state**: Delete `data/availability_state.json` to reset tracking

## Telegram Messages

### Initial Status (First Run)
```
📊 River Permit Monitor Initial Status

Dearlodge: 14 dates available
Gates of Lodore: 0 dates available

Total: 14 dates with availability
✅ Monitoring active - will notify of NEW availability only
```

### New Availability
```
🎉 New River Permit Availability!

📍 Dearlodge
Permit #250014

🗓 Newly available dates (2 total):

• Monday, July 15, 2025
  1 of 1 spots available

• Tuesday, July 16, 2025
  2 of 2 spots available

🔗 Book Now:
Direct Registration Link

📱 Permit Overview Page
```