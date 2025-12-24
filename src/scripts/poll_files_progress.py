import requests
import time
import sys
import os
from config import API_BASE_URL

def poll_worker(api_key, course_custom_id):
    
    max_attempts = 60  # Poll for up to 30 minutes (60 * 30 seconds)
    attempt = 0
    error_count = 0

    while attempt < max_attempts:
        attempt += 1
        
        try:
            response = requests.get(
                f'{API_BASE_URL}/learn/articles/files/status/{course_custom_id}',
                headers={'Authorization': f'Bearer {api_key}'}
            )
            
            if response.status_code == 200:
                error_count = 0
                data = response.json()
                if 'qbookUrl' in data:
                    qbook_url = data['qbookUrl']
                    print(f"✅ Course processing complete!")
                    print(f"qBook URL: {qbook_url}")
                    
                    if 'GITHUB_OUTPUT' in os.environ:
                        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                            f.write(f"qbook_url={qbook_url}\n")
                if status in data:
                    status = data['status']
                    match status:
                        case 'unprocessed':
                            print(f"Attempt {attempt}/{max_attempts}: Course files are unprocessed...")
                        case 'processing':
                            print(f"Attempt {attempt}/{max_attempts}: Course files are still being processed...")
                        case 'failed':
                            print("❌ Course file processing failed. Please check the logs for more details. or contact support. at contact@qbraid.com")
                            sys.exit(1)
                        case 'processed':
                            print("✅ Course processing complete!") 
                            sys.exit(0)
                        case _:
                            print(f"Attempt {attempt}/{max_attempts}: Unknown status '{status}'")
                    
            else:
                error_count += 1
                print(f"Attempt {attempt}/{max_attempts}: Received unexpected status code {response.status_code}")
                if error_count > 5:
                    print("ERROR: Too many consecutive errors polling worker. Terminating.")
                    sys.exit(1)
            
            time.sleep(30)  # Wait 30 seconds between polls
            
        except Exception as e:
            error_count += 1
            print(f"Error polling worker: {e}")
            if error_count > 5:
                print("ERROR: Too many consecutive errors polling worker. Terminating.")
                sys.exit(1)
            time.sleep(30)
    
    print("ERROR: Worker service did not complete within the timeout period")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python poll_worker.py <api_key> <formatted_name>")
        sys.exit(1)
    poll_worker(sys.argv[1], sys.argv[2])
