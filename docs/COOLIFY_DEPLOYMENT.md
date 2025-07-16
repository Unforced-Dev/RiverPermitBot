# Coolify Deployment Guide

This guide explains how to deploy the River Permit Bot to Coolify with automatic deployments via GitHub Actions.

## Prerequisites

1. A Coolify instance up and running
2. GitHub repository with the bot code
3. Docker setup in the repository (already done)

## Setup Steps

### 1. Create Application in Coolify

1. Log into your Coolify dashboard
2. Click "New Resource" → "Application"
3. Select your server
4. Choose deployment method:
   - For manual deployments: Select "Docker Compose"
   - For automatic deployments: Select "GitHub" and connect your repository

### 2. Configure the Application

#### If using Docker Compose deployment:
1. Name your application (e.g., "river-permit-bot")
2. In the Docker Compose configuration, use the existing `docker-compose.yml`
3. Set up environment variables in Coolify's UI:
   ```
   RECREATION_API_KEY=your_api_key
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHANNEL_ID=your_channel_id
   DATA_DIR=/data
   ```

#### If using GitHub deployment:
1. Connect your GitHub repository
2. Select the branch to deploy (main)
3. Coolify will automatically detect the `docker-compose.yml`
4. Configure the same environment variables as above

### 3. Set Up Persistent Storage

1. In Coolify, go to your application's "Storages" tab
2. Add a new storage:
   - Name: `bot-data`
   - Mount path: `/data`
   - Size: 1GB (or as needed)
3. This ensures your bot's state persists across deployments

### 4. Configure GitHub Action (for automatic deployments)

1. In Coolify, go to your application settings
2. Find the "Webhooks" section
3. Create a new webhook and copy:
   - Webhook URL
   - Webhook Secret/Token

4. In your GitHub repository:
   - Go to Settings → Secrets and variables → Actions
   - Add two new secrets:
     - `COOLIFY_WEBHOOK_URL`: The webhook URL from Coolify
     - `COOLIFY_WEBHOOK_TOKEN`: The webhook secret/token from Coolify

5. The GitHub Action (`.github/workflows/deploy-coolify.yml`) is already configured

### 5. First Deployment

1. If using manual deployment:
   - Click "Deploy" in Coolify
   - Monitor the deployment logs

2. If using GitHub deployment:
   - Push any change to the main branch
   - The GitHub Action will trigger Coolify to deploy

### 6. Verify Deployment

1. Check the application logs in Coolify
2. You should see:
   ```
   Starting River Permit Monitor...
   Monitoring Dinosaur Green And Yampa River Permits (#250014): ['Deerlodge Park, Yampa River', 'Gates of Lodore, Green River']
   Check interval: 60 seconds
   ```

3. The bot should send a startup message to your Telegram channel

## Monitoring and Maintenance

### View Logs
- In Coolify, go to your application and click "Logs"
- You can filter by container if needed

### Update Environment Variables
1. Go to your application in Coolify
2. Click "Environment Variables"
3. Update as needed
4. Redeploy the application

### Manual Redeploy
- Click the "Redeploy" button in your application dashboard

### Automatic Deployments
- Every push to the main branch triggers a deployment
- Check GitHub Actions tab for deployment status

## Troubleshooting

### Bot not starting
1. Check environment variables are set correctly
2. Verify the data directory has proper permissions
3. Check logs for specific error messages

### Telegram not working
1. Verify TELEGRAM_BOT_TOKEN is correct
2. Ensure bot is added as admin to the channel
3. Check TELEGRAM_CHANNEL_ID format (should be negative for channels)

### Persistence issues
1. Verify storage is mounted correctly at `/data`
2. Check file permissions in the container
3. Ensure storage has enough space

### Deployment failures
1. Check GitHub Action logs
2. Verify webhook URL and token are correct
3. Check Coolify deployment logs
4. Ensure docker-compose.yml is valid

## Advanced Configuration

### Custom Check Intervals
Modify the `CHECK_INTERVAL` in `river_permit_bot.py` before deployment

### Multiple Instances
1. Create separate applications in Coolify
2. Use different environment variables for each
3. Consider using different Telegram channels

### Backup Strategy
1. Set up regular backups of the `/data` directory
2. Export Coolify application configuration
3. Keep environment variables documented securely