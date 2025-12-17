import requests
import time
import sys
import os
from config import WORKER_BASE_URL

def poll_worker(api_key, formatted_name):
    worker_url = WORKER_BASE_URL
    
    max_attempts = 60  # Poll for up to 30 minutes (60 * 30 seconds)
    attempt = 0
    
    print(f"Polling worker service at {worker_url}...")
    
    while attempt < max_attempts:
        attempt += 1
        
        try:
            response = requests.get(
                f'{worker_url}/status/{formatted_name}',
                headers={'Authorization': f'Bearer {api_key}'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'qbookUrl' in data:
                    qbook_url = data['qbookUrl']
                    print(f"✅ Course processing complete!")
                    print(f"qBook URL: {qbook_url}")
                    
                    if 'GITHUB_OUTPUT' in os.environ:
                        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                            f.write(f"qbook_url={qbook_url}\n")
                    
                    sys.exit(0)
            
            print(f"Attempt {attempt}/{max_attempts}: Still processing...")
            time.sleep(30)  # Wait 30 seconds between polls
            
        except Exception as e:
            print(f"Error polling worker: {e}")
            time.sleep(30)
    
    print("ERROR: Worker service did not complete within the timeout period")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python poll_worker.py <api_key> <formatted_name>")
        sys.exit(1)
    poll_worker(sys.argv[1], sys.argv[2])
