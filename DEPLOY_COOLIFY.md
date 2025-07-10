# Deploying River Permit Bot on Coolify

This guide walks you through deploying the River Permit Bot on Coolify.

## Prerequisites

- Coolify instance up and running
- GitHub repository with the bot code
- Recreation.gov API key
- Telegram bot token and channel ID

## Deployment Steps

### 1. Create a New Project in Coolify

1. Log into your Coolify dashboard
2. Click "New Project" or go to an existing project
3. Click "New Resource" → "Docker Compose"

### 2. Configure the Source

1. **Source Type**: Choose "GitHub" (or "GitLab" if applicable)
2. **Repository**: Enter your repository URL
3. **Branch**: Select `main` (or your default branch)
4. **Build Path**: Leave as `/` (root)
5. **Docker Compose File**: Enter `docker-compose.prod.yml`

### 3. Set Environment Variables

In Coolify's environment variables section, add:

```bash
RECREATION_API_KEY=your_recreation_gov_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHANNEL_ID=your_telegram_channel_id_here
```

**Important**: Do NOT commit these values to your repository. Enter them only in Coolify's secure environment variables.

### 4. Configure Deployment Settings

1. **Deployment Type**: Set to "Docker Compose"
2. **Build Pack**: Docker Compose
3. **Health Check**: Already configured in docker-compose.prod.yml
4. **Restart Policy**: Already set to "always" in compose file

### 5. Storage Configuration

The bot uses a named volume `river-permit-data` for persistent storage. Coolify will automatically manage this volume.

### 6. Deploy

1. Click "Deploy"
2. Monitor the deployment logs
3. Check that the container starts successfully

## Verifying Deployment

### Check Logs
In Coolify, go to your application and click on "Logs" to see:
- Startup messages
- "River Permit Monitor Started!" message
- Regular check intervals (every 60 seconds)

### Expected Log Output
```
2025-07-10 12:00:00 - river_permit_bot - INFO - Starting River Permit Monitor...
2025-07-10 12:00:00 - river_permit_bot - INFO - Monitoring divisions: ['Dearlodge', 'Gates of Lodore']
2025-07-10 12:00:00 - river_permit_bot - INFO - Check interval: 60 seconds
```

### Telegram Verification
You should receive messages in your Telegram channel:
1. **On startup**: "🚀 River Permit Monitor Started!"
2. **First run**: Summary of current availability
3. **New spots**: Notifications when new permits become available

## Troubleshooting

### Bot Not Starting
1. Check environment variables are set correctly
2. Verify Telegram bot token is valid
3. Ensure bot is admin in your Telegram channel

### No Telegram Messages
1. Check logs for error messages
2. Verify TELEGRAM_CHANNEL_ID format (should be negative number for groups)
3. Test with `docker exec -it river-permit-bot python test_telegram.py`

### API Errors (403 Forbidden)
- The Recreation.gov API key might be invalid
- Check if the API endpoints have changed

### Persistent Data
- Data is stored in the `river-permit-data` volume
- To reset notifications: Delete the volume in Coolify's volume management

## Monitoring

### Health Checks
The container includes a health check that verifies:
- The data directory exists
- The container is responsive

### Resource Usage
- **CPU**: Minimal (spikes only during API calls)
- **Memory**: ~50-100MB
- **Storage**: <1MB for state file

## Updates

To update the bot:
1. Push changes to your GitHub repository
2. In Coolify, click "Redeploy"
3. The bot will restart with new code

## Backup

The only data that needs backing up is the state file in the volume. This contains the list of previously seen availability dates.

To backup:
```bash
docker cp river-permit-bot:/app/data/availability_state.json ./backup/
```

## Security Notes

1. Never commit API keys or tokens to git
2. Use Coolify's environment variable encryption
3. Restrict Telegram bot permissions to only necessary channels
4. Regularly rotate API keys and tokens

## Alternative: Deploy Without GitHub

If you prefer not to use GitHub:

1. In Coolify, choose "Docker Image" instead of GitHub
2. Build and push your image to a registry:
   ```bash
   docker build -t your-registry/river-permit-bot:latest .
   docker push your-registry/river-permit-bot:latest
   ```
3. Use that image in Coolify
4. Still set environment variables as described above