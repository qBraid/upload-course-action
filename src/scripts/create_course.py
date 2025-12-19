import json
import requests
import sys
import os
from config import API_BASE_URL

def create_course(api_key, article_type='course'):
    if not os.path.exists('course_data.json'):
        print("ERROR: course_data.json not found. Run validation first.")
        sys.exit(1)

    with open('course_data.json', 'r') as f:
        course_data = json.load(f)

    # Validate article_type
    if article_type not in ['course', 'blog']:
        print(f"WARNING: Invalid article type '{article_type}'. Defaulting to 'course'.")
        article_type = 'course'

    print(f"Creating article of type: {article_type}")

    # Call qBraid API to create course
    try:
        response = requests.post(
            f'{API_BASE_URL}/api/v1/learn/articles/{article_type}',
            json={'data': course_data,'forceDuplicateQuestions':True},
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

        # Generate qBook URL
        try:
            article_id = response_data['article']['_id']
            # Get the first chapter's ID (file ID)
            first_chapter_id = response_data['article']['content'][0]['_id']
            
            qbook_url = f"https://qbook.qbraid.com/learn/?article={article_id}&file={first_chapter_id}"
            print(f"qBook URL: {qbook_url}")

            # Set output for GitHub Actions
            if 'GITHUB_OUTPUT' in os.environ:
                with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                    f.write(f"qbook_url={qbook_url}\n")
        except (KeyError, IndexError) as e:
            print(f"WARNING: Could not generate qBook URL from response: {e}")
        
    except Exception as e:
        print(f"ERROR: Exception during API call: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_course.py <api_key> [article_type]")
        sys.exit(1)
    
    api_key = sys.argv[1]
    article_type = sys.argv[2] if len(sys.argv) > 2 else 'course'
    
    create_course(api_key, article_type)
