#!/usr/bin/env python3
"""
Telegram bot to monitor River Permit availability and send notifications
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Set
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Recreation.gov API configuration
API_KEY = os.getenv('RECREATION_API_KEY')
PERMIT_ID = "250014"
DIVISIONS = {
    371: "Dearlodge",
    380: "Gates of Lodore"
}

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# File to store previous availability state
DATA_DIR = os.environ.get('DATA_DIR', './data')
os.makedirs(DATA_DIR, exist_ok=True)
STATE_FILE = os.path.join(DATA_DIR, "availability_state.json")

# Check interval in seconds (1 minute)
CHECK_INTERVAL = 60

class RiverPermitMonitor:
    def __init__(self):
        self.session = self._create_session()
        self.previous_availability = self._load_state()
        self.is_first_run = not os.path.exists(STATE_FILE)
        
    def _create_session(self):
        """Create a session with browser-like headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://www.recreation.gov',
            'Referer': 'https://www.recreation.gov/',
            'apikey': API_KEY
        })
        return session
    
    def _load_state(self) -> Dict[int, Set[str]]:
        """Load previous availability state from file"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    # Convert lists back to sets
                    return {int(k): set(v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"Error loading state: {e}")
        return {}
    
    def _save_state(self):
        """Save current availability state to file"""
        try:
            # Convert sets to lists for JSON serialization
            data = {k: list(v) for k, v in self.previous_availability.items()}
            with open(STATE_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def check_division_availability(self, division_id: int) -> Dict[str, Dict]:
        """Check availability for a specific division"""
        url = f"https://www.recreation.gov/api/permits/{PERMIT_ID}/divisions/{division_id}/availability"
        
        # Check next 3 months
        today = datetime.now()
        start_date = today.strftime('%Y-%m-%d')
        end_date = (today.replace(month=today.month + 3)).strftime('%Y-%m-%d')
        
        params = {
            "start_date": f"{start_date}T06:00:00.000Z",
            "end_date": f"{end_date}T06:00:00.000Z",
            "commercial_acct": "false",
            "is_lottery": "false"
        }
        
        try:
            resp = self.session.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                
                if 'payload' in data and 'date_availability' in data['payload']:
                    dates = data['payload']['date_availability']
                    available_dates = {}
                    
                    for date_str, info in dates.items():
                        if info.get('remaining', 0) > 0:
                            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            available_dates[date_obj.strftime('%Y-%m-%d')] = {
                                'remaining': info['remaining'],
                                'total': info['total']
                            }
                    
                    return available_dates
            else:
                logger.error(f"HTTP {resp.status_code} for division {division_id}")
                
        except Exception as e:
            logger.error(f"Error checking division {division_id}: {e}")
        
        return {}
    
    def send_telegram_message(self, message: str):
        """Send a message to the Telegram channel"""
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        data = {
            "chat_id": TELEGRAM_CHANNEL_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        try:
            resp = requests.post(url, json=data, timeout=10)
            if resp.status_code == 200:
                logger.info("Telegram message sent successfully")
            else:
                logger.error(f"Failed to send Telegram message: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
    
    def check_and_notify(self):
        """Check availability and send notifications for new spots"""
        logger.info("Checking availability...")
        
        # If first run, just save state and send summary
        if self.is_first_run:
            logger.info("First run detected - initializing state without notifications")
            summary_message = "<b>River Permit Monitor Started</b>\n\n"
            total_available = 0
            
            for division_id, division_name in DIVISIONS.items():
                current_dates = self.check_division_availability(division_id)
                current_available = set(current_dates.keys())
                
                # Save initial state
                self.previous_availability[division_id] = current_available
                
                # Add to summary
                available_count = len(current_available)
                total_available += available_count
                summary_message += f"<b>{division_name}</b>: {available_count} dates\n"
                
                time.sleep(1)
            
            summary_message += f"\n<b>Total:</b> {total_available} dates available\n"
            summary_message += "\nMonitoring active - will notify of NEW availability only"
            
            # Send summary message
            self.send_telegram_message(summary_message)
            self._save_state()
            self.is_first_run = False
            return
        
        # Normal run - check for new availability
        for division_id, division_name in DIVISIONS.items():
            current_dates = self.check_division_availability(division_id)
            current_available = set(current_dates.keys())
            
            # Get previous availability for this division
            previous_available = self.previous_availability.get(division_id, set())
            
            # Find new available dates
            new_dates = current_available - previous_available
            
            if new_dates:
                # Build notification message
                message = f"<b>New Availability: {division_name}</b>\n\n"
                
                for date in sorted(new_dates):
                    info = current_dates[date]
                    # Format date nicely
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    formatted_date = date_obj.strftime('%b %d, %Y')
                    message += f"• {formatted_date} - {info['remaining']} spots\n"
                
                # Add direct registration link
                message += f"\n<a href='https://www.recreation.gov/permits/{PERMIT_ID}/registration/detailed-availability?type=overnight-permit'>Book Now</a>"
                
                # Send notification
                self.send_telegram_message(message)
                logger.info(f"Found {len(new_dates)} new dates for {division_name}")
            
            # Also check for dates that became unavailable
            lost_dates = previous_available - current_available
            if lost_dates:
                logger.info(f"{len(lost_dates)} dates no longer available for {division_name}")
            
            # Update state
            self.previous_availability[division_id] = current_available
            
            # Small delay between divisions
            time.sleep(1)
        
        # Save state after checking all divisions
        self._save_state()
    
    def run(self):
        """Run the monitor continuously"""
        logger.info("Starting River Permit Monitor...")
        logger.info(f"Monitoring divisions: {list(DIVISIONS.values())}")
        logger.info(f"Check interval: {CHECK_INTERVAL} seconds")
        
        # Send startup message
        self.send_telegram_message(
            f"<b>River Permit Monitor Started</b>\n\n"
            f"Monitoring: {', '.join(DIVISIONS.values())}\n"
            f"Check interval: Every {CHECK_INTERVAL} seconds"
        )
        
        while True:
            try:
                self.check_and_notify()
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
            
            # Wait for next check
            logger.info(f"Waiting {CHECK_INTERVAL} seconds until next check...")
            time.sleep(CHECK_INTERVAL)

def main():
    # Check if required environment variables are configured
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID or not API_KEY:
        print("ERROR: Missing required environment variables!")
        print("\nPlease create a .env file with:")
        print("RECREATION_API_KEY=your_api_key")
        print("TELEGRAM_BOT_TOKEN=your_bot_token")
        print("TELEGRAM_CHANNEL_ID=your_channel_id")
        print("\nSee .env.example for reference.")
        return
    
    # Create and run monitor
    monitor = RiverPermitMonitor()
    
    try:
        monitor.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == "__main__":
    main()