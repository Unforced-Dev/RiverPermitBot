#!/usr/bin/env python3
"""
River Permit Availability Monitor with SQLite Logging

Monitors both Gates of Lodore (Green River) and Deerlodge Park (Yampa River)
for new permit availability and maintains a history in SQLite database.
"""

import requests
import json
import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# Configuration
CONFIG = {
    # Recreation.gov API Key
    "API_KEY": "5b106992-95c4-4b77-b6b5-0b60ed0ffb89",
    
    # Permit to monitor
    "PERMIT_ID": "250014",  # Dinosaur National Monument
    
    # Division IDs for river segments
    # Found via network inspection of Recreation.gov
    "DIVISIONS": {
        "380": "Gates of Lodore, Green River",
        "381": "Deerlodge Park, Yampa River"  # Likely 381 based on common patterns
    },
    
    # Date range to monitor (YYYY-MM-DD format)
    "START_DATE": "2025-05-01",
    "END_DATE": "2025-09-30",
    
    # Optional webhook for notifications (Discord, Slack, etc)
    "WEBHOOK_URL": "",  # Leave empty to just log to console/file
    
    # Files
    "DATABASE_FILE": "permit_availability.db",
    "LOG_FILE": "permit_monitor.log"
}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CONFIG["LOG_FILE"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PermitMonitorDB:
    """SQLite database handler for permit availability tracking"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create availability history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS availability_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date TEXT NOT NULL,
                    division_id TEXT NOT NULL,
                    division_name TEXT,
                    available INTEGER NOT NULL,
                    total INTEGER,
                    UNIQUE(date, division_id)
                )
            """)
            
            # Create notifications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notification_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date TEXT NOT NULL,
                    division_id TEXT NOT NULL,
                    division_name TEXT,
                    available INTEGER NOT NULL,
                    previous_available INTEGER,
                    message TEXT
                )
            """)
            
            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_availability_date 
                ON availability_history(date, division_id)
            """)
            
            conn.commit()
    
    def get_last_availability(self, date: str, division_id: str) -> Optional[int]:
        """Get the last recorded availability for a specific date and division"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT available 
                FROM availability_history 
                WHERE date = ? AND division_id = ?
                ORDER BY check_time DESC
                LIMIT 1
            """, (date, division_id))
            
            result = cursor.fetchone()
            return result[0] if result else None
    
    def record_availability(self, date: str, division_id: str, division_name: str, 
                          available: int, total: int = None):
        """Record current availability"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO availability_history 
                (date, division_id, division_name, available, total)
                VALUES (?, ?, ?, ?, ?)
            """, (date, division_id, division_name, available, total))
            conn.commit()
    
    def record_notification(self, date: str, division_id: str, division_name: str,
                          available: int, previous_available: Optional[int], message: str):
        """Record that a notification was sent"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notifications 
                (date, division_id, division_name, available, previous_available, message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (date, division_id, division_name, available, previous_available, message))
            conn.commit()
    
    def get_availability_summary(self) -> List[Dict]:
        """Get summary of current availability"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    date,
                    division_name,
                    available,
                    total,
                    check_time
                FROM availability_history
                WHERE (date, division_id, check_time) IN (
                    SELECT date, division_id, MAX(check_time)
                    FROM availability_history
                    GROUP BY date, division_id
                )
                AND available > 0
                ORDER BY date, division_name
            """)
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


class SimplePermitMonitor:
    def __init__(self, config: Dict):
        self.config = config
        self.db = PermitMonitorDB(config["DATABASE_FILE"])
        
        # Log configuration
        logger.info("=" * 60)
        logger.info("River Permit Monitor Starting")
        logger.info(f"Monitoring divisions: {list(config['DIVISIONS'].values())}")
        logger.info(f"Date range: {config['START_DATE']} to {config['END_DATE']}")
    
    def fetch_availability(self) -> Dict[str, Dict]:
        """Fetch permit availability from Recreation.gov API"""
        all_availabilities = {}
        
        headers = {
            "accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; PermitMonitor/1.0)"
        }
        
        # Add API key to headers if provided
        if self.config.get("API_KEY"):
            headers["apikey"] = self.config["API_KEY"]
        
        # Convert dates for API
        start_date = datetime.strptime(self.config["START_DATE"], "%Y-%m-%d")
        end_date = datetime.strptime(self.config["END_DATE"], "%Y-%m-%d")
        
        # Check each division
        for division_id, division_name in self.config["DIVISIONS"].items():
            try:
                logger.info(f"Checking {division_name} (Division {division_id})...")
                
                endpoint = f"https://www.recreation.gov/api/permits/{self.config['PERMIT_ID']}/divisions/{division_id}/availability"
                
                params = {
                    "start_date": start_date.strftime("%Y-%m-%dT06:00:00.000Z"),
                    "end_date": end_date.strftime("%Y-%m-%dT06:00:00.000Z"),
                    "commercial_acct": "false",
                    "is_lottery": "false"
                }
                
                response = requests.get(endpoint, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Parse availability data
                    if "payload" in data and "availability" in data["payload"]:
                        availability_data = data["payload"]["availability"]
                    elif "availability" in data:
                        availability_data = data["availability"]
                    else:
                        logger.warning(f"No availability data found for {division_name}")
                        continue
                    
                    # Process each date
                    for date_str, info in availability_data.items():
                        if isinstance(info, dict):
                            remaining = info.get("remaining", info.get("available", 0))
                            
                            # Store all dates, even with 0 availability, for tracking
                            date_key = f"{date_str}_{division_id}"
                            all_availabilities[date_key] = {
                                "date": date_str[:10],  # Just the date part
                                "division_id": division_id,
                                "division_name": division_name,
                                "available": remaining,
                                "total": info.get("total", 0)
                            }
                            
                            # Record in database
                            self.db.record_availability(
                                date_str[:10],
                                division_id,
                                division_name,
                                remaining,
                                info.get("total", 0)
                            )
                
                elif response.status_code == 401:
                    logger.error(f"Authentication failed for {division_name}")
                else:
                    logger.error(f"API error for {division_name}: Status {response.status_code}")
                    logger.debug(f"Response: {response.text[:500]}")
                    
            except Exception as e:
                logger.error(f"Error checking {division_name}: {e}")
                continue
        
        return all_availabilities
    
    def find_new_availabilities(self, current_data: Dict[str, Dict]) -> List[Tuple[str, str]]:
        """Find new or increased availability"""
        notifications = []
        
        # Check date range
        start_date = datetime.strptime(self.config["START_DATE"], "%Y-%m-%d")
        end_date = datetime.strptime(self.config["END_DATE"], "%Y-%m-%d")
        
        for key, info in current_data.items():
            date_str = info["date"]
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Skip if outside our date range
            if not (start_date <= date_obj <= end_date):
                continue
            
            # Skip if no availability
            if info["available"] <= 0:
                continue
            
            # Check previous availability
            previous = self.db.get_last_availability(date_str, info["division_id"])
            
            # New availability or increased availability
            if previous is None or previous == 0:
                # New availability!
                formatted_date = date_obj.strftime("%B %d, %Y")
                message = f"{formatted_date}: {info['available']} permits available at {info['division_name']}"
                
                notifications.append((date_str, message))
                
                # Record notification
                self.db.record_notification(
                    date_str,
                    info["division_id"],
                    info["division_name"],
                    info["available"],
                    previous,
                    message
                )
                
            elif info["available"] > previous:
                # Increased availability
                formatted_date = date_obj.strftime("%B %d, %Y")
                message = f"{formatted_date}: {info['available']} permits available at {info['division_name']} (was {previous})"
                
                notifications.append((date_str, message))
                
                # Record notification
                self.db.record_notification(
                    date_str,
                    info["division_id"],
                    info["division_name"],
                    info["available"],
                    previous,
                    message
                )
        
        return sorted(notifications)
    
    def send_webhook(self, message: str):
        """Send notification to webhook (Discord/Slack format)"""
        if not self.config["WEBHOOK_URL"]:
            return
            
        try:
            # Discord webhook format
            if "discord.com" in self.config["WEBHOOK_URL"]:
                payload = {
                    "content": message,
                    "username": "Permit Monitor"
                }
            # Slack webhook format
            elif "slack.com" in self.config["WEBHOOK_URL"]:
                payload = {
                    "text": message
                }
            else:
                # Generic format
                payload = {
                    "text": message,
                    "content": message
                }
            
            response = requests.post(self.config["WEBHOOK_URL"], json=payload)
            if response.status_code in [200, 204]:
                logger.info("Webhook notification sent successfully")
            else:
                logger.error(f"Webhook failed with status {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
    
    def run(self):
        """Main monitoring process"""
        logger.info("Starting permit availability check...")
        
        try:
            # Fetch current availability
            current_availabilities = self.fetch_availability()
            
            # Get summary of available permits
            available_count = sum(1 for info in current_availabilities.values() 
                                if info["available"] > 0)
            logger.info(f"Found {available_count} dates with availability across all divisions")
            
            # Find new availabilities
            new_availabilities = self.find_new_availabilities(current_availabilities)
            
            if new_availabilities:
                logger.info("🎉 NEW AVAILABILITY FOUND! 🎉")
                
                # Build notification message
                message = "🏕️ New River Permit Available!\n\n"
                for date, notification in new_availabilities:
                    logger.info(f"  → {notification}")
                    message += f"{notification}\n"
                
                message += f"\nBook now: https://www.recreation.gov/permits/{self.config['PERMIT_ID']}"
                
                # Send webhook
                self.send_webhook(message)
                
                # Also print to console
                print("\n" + "!" * 60)
                print("NEW PERMITS AVAILABLE!")
                print("!" * 60)
                for _, notification in new_availabilities:
                    print(f"→ {notification}")
                print(f"\nBook at: https://www.recreation.gov/permits/{self.config['PERMIT_ID']}")
                print("!" * 60 + "\n")
                
            else:
                logger.info("No new availabilities found")
            
            # Log summary
            logger.info("-" * 40)
            logger.info("Current availability summary:")
            summary = self.db.get_availability_summary()
            if summary:
                for entry in summary:
                    logger.info(f"  {entry['date']}: {entry['available']} permits at {entry['division_name']}")
            else:
                logger.info("  No permits currently available")
            
            logger.info("Check complete")
            
        except Exception as e:
            logger.error(f"Error during monitoring: {e}")
            raise


def main():
    """Main entry point"""
    # Override with environment variables if set
    if "WEBHOOK_URL" in os.environ:
        CONFIG["WEBHOOK_URL"] = os.environ["WEBHOOK_URL"]
    
    # Run monitor
    try:
        monitor = SimplePermitMonitor(CONFIG)
        monitor.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()