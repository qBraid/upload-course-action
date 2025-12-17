import os
import sys
import json
import requests
import nbformat
import re
import fnmatch
from config import API_BASE_URL

def get_signed_urls(api_key, files, course_name):
    """
    Request signed URLs for a list of files from qBraid API.
    """
    api_url = f'{API_BASE_URL}/api/v1/learn/articles/signed-urls'
    
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

def get_notebook_assets(notebook_path):
    """Extract local image/asset paths from a notebook file."""
    assets = []
    notebook_dir = os.path.dirname(notebook_path)
    
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
    except Exception as e:
        print(f"WARNING: Could not read notebook {notebook_path}: {e}")
        return assets

    images_to_check = []
    for cell in nb.cells:
        if cell.cell_type == 'markdown':
            # Find markdown image references: ![alt](path)
            md_images = re.findall(r'!\[.*?\]\((.*?)\)', cell.source)
            images_to_check.extend(md_images)
            
            # Find HTML img tags: <img src="path">
            html_images = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', cell.source)
            images_to_check.extend(html_images)
    
    for img_ref in images_to_check:
        # Skip URLs
        if img_ref.startswith('http://') or img_ref.startswith('https://'):
            continue
        
        # Resolve path
        if img_ref.startswith('/'):
            # Absolute path from repo root (remove leading /)
            # Note: We assume the script runs from repo root or we need to handle this carefully.
            # But here we are returning absolute paths.
            # If img_ref starts with /, it's usually relative to the root of the Jupyter server, 
            # which often maps to the repo root in this context.
            abs_path = os.path.abspath(img_ref[1:])
        else:
            # Relative path from notebook directory
            abs_path = os.path.abspath(os.path.join(notebook_dir, img_ref))
            
        if os.path.exists(abs_path):
            assets.append(abs_path)
            
    return assets

def upload_files(api_key, source_path, exclude_patterns_str, formatted_course_name):
    # Resolve source path (repo root)
    resolved_source_path = os.path.abspath(source_path)
    if not os.path.exists(resolved_source_path):
        print(f"ERROR: Source path does not exist: {resolved_source_path}")
        sys.exit(1)

    # Load course_data.json to identify required files
    if not os.path.exists('course_data.json'):
        print("ERROR: course_data.json not found. Run validation first.")
        sys.exit(1)

    with open('course_data.json', 'r') as f:
        course_data = json.load(f)

    # Collect files to upload
    files_to_upload = set()
    
    # 1. Add course.json (assuming it's in the root or we know its path)
    course_json_path = os.path.join(resolved_source_path, 'course.json')
    if os.path.exists(course_json_path):
        files_to_upload.add(course_json_path)

    # 2. Add notebooks and their assets
    for chapter in course_data.get('content', []):
        # Add chapter notebook
        if 'baseFilePath' in chapter:
            nb_path = os.path.abspath(os.path.join(resolved_source_path, chapter['baseFilePath']))
            if os.path.exists(nb_path):
                files_to_upload.add(nb_path)
                # Add assets from this notebook
                assets = get_notebook_assets(nb_path)
                files_to_upload.update(assets)
        
        # Add section notebooks
        if 'sections' in chapter:
            for section in chapter['sections']:
                if 'baseFilePath' in section:
                    nb_path = os.path.abspath(os.path.join(resolved_source_path, section['baseFilePath']))
                    if os.path.exists(nb_path):
                        files_to_upload.add(nb_path)
                        # Add assets from this notebook
                        assets = get_notebook_assets(nb_path)
                        files_to_upload.update(assets)

    if not files_to_upload:
        print("WARNING: No files found to upload")
        return

    print(f"Found {len(files_to_upload)} files to upload (notebooks + assets + course.json)")
    
    # Prepare list of relative paths for API
    relative_paths = []
    path_map = {} # Map relative path to absolute path
    
    exclude_patterns = [p.strip() for p in exclude_patterns_str.split(',') if p.strip()]

    for f in files_to_upload:
        rel_path = os.path.relpath(f, resolved_source_path)
        
        # Apply exclude patterns just in case
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
        
        if excluded:
            continue

        # Normalize to forward slashes
        normalized_path = rel_path.replace(os.sep, '/')
        relative_paths.append(normalized_path)
        path_map[normalized_path] = f

    if not relative_paths:
        print("WARNING: No files left to upload after exclusion")
        return

    # Get signed URLs
    print("Requesting signed upload URLs...")
    signed_urls = get_signed_urls(api_key, relative_paths, formatted_course_name)
    
    print(f"Received {len(signed_urls)} signed URLs")

    uploaded_count = 0
    for rel_path, signed_url in signed_urls.items():
        if rel_path not in path_map:
            print(f"WARNING: Received URL for unknown file: {rel_path}")
            continue
            
        file_path = path_map[rel_path]
        print(f"Uploading {rel_path}...")
        
        try:
            with open(file_path, 'rb') as f:
                upload_response = requests.put(
                    signed_url,
                    data=f,
                    headers={'Content-Type': 'application/octet-stream'}
                )
                
                if upload_response.status_code == 200:
                    uploaded_count += 1
                else:
                    print(f"ERROR: Failed to upload {rel_path}. Status: {upload_response.status_code}")
        except Exception as e:
            print(f"ERROR: Exception uploading {rel_path}: {e}")

    print(f"Successfully uploaded {uploaded_count}/{len(relative_paths)} files")
    
    if uploaded_count < len(relative_paths):
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python upload_files.py <api_key> <source_path> <exclude_patterns> <formatted_course_name>")
        sys.exit(1)
    
    upload_files(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
