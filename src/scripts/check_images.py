import json
import os
import sys
import nbformat
import re

def check_notebook_images(notebook_path, missing_images):
    """Check all image references in a notebook"""
    notebook_dir = os.path.dirname(notebook_path)
    
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
        
        # Check absolute path from repo root
        if img_ref.startswith('/'):
            abs_path = img_ref[1:]  # Remove leading /
            if not os.path.exists(abs_path):
                missing_images.append({
                    'notebook': notebook_path,
                    'image': img_ref,
                    'type': 'absolute'
                })
        else:
            # Check relative path from notebook directory
            rel_path = os.path.join(notebook_dir, img_ref)
            if not os.path.exists(rel_path):
                missing_images.append({
                    'notebook': notebook_path,
                    'image': img_ref,
                    'type': 'relative'
                })

def verify_images():
    if not os.path.exists('course_data.json'):
        print("ERROR: course_data.json not found. Run validation first.")
        sys.exit(1)

    with open('course_data.json', 'r') as f:
        course_data = json.load(f)

    missing_images = []

    # Check all notebooks
    for chapter in course_data['content']:
        file_path = chapter['file_path']
        check_notebook_images(file_path, missing_images)
        
        if 'sections' in chapter:
            for section in chapter['sections']:
                section_path = section['file_path']
                check_notebook_images(section_path, missing_images)

    if missing_images:
        print("ERROR: The following image references are missing:")
        for item in missing_images:
            print(f"  Notebook: {item['notebook']}")
            print(f"    Missing {item['type']} path: {item['image']}")
        sys.exit(1)

    print("✅ All image references in notebooks are valid")

if __name__ == "__main__":
    verify_images()
