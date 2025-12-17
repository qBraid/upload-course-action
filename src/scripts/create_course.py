import json
import requests
import sys
import os
from config import API_BASE_URL

def create_course(api_key):
    if not os.path.exists('course_data.json'):
        print("ERROR: course_data.json not found. Run validation first.")
        sys.exit(1)

    with open('course_data.json', 'r') as f:
        course_data = json.load(f)

    # Call qBraid API to create course
    try:
        response = requests.post(
            f'{API_BASE_URL}/learn/create',
            json={'data': course_data},
            headers={'X-API-Key': api_key} 
        )
        
        if response.status_code != 201:
            print(f"ERROR: Failed to create course. Status: {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)
        
        print("✅ Course created successfully via qBraid API")
        
        # Extract course ID or other info if needed
        response_data = response.json()
        print(f"API Response: {json.dumps(response_data, indent=2)}")
        
    except Exception as e:
        print(f"ERROR: Exception during API call: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_course.py <api_key>")
        sys.exit(1)
    create_course(sys.argv[1])
