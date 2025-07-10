#!/bin/bash
# Start the River Permit Bot using Docker Compose

echo "Starting River Permit Bot..."
docker-compose up -d --build

echo ""
echo "Bot started!"
echo ""
echo "Useful commands:"
echo "  View logs:        docker-compose logs -f"
echo "  Stop bot:         docker-compose down"
echo "  Restart bot:      docker-compose restart"
echo "  Check status:     docker-compose ps"
echo ""
echo "The bot will start automatically on system boot."