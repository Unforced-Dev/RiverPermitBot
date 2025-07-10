FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot script
COPY river_permit_bot.py .

# Create volume mount point for persistent state
VOLUME ["/app/data"]

# Set environment variable to ensure output is not buffered
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "river_permit_bot.py"]