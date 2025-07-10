#!/usr/bin/env python3
"""
Quick script to find the correct division IDs
"""

import requests
import json
from time import sleep
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('RECREATION_API_KEY', '5b106992-95c4-4b77-b6b5-0b60ed0ffb89')
PERMIT_ID = "250014"

# Create a session with browser-like headers
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Origin': 'https://www.recreation.gov',
    'Referer': 'https://www.recreation.gov/',
    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"macOS"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin'
})

# Try a range of division IDs
for div_id in range(370, 385):
    print(f"\nTrying division {div_id}...")
    
    url = f"https://www.recreation.gov/api/permits/{PERMIT_ID}/divisions/{div_id}/availability"
    params = {
        "start_date": "2025-07-01T06:00:00.000Z",
        "end_date": "2025-07-31T06:00:00.000Z",
        "commercial_acct": "false",
        "is_lottery": "false"
    }
    
    headers = {
        "accept": "application/json",
        "apikey": API_KEY
    }
    
    try:
        # Add API key to session headers if available
        if API_KEY:
            session.headers['apikey'] = API_KEY
        
        resp = session.get(url, params=params, timeout=10)
        sleep(0.5)  # Rate limiting
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            
            # Check if it's date data
            if isinstance(data, dict):
                keys = list(data.keys())
                print(f"✓ FOUND! Division {div_id} - Response keys: {keys}")
                
                # Check for payload structure
                if 'payload' in data:
                    payload = data['payload']
                    if isinstance(payload, dict):
                        print(f"  Payload has {len(payload)} entries")
                        # Show first few entries
                        for i, (key, value) in enumerate(payload.items()):
                            if i < 3:
                                print(f"  {key}: {value}")
                elif keys and keys[0].startswith('20'):
                    # Direct date data
                    available = sum(1 for v in data.values() if isinstance(v, dict) and v.get('remaining', 0) > 0)
                    print(f"  Has {len(data)} dates, {available} with availability")
                    
                    # Show a sample
                    for i, (date, info) in enumerate(data.items()):
                        if i < 3:
                            print(f"  {date}: {info}")
                        else:
                            break
                            
    except Exception as e:
        print(f"Error: {e}")

# Also try without API key
print("\n\nTrying without API key...")
for div_id in [371, 380]:
    print(f"\nDivision {div_id} without API key...")
    
    url = f"https://www.recreation.gov/api/permits/{PERMIT_ID}/divisions/{div_id}/availability"
    params = {
        "start_date": "2025-07-01T06:00:00.000Z",
        "end_date": "2025-07-31T06:00:00.000Z",
        "commercial_acct": "false",
        "is_lottery": "false"
    }
    
    headers = {
        "accept": "application/json"
    }
    
    try:
        # Remove API key from headers
        if 'apikey' in session.headers:
            del session.headers['apikey']
        
        resp = session.get(url, params=params, timeout=10)
        sleep(0.5)  # Rate limiting
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                keys = list(data.keys())
                print(f"Response keys: {keys}")
                
                if 'payload' in data:
                    payload = data['payload']
                    if isinstance(payload, dict):
                        print(f"Payload has {len(payload)} entries")
                        # Show first few entries
                        for i, (key, value) in enumerate(payload.items()):
                            if i < 3:
                                print(f"  {key}: {value}")
                
    except Exception as e:
        print(f"Error: {e}")