import requests
import sys
import json
from config import API_BASE_URL

def validate_api_key(api_key):
    """
    Validate the qBraid API key using the verification endpoint.
    """
    verify_url = f'{API_BASE_URL}/api/v1/users/verify'
    
    print(f"Validating API key against {verify_url}...")
    
    try:
        # The user specified X-API-Key header in the request description
        response = requests.get(
            verify_url,
            headers={'X-API-Key': api_key},
            timeout=10  # Add timeout to prevent hanging
        )
        
        if response.status_code == 200:
            print("✅ API key is valid.")
            try:
                user_data = response.json()
                # Print user info if available, but be careful not to log sensitive data
                if 'email' in user_data:
                    print(f"Authenticated as: {user_data['email']}")
            except:
                pass
            sys.exit(0)
        elif response.status_code == 401:
            print("❌ Error: Invalid API key. Please check your QBRAID_API_KEY secret.")
            sys.exit(1)
        else:
            print(f"❌ Error: API key validation failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)
            
    except requests.exceptions.Timeout:
        print("❌ Error: Request timed out. The API is not responding.")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to qBraid API. Please check your network connection.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: Exception during API key validation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_api_key.py <api_key>")
        sys.exit(1)
    
    validate_api_key(sys.argv[1])
