#!/usr/bin/env python3
"""
Telegram bot to monitor River Permit availability and send notifications
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
import os
from dotenv import load_dotenv
import re

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

# Default permits configuration for migration
DEFAULT_PERMITS = {
    "250014": {
        "name": "Green River",
        "divisions": {
            371: "Dearlodge",
            380: "Gates of Lodore"
        }
    },
    "621743": {
        "name": "Rio Chama River", 
        "divisions": {
            1: "Rio Chama"
        }
    }
}

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# File to store previous availability state and permit configuration
DATA_DIR = os.environ.get('DATA_DIR', './data')
os.makedirs(DATA_DIR, exist_ok=True)
STATE_FILE = os.path.join(DATA_DIR, "availability_state.json")
PERMITS_CONFIG_FILE = os.path.join(DATA_DIR, "permits_config.json")

# Check interval in seconds (1 minute)
CHECK_INTERVAL = 60

class PermitConfigManager:
    """Manages dynamic permit configuration and division discovery"""
    
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.permits = self._load_permits()
        
    def _load_permits(self) -> Dict:
        """Load permits configuration from file, with migration from defaults"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading permits config: {e}")
        
        # First run or error - migrate from defaults
        logger.info("Migrating from default permits configuration")
        self._save_permits(DEFAULT_PERMITS)
        return DEFAULT_PERMITS.copy()
    
    def _save_permits(self, permits: Dict):
        """Save permits configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(permits, f, indent=2)
            self.permits = permits
            logger.info(f"Saved permits configuration with {len(permits)} permits")
        except Exception as e:
            logger.error(f"Error saving permits config: {e}")
    
    def get_permits(self) -> Dict:
        """Get current permits configuration"""
        return self.permits.copy()
    
    def add_permit(self, permit_id: str, name: str, divisions: Dict[int, str]) -> bool:
        """Add a new permit to monitoring"""
        try:
            new_permits = self.permits.copy()
            new_permits[permit_id] = {
                "name": name,
                "divisions": divisions
            }
            self._save_permits(new_permits)
            logger.info(f"Added permit {permit_id} ({name}) with {len(divisions)} divisions")
            return True
        except Exception as e:
            logger.error(f"Error adding permit {permit_id}: {e}")
            return False
    
    def remove_permit(self, permit_id: str) -> bool:
        """Remove a permit from monitoring"""
        try:
            if permit_id not in self.permits:
                return False
            
            new_permits = self.permits.copy()
            permit_name = new_permits[permit_id].get('name', permit_id)
            del new_permits[permit_id]
            self._save_permits(new_permits)
            logger.info(f"Removed permit {permit_id} ({permit_name})")
            return True
        except Exception as e:
            logger.error(f"Error removing permit {permit_id}: {e}")
            return False
    
    def list_permits(self) -> List[str]:
        """Get list of permit descriptions for display"""
        result = []
        for permit_id, config in self.permits.items():
            name = config['name']
            divisions = list(config['divisions'].values())
            result.append(f"{name} (#{permit_id}): {', '.join(divisions)}")
        return result
    
    def discover_divisions(self, permit_id: str, session: requests.Session, 
                          permit_name: str = None) -> Tuple[Dict[int, str], List[str]]:
        """
        Discover valid divisions for a permit ID
        Returns: (divisions_dict, error_messages)
        """
        divisions = {}
        errors = []
        
        # Test a range of division IDs
        test_ranges = [
            range(1, 20),      # Common low numbers
            range(300, 400),   # Green River range
            range(1000, 1100), # Higher numbers
        ]
        
        for test_range in test_ranges:
            for div_id in test_range:
                if self._test_division(permit_id, div_id, session):
                    # Use generic name if permit name not provided
                    if permit_name:
                        div_name = f"{permit_name} Div {div_id}"
                    else:
                        div_name = f"Division {div_id}"
                    divisions[div_id] = div_name
                    logger.info(f"Found valid division {div_id} for permit {permit_id}")
                
                # Rate limiting
                time.sleep(0.3)
                
                # Stop if we found some divisions and tested enough
                if len(divisions) > 0 and div_id > min(divisions.keys()) + 50:
                    break
        
        if not divisions:
            errors.append(f"No valid divisions found for permit {permit_id}")
            # Try some common alternative patterns
            for div_id in [0, 100, 200, 500, 1000]:
                if self._test_division(permit_id, div_id, session):
                    divisions[div_id] = f"Division {div_id}"
                    break
                time.sleep(0.3)
        
        return divisions, errors
    
    def _test_division(self, permit_id: str, division_id: int, session: requests.Session) -> bool:
        """Test if a permit/division combination is valid"""
        url = f"https://www.recreation.gov/api/permits/{permit_id}/divisions/{division_id}/availability"
        
        # Use a short date range for testing
        today = datetime.now()
        start_date = today.strftime('%Y-%m-%d')
        end_date = (today.replace(day=min(today.day + 7, 28))).strftime('%Y-%m-%d')
        
        params = {
            "start_date": f"{start_date}T06:00:00.000Z",
            "end_date": f"{end_date}T06:00:00.000Z",
            "commercial_acct": "false",
            "is_lottery": "false"
        }
        
        try:
            resp = session.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                # Check for expected response structure
                if ('payload' in data and 'date_availability' in data['payload']) or \
                   (isinstance(data, dict) and any(k.startswith('20') for k in data.keys())):
                    return True
                    
        except Exception as e:
            logger.debug(f"Division {division_id} test failed: {e}")
        
        return False

class RiverPermitMonitor:
    def __init__(self):
        self.session = self._create_session()
        self.previous_availability = self._load_state()
        self.is_first_run = not os.path.exists(STATE_FILE)
        self.permit_manager = PermitConfigManager(PERMITS_CONFIG_FILE)
        
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
    
    def _load_state(self) -> Dict[str, Set[str]]:
        """Load previous availability state from file"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    # Convert lists back to sets
                    return {k: set(v) for k, v in data.items()}
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
    
    def check_division_availability(self, permit_id: str, division_id: int) -> Dict[str, Dict]:
        """Check availability for a specific division"""
        url = f"https://www.recreation.gov/api/permits/{permit_id}/divisions/{division_id}/availability"
        
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
    
    def check_telegram_commands(self):
        """Check for new Telegram commands and process them"""
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('ok') and data.get('result'):
                    for update in data['result']:
                        self._process_telegram_update(update)
                        # Mark update as processed
                        offset = update['update_id'] + 1
                        requests.get(f"{url}?offset={offset}", timeout=5)
        except Exception as e:
            logger.error(f"Error checking Telegram commands: {e}")
    
    def _process_telegram_update(self, update: Dict):
        """Process a single Telegram update"""
        if 'message' not in update:
            return
            
        message = update['message']
        if 'text' not in message:
            return
            
        text = message['text'].strip()
        chat_id = message['chat']['id']
        
        # Only process commands from the configured channel
        if str(chat_id) != str(TELEGRAM_CHANNEL_ID):
            return
            
        # Handle commands
        if text.startswith('/monitor'):
            self._handle_start_monitoring(text)
        elif text.startswith('/unmonitor'):
            self._handle_stop_monitoring(text)
        elif text == '/list':
            self._handle_list_permits()
        elif text == '/help':
            self._handle_help()
    
    def _handle_start_monitoring(self, command: str):
        """Handle /monitor [permit-id] [permit-name] command"""
        parts = command.split(maxsplit=2)
        if len(parts) < 2:
            self.send_telegram_message(
                "<b>Usage:</b> /monitor [permit-id] [permit-name]\n"
                "Example: /monitor 621743 Rio Chama"
            )
            return
            
        permit_id = parts[1]
        permit_name = parts[2] if len(parts) > 2 else f"Permit {permit_id}"
        
        # Check if already monitoring
        current_permits = self.permit_manager.get_permits()
        if permit_id in current_permits:
            self.send_telegram_message(
                f"<b>Already monitoring:</b> {current_permits[permit_id]['name']} (#{permit_id})"
            )
            return
        
        # Discover divisions
        self.send_telegram_message(
            f"<b>Discovering divisions for permit {permit_id}...</b>\n"
            f"This may take a moment..."
        )
        
        divisions, errors = self.permit_manager.discover_divisions(
            permit_id, self.session, permit_name
        )
        
        if divisions:
            # Add to monitoring
            if self.permit_manager.add_permit(permit_id, permit_name, divisions):
                div_list = [f"{name} ({div_id})" for div_id, name in divisions.items()]
                self.send_telegram_message(
                    f"<b>✓ Started monitoring:</b> {permit_name} (#{permit_id})\n\n"
                    f"<b>Divisions found:</b>\n" + "\n".join(f"• {div}" for div in div_list)
                )
            else:
                self.send_telegram_message(
                    f"<b>✗ Error:</b> Failed to add permit {permit_id} to configuration"
                )
        else:
            error_msg = "\n".join(errors) if errors else "Unknown error"
            self.send_telegram_message(
                f"<b>✗ Failed to discover divisions for permit {permit_id}</b>\n\n"
                f"Error: {error_msg}\n\n"
                f"Please verify the permit ID is correct."
            )
    
    def _handle_stop_monitoring(self, command: str):
        """Handle /unmonitor [permit-id] command"""
        parts = command.split()
        if len(parts) != 2:
            self.send_telegram_message(
                "<b>Usage:</b> /unmonitor [permit-id]\n"
                "Example: /unmonitor 621743"
            )
            return
            
        permit_id = parts[1]
        current_permits = self.permit_manager.get_permits()
        
        if permit_id not in current_permits:
            self.send_telegram_message(
                f"<b>Not monitoring permit {permit_id}</b>\n\n"
                f"Use /list to see currently monitored permits."
            )
            return
        
        permit_name = current_permits[permit_id]['name']
        if self.permit_manager.remove_permit(permit_id):
            self.send_telegram_message(
                f"<b>✓ Stopped monitoring:</b> {permit_name} (#{permit_id})"
            )
        else:
            self.send_telegram_message(
                f"<b>✗ Error:</b> Failed to remove permit {permit_id}"
            )
    
    def _handle_list_permits(self):
        """Handle /list command"""
        permits = self.permit_manager.list_permits()
        if permits:
            message = "<b>Currently monitoring:</b>\n\n"
            for permit in permits:
                message += f"• {permit}\n"
        else:
            message = "<b>No permits being monitored</b>\n\nUse /monitor to add permits."
        
        self.send_telegram_message(message)
    
    def _handle_help(self):
        """Handle /help command"""
        help_text = (
            "<b>River Permit Monitor Commands:</b>\n\n"
            "<b>/monitor [permit-id] [name]</b>\n"
            "Start monitoring a new permit. The bot will automatically discover divisions.\n"
            "Example: /monitor 621743 Rio Chama\n\n"
            "<b>/unmonitor [permit-id]</b>\n"
            "Stop monitoring a permit.\n"
            "Example: /unmonitor 621743\n\n"
            "<b>/list</b>\n"
            "Show all currently monitored permits.\n\n"
            "<b>/help</b>\n"
            "Show this help message.\n\n"
            "<i>Note: Commands only work from the configured channel.</i>"
        )
        self.send_telegram_message(help_text)
    
    def check_and_notify(self):
        """Check availability and send notifications for new spots"""
        logger.info("Checking availability...")
        
        # If first run, just save state and send summary
        if self.is_first_run:
            logger.info("First run detected - initializing state without notifications")
            summary_message = "<b>River Permit Monitor</b> - Initial Status\n\n"
            total_available = 0
            
            for permit_id, permit_config in self.permit_manager.get_permits().items():
                permit_name = permit_config['name']
                summary_message += f"<b>{permit_name}</b>\n"
                
                for division_id, division_name in permit_config['divisions'].items():
                    current_dates = self.check_division_availability(permit_id, division_id)
                    current_available = set(current_dates.keys())
                    
                    # Save initial state with unique key
                    state_key = f"{permit_id}:{division_id}"
                    self.previous_availability[state_key] = current_available
                    
                    # Add to summary
                    available_count = len(current_available)
                    total_available += available_count
                    summary_message += f"  {division_name}: {available_count} dates\n"
                    
                    time.sleep(1)
                
                summary_message += "\n"
            
            summary_message += f"Monitoring {total_available} available dates. Will notify of NEW availability only."
            
            # Send summary message
            self.send_telegram_message(summary_message)
            self._save_state()
            self.is_first_run = False
            return
        
        # Normal run - check for new availability
        for permit_id, permit_config in self.permit_manager.get_permits().items():
            permit_name = permit_config['name']
            
            for division_id, division_name in permit_config['divisions'].items():
                current_dates = self.check_division_availability(permit_id, division_id)
                current_available = set(current_dates.keys())
                
                # Get previous availability for this division
                state_key = f"{permit_id}:{division_id}"
                previous_available = self.previous_availability.get(state_key, set())
                
                # Find new available dates
                new_dates = current_available - previous_available
                
                if new_dates:
                    # Build notification message
                    message = f"<b>New Availability: {division_name}</b>\n"
                    message += f"{permit_name}\n\n"
                    
                    for date in sorted(new_dates):
                        info = current_dates[date]
                        # Format date more concisely
                        date_obj = datetime.strptime(date, '%Y-%m-%d')
                        formatted_date = date_obj.strftime('%b %d, %Y')
                        message += f"• {formatted_date} - {info['remaining']} spots\n"
                    
                    # Add direct registration link
                    message += f"\n<a href='https://www.recreation.gov/permits/{permit_id}/registration/detailed-availability?type=overnight-permit'>Book Now</a>"
                    
                    # Send notification
                    self.send_telegram_message(message)
                    logger.info(f"Found {len(new_dates)} new dates for {permit_name} - {division_name}")
                
                # Also check for dates that became unavailable
                lost_dates = previous_available - current_available
                if lost_dates:
                    logger.info(f"{len(lost_dates)} dates no longer available for {permit_name} - {division_name}")
                
                # Update state
                self.previous_availability[state_key] = current_available
                
                # Small delay between divisions
                time.sleep(1)
        
        # Save state after checking all permits
        self._save_state()
    
    def run(self):
        """Run the monitor continuously"""
        logger.info("Starting River Permit Monitor...")
        
        # Log all permits being monitored
        for permit_id, permit_config in self.permit_manager.get_permits().items():
            permit_name = permit_config['name']
            divisions = list(permit_config['divisions'].values())
            logger.info(f"Monitoring {permit_name} (#{permit_id}): {divisions}")
        
        logger.info(f"Check interval: {CHECK_INTERVAL} seconds")
        
        # Build startup message
        startup_message = "<b>River Permit Monitor Started</b>\n\n"
        startup_message += "Monitoring:\n"
        
        for permit_id, permit_config in self.permit_manager.get_permits().items():
            permit_name = permit_config['name']
            divisions = list(permit_config['divisions'].values())
            startup_message += f"• {permit_name}: {', '.join(divisions)}\n"
        
        startup_message += f"\nChecking every {CHECK_INTERVAL} seconds for new availability.\n\n"
        startup_message += "<i>Use /help to see available commands.</i>"
        
        # Send startup message
        self.send_telegram_message(startup_message)
        
        while True:
            try:
                # Check for Telegram commands
                self.check_telegram_commands()
                
                # Check availability and notify
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