# River Permit Bot - Project Context

## Overview
This is a Telegram bot that monitors Recreation.gov for river permit availability and sends real-time notifications when new spots become available.

## Key Features
- Monitors two permit divisions: Dearlodge (371) and Gates of Lodore (380)
- Checks for new availability every 60 seconds
- Sends Telegram notifications only for NEW spots (no duplicates)
- Includes direct registration links with human-readable date formatting
- Runs in Docker for easy deployment with automatic restart

## Architecture
- **Language**: Python 3.9
- **Deployment**: Docker/Docker Compose
- **State Management**: JSON file in ./data directory
- **API Integration**: Recreation.gov API with browser-like headers to avoid 403 errors
- **Notifications**: Telegram Bot API

## Important Technical Details

### Environment Variables (stored in .env file)
- `RECREATION_API_KEY`: API key for Recreation.gov
- `TELEGRAM_BOT_TOKEN`: Telegram bot token from @BotFather
- `TELEGRAM_CHANNEL_ID`: Telegram channel ID (negative number for groups/channels)

### API Behavior
- The Recreation.gov API requires browser-like headers including User-Agent
- Division IDs are hardcoded: 371 (Dearlodge) and 380 (Gates of Lodore)
- API returns availability in a payload structure with date_availability object
- Dates are in ISO format with 'Z' timezone suffix

### First Run Behavior
- On first run, the bot detects no state file exists
- Sends a summary message instead of individual notifications
- Saves current availability to prevent notification spam
- Subsequent runs only notify about NEW availability

### Docker Setup
- Uses docker-compose with env_file directive to load .env
- Persistent volume mount at ./data for state storage
- Configured with restart: always for automatic recovery
- Logs are managed with json-file driver with rotation

## Common Tasks

### Start the bot
```bash
./docker_start.sh
```

### View logs
```bash
./docker_logs.sh
```

### Stop the bot
```bash
./docker_stop.sh
```

### Reset notification state
```bash
rm data/availability_state.json
```

### Test Telegram connection
```bash
python3 test_telegram.py
```

### Check current availability manually
```bash
python3 check_availability.py
```

## File Structure
- `river_permit_bot.py` - Main bot application
- `docker-compose.yml` - Docker service configuration
- `Dockerfile` - Container build instructions
- `.env` - Environment variables (not in git)
- `.env.example` - Template for environment setup
- `data/` - Persistent state storage directory
- `test_telegram.py` - Utility to test Telegram setup
- `check_availability.py` - Manual availability checker
- `find_divisions.py` - Tool to discover division IDs

## Notification Format
New availability notifications include:
- Location name (Dearlodge or Gates of Lodore)
- Permit ID
- List of newly available dates with full formatting (e.g., "Monday, July 15, 2025")
- Number of spots available for each date
- Direct registration link
- Permit overview page link

## Development Notes
- Uses python-dotenv for environment variable management
- All sensitive credentials must be in .env (never commit these)
- The bot uses requests.Session() for consistent API access
- Rate limiting is implemented with time.sleep() between API calls
- Logging is configured with timestamps for debugging

## Troubleshooting
- If getting 403 errors: Check browser headers in session setup
- If not sending messages: Verify bot is admin in Telegram channel
- If duplicate notifications: Check/delete availability_state.json
- For testing: Use test_telegram.py to verify bot configuration

## Future Improvements to Consider
- Add more permit divisions if needed
- Implement configurable check intervals
- Add support for multiple Telegram channels
- Create web dashboard for availability status
- Add email notifications as alternative to Telegram