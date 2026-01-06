import json
import os
import sys
import nbformat
import re

def check_notebook_images(notebook_path, image_issues):
    """Check all image references in a notebook"""
    notebook_dir = os.path.dirname(notebook_path)
    if not notebook_dir:  # Handle case where notebook is in root directory
        notebook_dir = '.'
    MAX_SIZE_MB = 1
    MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024
    
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
    except Exception as e:
        print(f"WARNING: Could not read notebook {notebook_path}: {e}")
        return

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
        
        file_path_to_check = None
        
        # Check absolute path from repo root
        if img_ref.startswith('/'):
            abs_path = img_ref[1:]  # Remove leading /
            if not os.path.exists(abs_path):
                image_issues.append({
                    'notebook': notebook_path,
                    'image': img_ref,
                    'issue': 'missing',
                    'type': 'absolute'
                })
            else:
                file_path_to_check = abs_path
            
        else:
            # Check relative path from notebook directory
            rel_path = os.path.join(notebook_dir, img_ref)
            if not os.path.exists(rel_path):
                image_issues.append({
                    'notebook': notebook_path,
                    'image': img_ref,
                    'issue': 'missing',
                    'type': 'relative'
                })
            else:
                file_path_to_check = rel_path
        
        if file_path_to_check:
            try:
                size = os.path.getsize(file_path_to_check)
                if size > MAX_SIZE_BYTES:
                    image_issues.append({
                        'notebook': notebook_path,
                        'image': img_ref,
                        'issue': 'oversized',
                        'size': size,
                        'max_size': MAX_SIZE_BYTES
                    })
            except OSError as e:
                print(f"WARNING: Could not check size of {file_path_to_check}: {e}")

def verify_images():
    if not os.path.exists('course_data.json'):
        print("ERROR: course_data.json not found. Run validation first.")
        sys.exit(1)

    with open('course_data.json', 'r') as f:
        course_data = json.load(f)

    image_issues = []

    # Check all notebooks
    for chapter in course_data['content']:
        file_path = chapter['baseFilePath']
        check_notebook_images(file_path, image_issues)
        
        if 'sections' in chapter:
            for section in chapter['sections']:
                section_path = section['baseFilePath']
                check_notebook_images(section_path, image_issues)

    if image_issues:
        print("ERROR: Found issues with image references:")
        for item in image_issues:
            if item['issue'] == 'missing':
                print(f"  Notebook: {item['notebook']}")
                print(f"    Missing {item['type']} path: {item['image']}")
            elif item['issue'] == 'oversized':
                size_mb = item['size'] / (1024 * 1024)
                print(f"  Notebook: {item['notebook']}")
                print(f"    Image too large ({size_mb:.2f}MB > 1MB): {item['image']}")
        sys.exit(1)

    print("✅ All image references in notebooks are valid")

if __name__ == "__main__":
    verify_images()
