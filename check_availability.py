#!/usr/bin/env python3
"""
Check availability for River Permit divisions
"""

import requests
import json
from time import sleep
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('RECREATION_API_KEY', '5b106992-95c4-4b77-b6b5-0b60ed0ffb89')

# Multiple permits configuration
PERMITS = {
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

def check_division(permit_id, division_id, start_date="2025-07-01", end_date="2025-07-31"):
    """Check availability for a specific division"""
    
    url = f"https://www.recreation.gov/api/permits/{permit_id}/divisions/{division_id}/availability"
    params = {
        "start_date": f"{start_date}T06:00:00.000Z",
        "end_date": f"{end_date}T06:00:00.000Z",
        "commercial_acct": "false",
        "is_lottery": "false"
    }
    
    # Add API key
    if API_KEY:
        session.headers['apikey'] = API_KEY
    
    try:
        resp = session.get(url, params=params, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            
            if 'payload' in data and 'date_availability' in data['payload']:
                dates = data['payload']['date_availability']
                available_dates = []
                
                for date_str, info in dates.items():
                    if info.get('remaining', 0) > 0:
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        available_dates.append({
                            'date': date_obj.strftime('%Y-%m-%d'),
                            'remaining': info['remaining'],
                            'total': info['total']
                        })
                
                return {
                    'status': 'success',
                    'total_dates': len(dates),
                    'available_dates': available_dates,
                    'next_available': data['payload'].get('next_available_date')
                }
            else:
                return {'status': 'error', 'message': 'Unexpected response format'}
        else:
            return {'status': 'error', 'message': f'HTTP {resp.status_code}'}
            
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def main():
    print("Checking River Permit Availability")
    print("=" * 50)
    print(f"Date Range: July 2025")
    print("=" * 50)
    
    for permit_id, permit_config in PERMITS.items():
        permit_name = permit_config['name']
        print(f"\n{permit_name} (#{permit_id}):")
        print("-" * 40)
        
        for div_id, div_name in permit_config['divisions'].items():
            print(f"\n  {div_name}:")
            result = check_division(permit_id, div_id)
            
            if result['status'] == 'success':
                print(f"    Total dates checked: {result['total_dates']}")
                print(f"    Available dates: {len(result['available_dates'])}")
                
                if result['available_dates']:
                    print("\n    Available dates:")
                    for date_info in result['available_dates']:
                        print(f"      - {date_info['date']}: {date_info['remaining']} of {date_info['total']} spots")
                else:
                    print("    No availability in this date range")
            else:
                print(f"    Error: {result['message']}")
            
            sleep(0.5)  # Rate limiting

if __name__ == "__main__":
    main()