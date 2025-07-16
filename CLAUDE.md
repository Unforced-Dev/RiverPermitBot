# River Permit Bot - Project Context

## Overview
This is a Telegram bot that monitors Recreation.gov for river permit availability and sends real-time notifications when new spots become available.

## Key Features
- Dynamic permit monitoring - add/remove permits and specific divisions via Telegram commands
- Automatic discovery of permit and division names from Recreation.gov API
- Checks for new availability every 60 seconds
- Checks for Telegram commands every 2 seconds for responsive interaction
- Sends Telegram notifications only for NEW spots (no duplicates)
- Includes direct registration links with human-readable date formatting
- Shows division IDs in brackets for easy reference (e.g., "Deerlodge Park, Yampa River [371]")
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
- Permit data is returned in a 'payload' structure with permit name in payload.name
- Division data is in payload.divisions with division IDs as string keys
- Division names are fetched from permit payload.divisions[id].name
- API returns availability in a payload structure with date_availability object
- Dates are in ISO format with 'Z' timezone suffix

### First Run Behavior
- On first run, the bot detects no state file exists
- Sends a summary message instead of individual notifications
- Saves current availability to prevent notification spam
- Subsequent runs only notify about NEW availability
- Migrates from default permits configuration to permits_config.json for dynamic management

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

### Telegram Commands
- `/help` - Show all available commands
- `/list` - Show currently monitored permits with division IDs
- `/monitor [permit-id] [name]` - Start monitoring a permit (name optional, auto-discovered)
- `/unmonitor [permit-id]` - Stop monitoring a permit
- `/monitor_division [permit-id] [division-id] [name]` - Monitor specific division (name optional)
- `/unmonitor_division [permit-id] [division-id]` - Stop monitoring specific division

## File Structure
- `river_permit_bot.py` - Main bot application
- `docker-compose.yml` - Docker service configuration
- `Dockerfile` - Container build instructions
- `.env` - Environment variables (not in git)
- `.env.example` - Template for environment setup
- `data/` - Persistent state storage directory
  - `availability_state.json` - Tracks previously seen availability
  - `permits_config.json` - Dynamic permit configuration
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
- Telegram commands are checked every 2 seconds for responsiveness
- Permit availability is checked every 60 seconds
- Division IDs must be converted to strings when accessing API data

## Troubleshooting
- If getting 403 errors: Check browser headers in session setup
- If not sending messages: Verify bot is admin in Telegram channel
- If duplicate notifications: Check/delete availability_state.json
- For testing: Use test_telegram.py to verify bot configuration

## Future Improvements to Consider
- Implement Telegram webhooks for instant command response
- Add support for multiple Telegram channels
- Create web dashboard for availability status
- Add email notifications as alternative to Telegram
- Cache permit/division names to reduce API calls
- Add ability to set custom check intervals per permit