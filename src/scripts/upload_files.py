import os
import sys
import json
import requests
import nbformat
import re
import shutil
import tempfile
from config import API_BASE_URL

def sanitize_name(name):
    """Sanitize string to be used as directory name."""
    # Replace spaces with underscores, remove non-alphanumeric (except _ and -)
    s = re.sub(r'[^a-zA-Z0-9_-]', '', name.replace(' ', '_'))
    return s if s else 'unnamed'

def get_signed_urls(api_key, zipFile, course_name):
    """
    Request signed URLs for a list of files from qBraid API.
    """
    api_url = f'{API_BASE_URL}/api/v1/learn/article/signed-url'
    
    payload = {
        'courseName': course_name,
        'file': zipFile
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

def process_notebook(src_path, dest_dir, assets_dir_name="assets_folder"):
    """
    Reads a notebook, extracts images, copies them to assets folder,
    updates image links, and saves the notebook to dest_dir.
    Returns the filename of the saved notebook.
    """
    if not os.path.exists(src_path):
        print(f"WARNING: Notebook not found: {src_path}")
        return None

    try:
        with open(src_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
    except Exception as e:
        print(f"ERROR: Could not read notebook {src_path}: {e}")
        return None

    notebook_dir = os.path.dirname(src_path)
    assets_dir = os.path.join(dest_dir, assets_dir_name)
    
    # Ensure assets directory exists if we find images
    assets_created = False

    # Helper to process image path
    def process_image_path(img_path):
        nonlocal assets_created
        
        # Skip URLs
        if img_path.startswith('http://') or img_path.startswith('https://'):
            return img_path
            
        # Resolve absolute path of the source image
        if img_path.startswith('/'):
            # Assuming absolute path from repo root
            # We need to know repo root. Assuming script runs from repo root.
            src_img_abs = os.path.abspath(img_path[1:])
        else:
            src_img_abs = os.path.abspath(os.path.join(notebook_dir, img_path))
            
        if not os.path.exists(src_img_abs):
            print(f"WARNING: Image not found: {src_img_abs} (referenced in {src_path})")
            return img_path # Keep original if not found

        # Create assets dir if needed
        if not assets_created:
            os.makedirs(assets_dir, exist_ok=True)
            assets_created = True

        # Determine destination filename (handle collisions)
        img_filename = os.path.basename(src_img_abs)
        dest_img_path = os.path.join(assets_dir, img_filename)
        
        # If file exists and is different, rename
        if os.path.exists(dest_img_path):
            # Simple check: if paths are different, assume content might be different
            # For now, just append a counter if it's not the exact same file path we processed before
            # But we are in a fresh temp dir, so collision means same filename from different sources
            base, ext = os.path.splitext(img_filename)
            counter = 1
            while os.path.exists(os.path.join(assets_dir, f"{base}_{counter}{ext}")):
                counter += 1
            img_filename = f"{base}_{counter}{ext}"
            dest_img_path = os.path.join(assets_dir, img_filename)

        # Copy image
        shutil.copy2(src_img_abs, dest_img_path)
        
        # Return new relative path
        return f"{assets_dir_name}/{img_filename}"

    # Iterate cells and update references
    for cell in nb.cells:
        if cell.cell_type == 'markdown':
            # Update Markdown image references: ![alt](path)
            cell.source = re.sub(
                r'(!\[.*?\]\()(.+?)(\))',
                lambda m: f"{m.group(1)}{process_image_path(m.group(2))}{m.group(3)}",
                cell.source
            )
            
            # Update HTML img tags: <img src="path">
            cell.source = re.sub(
                r'(<img[^>]+src=["\'])(.+?)(["\'])',
                lambda m: f"{m.group(1)}{process_image_path(m.group(2))}{m.group(3)}",
                cell.source
            )

    # Save updated notebook
    nb_filename = os.path.basename(src_path)
    dest_nb_path = os.path.join(dest_dir, nb_filename)
    
    with open(dest_nb_path, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)
        
    return nb_filename

def upload_files(api_key, source_path, exclude_patterns_str, formatted_course_name):
    # Resolve source path (repo root)
    resolved_source_path = os.path.abspath(source_path)
    
    if not os.path.exists('course_data.json'):
        print("ERROR: course_data.json not found. Run validation first.")
        sys.exit(1)

    with open('course_data.json', 'r') as f:
        course_data = json.load(f)

    # Create a temporary directory for the course package
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created temporary directory: {temp_dir}")
        
        # 1. Process Chapters
        for chapter in course_data.get('content', []):
            chapter_name = chapter.get('chapterName', 'Untitled_Chapter')
            safe_chapter_name = sanitize_name(chapter_name)
            
            chapter_dir = os.path.join(temp_dir, safe_chapter_name)
            os.makedirs(chapter_dir, exist_ok=True)
            
            # Process Chapter Notebook
            if 'baseFilePath' in chapter:
                src_nb = os.path.join(resolved_source_path, chapter['baseFilePath'])
                new_nb_name = process_notebook(src_nb, chapter_dir)
                
                if new_nb_name:
                    # Update course_data with new relative path
                    chapter['baseFilePath'] = f"{safe_chapter_name}/{new_nb_name}"
            
            # Process Sections
            if 'sections' in chapter:
                section_folder_dir = os.path.join(chapter_dir, 'section_folder')
                
                for section in chapter['sections']:
                    section_name = section.get('sectionName', 'Untitled_Section')
                    safe_section_name = sanitize_name(section_name)
                    
                    section_dir = os.path.join(section_folder_dir, safe_section_name)
                    os.makedirs(section_dir, exist_ok=True)
                    
                    if 'baseFilePath' in section:
                        src_nb = os.path.join(resolved_source_path, section['baseFilePath'])
                        new_nb_name = process_notebook(src_nb, section_dir)
                        
                        if new_nb_name:
                            # Update course_data with new relative path
                            # Path is Chapter/section_folder/Section/notebook.ipynb
                            section['baseFilePath'] = f"{safe_chapter_name}/section_folder/{safe_section_name}/{new_nb_name}"

        # 2. Save updated course.json to root of temp dir
        with open(os.path.join(temp_dir, 'course.json'), 'w') as f:
            json.dump(course_data, f, indent=2)
            
        # 3. Create Zip Archive
        zip_filename = f"{formatted_course_name}.zip"
        zip_path = os.path.join(os.getcwd(), zip_filename)
        
        print(f"Creating archive: {zip_path}")
        shutil.make_archive(os.path.splitext(zip_path)[0], 'zip', temp_dir)
        
        if not os.path.exists(zip_path):
            print("ERROR: Failed to create zip archive")
            sys.exit(1)
            
        print(f"Archive created successfully. Size: {os.path.getsize(zip_path) / 1024 / 1024:.2f} MB")

        # 4. Upload Zip
        print("Requesting signed upload URL for archive...")
        # Pass filename as string
        response_data = get_signed_urls(api_key, zip_filename, formatted_course_name)
        
        upload_url = None
        if 'signedURL' in response_data:
            upload_url = response_data['signedURL']
        
        if not upload_url:
            print(f"ERROR: API did not return signed URL. Response: {response_data}")
            sys.exit(1)
            
        print(f"Uploading {zip_filename}...")
        
        try:
            with open(zip_path, 'rb') as f:
                upload_response = requests.put(
                    upload_url,
                    data=f,
                    headers={'Content-Type': 'application/octet-stream'}
                )
                
                if upload_response.status_code == 200:
                    print("✅ Upload successful!")
                else:
                    print(f"ERROR: Failed to upload archive. Status: {upload_response.status_code}")
                    print(upload_response.text)
                    sys.exit(1)
        except Exception as e:
            print(f"ERROR: Exception during upload: {e}")
            sys.exit(1)
            
        # Cleanup zip file (temp dir is auto-cleaned)
        if os.path.exists(zip_path):
            os.remove(zip_path)

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python upload_files.py <api_key> <source_path> <exclude_patterns> <formatted_course_name>")
        sys.exit(1)
    
    upload_files(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
