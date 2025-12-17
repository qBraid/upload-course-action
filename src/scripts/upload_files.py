import os
import sys
import json
import requests
from glob import glob
import fnmatch
from config import API_BASE_URL

def get_signed_urls(api_key, files, course_name):
    """
    Request signed URLs for a list of files from qBraid API.
    """
    api_url = f'{API_BASE_URL}/learn/signed-urls'
    
    payload = {
        'courseName': course_name,
        'files': files
    }
    
    try:
        response = requests.post(
            api_url,
            json=payload,
            headers={'X-API-Key': api_key} 
        )
        
        if response.status_code != 200:
            print(f"ERROR: Failed to get signed URLs. Status: {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)
            
        return response.json()
    except Exception as e:
        print(f"ERROR: Exception while requesting signed URLs: {e}")
        sys.exit(1)

def upload_files(api_key, source_path, exclude_patterns_str, formatted_course_name):
    # Resolve source path
    resolved_source_path = os.path.abspath(source_path)
    if not os.path.exists(resolved_source_path):
        print(f"ERROR: Source path does not exist: {resolved_source_path}")
        sys.exit(1)

    # Get files to upload
    files_to_upload = []
    if os.path.isfile(resolved_source_path):
        files_to_upload.append(resolved_source_path)
    else:
        # Glob all files
        all_files = glob(os.path.join(resolved_source_path, '**/*'), recursive=True)
        
        exclude_patterns = [p.strip() for p in exclude_patterns_str.split(',') if p.strip()]
        
        for f in all_files:
            if os.path.isfile(f):
                rel_path = os.path.relpath(f, resolved_source_path)
                excluded = False
                for pattern in exclude_patterns:
                    if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(os.path.basename(f), pattern):
                        excluded = True
                        break
                    if pattern.endswith('**'):
                        dir_pattern = pattern[:-2]
                        if rel_path.startswith(dir_pattern):
                            excluded = True
                            break
                
                if not excluded:
                    files_to_upload.append(f)

    if not files_to_upload:
        print("WARNING: No files found to upload")
        return

    print(f"Found {len(files_to_upload)} files to upload")
    
    # Prepare list of relative paths for API
    relative_paths = []
    path_map = {} # Map relative path to absolute path
    
    for f in files_to_upload:
        rel_path = os.path.relpath(f, resolved_source_path)
        # Normalize to forward slashes
        normalized_path = rel_path.replace(os.sep, '/')
        relative_paths.append(normalized_path)
        path_map[normalized_path] = f

    # Get signed URLs
    print("Requesting signed upload URLs...")
    # Note: This assumes the API returns a dict: { "filePath": "signedUrl", ... }
    signed_urls = get_signed_urls(api_key, relative_paths, formatted_course_name)
    
    print(f"Received {len(signed_urls)} signed URLs")

    uploaded_count = 0
    for rel_path, signed_url in signed_urls.items():
        if rel_path not in path_map:
            print(f"WARNING: Received URL for unknown file: {rel_path}")
            continue
            
        abs_path = path_map[rel_path]
        
        try:
            print(f"Uploading: {rel_path}")
            with open(abs_path, 'rb') as f:
                # Use PUT for signed URLs (standard for GCS/S3)
                response = requests.put(
                    signed_url,
                    data=f,
                    headers={'Content-Type': 'application/octet-stream'} 
                )
                
                if response.status_code not in [200, 201]:
                    print(f"ERROR: Failed to upload {rel_path}. Status: {response.status_code}")
                    # Continue uploading other files? Or fail? 
                    # Let's fail to ensure consistency
                    sys.exit(1)
                    
            uploaded_count += 1
        except Exception as e:
            print(f"ERROR: Failed to upload {rel_path}: {e}")
            sys.exit(1)

    print(f"✅ Successfully uploaded {uploaded_count} files")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python upload_files.py <api_key> <source_path> <exclude_patterns> <formatted_course_name>")
        sys.exit(1)
    
    upload_files(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
