#!/usr/bin/env python3
"""
Test script to verify Telegram bot configuration
"""

import requests
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_telegram_bot(token, channel_id):
    """Test sending a message to verify bot configuration"""
    
    print(f"Testing bot token: {token[:10]}...")
    print(f"Testing channel ID: {channel_id}")
    
    # First, test if the bot token is valid
    bot_info_url = f"https://api.telegram.org/bot{token}/getMe"
    
    try:
        resp = requests.get(bot_info_url)
        if resp.status_code == 200:
            bot_data = resp.json()
            if bot_data.get('ok'):
                bot_name = bot_data['result']['username']
                print(f"✓ Bot token is valid! Bot username: @{bot_name}")
            else:
                print("✗ Bot token is invalid!")
                return False
        else:
            print(f"✗ Failed to verify bot token: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error verifying bot token: {e}")
        return False
    
    # Now try to send a test message
    send_url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    test_message = {
        "chat_id": channel_id,
        "text": "🧪 <b>Test Message</b>\n\nThis is a test message from the River Permit Bot.\nIf you see this, your bot is configured correctly!",
        "parse_mode": "HTML"
    }
    
    try:
        resp = requests.post(send_url, json=test_message)
        if resp.status_code == 200:
            result = resp.json()
            if result.get('ok'):
                print("✓ Test message sent successfully!")
                print(f"  Message ID: {result['result']['message_id']}")
                return True
            else:
                error = result.get('description', 'Unknown error')
                print(f"✗ Failed to send message: {error}")
                
                if "chat not found" in error.lower():
                    print("\n  Hint: Make sure the bot is added as an admin to your channel/group")
                elif "chat_id is empty" in error.lower():
                    print("\n  Hint: Check your channel ID format")
                
                return False
        else:
            print(f"✗ HTTP error: {resp.status_code}")
            print(f"  Response: {resp.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error sending message: {e}")
        return False

def main():
    print("Telegram Bot Configuration Test")
    print("=" * 40)
    
    # You can either:
    # 1. Pass token and channel as arguments
    # 2. Or edit these values directly
    
    if len(sys.argv) == 3:
        token = sys.argv[1]
        channel_id = sys.argv[2]
    else:
        # Default values from environment
        token = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
        channel_id = os.getenv('TELEGRAM_CHANNEL_ID', '@your_channel_id')
        
        if token == "YOUR_BOT_TOKEN_HERE":
            print("Usage: python test_telegram.py <bot_token> <channel_id>")
            print("Or edit the token and channel_id in this script")
            return
    
    test_telegram_bot(token, channel_id)

if __name__ == "__main__":
    main()