#!/usr/bin/env python3
import sys
import os
import re
import subprocess
import inquirer
import requests
from bs4 import BeautifulSoup
import utils

SEARCH_URL = "https://learning.oreilly.com/search/"

def main():
    print("O'Reilly Course Downloader")
    print("--------------------------")
    
    cookie_file = utils.find_cookie_file()
    if not cookie_file:
        print("Error: cookie.txt or cookies.txt not found in current directory.")
        print("Please export your cookies from your browser and save them here.")
        sys.exit(1)
        
    session = utils.get_legacy_session(cookie_file)
    
    # Check if cookies work (optional but good)
    try:
        resp = session.get("https://learning.oreilly.com/api/v2/user/")
        if resp.status_code == 401 or resp.status_code == 403:
            print("Warning: Authentication failed. Your cookies might be expired.")
            proceed = input("Continue anyway? (y/n): ")
            if proceed.lower() != 'y':
                sys.exit(1)
        else:
            print("Authentication successful.")
    except Exception as e:
        print(f"Auth check skipped: {e}")

    # Ensure Downloads directory exists
    base_download_dir = os.path.join(os.getcwd(), "Downloads")
    if not os.path.exists(base_download_dir):
        os.makedirs(base_download_dir)

    while True:
        course_url = input("\nEnter Course URL (or 'q' to quit): ").strip()
        if course_url.lower() == 'q':
            break
        
        if not course_url:
            continue
            
        print(f"\nProcessing: {course_url}")
        
        # 1. Extract ISBN
        isbn_match = re.search(r'/(?:course|videos|library/view|book)/[^/]+/([^/]+)/?', course_url)
        if not isbn_match:
            print("Could not detect ISBN from URL. Using fallback yt-dlp mode (metadata might be incomplete).")
            # Fallback to old behavior if ISBN not found (simple pass-through)
            output_template = f"{base_download_dir}/%(playlist)s/%(chapter_number)s - %(chapter)s/%(playlist_index)s - %(title)s.%(ext)s"
            cmd = ["yt-dlp", "--cookies", cookie_file, "-o", output_template, "--format", "bestvideo+bestaudio/best", "--merge-output-format", "mp4", "--embed-metadata", course_url]
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error: {e}")
            continue

        isbn = isbn_match.group(1)
        print(f"Detected ISBN: {isbn}")
        
        # 2. Fetch Course TOC to get structure
        api_url = f"https://learning.oreilly.com/api/v1/book/{isbn}/"
        toc_url = f"https://learning.oreilly.com/api/v1/book/{isbn}/toc/"
        
        try:
            # Get Title first
            resp = session.get(api_url)
            course_title = "Unknown Course"
            if resp.status_code == 200:
                course_title = resp.json().get('title', course_title)
            
            # Sanitize course title
            course_title = re.sub(r'[\\/*?"<>|]', "", course_title).strip()
            print(f"Course Title: {course_title}")
            
            # Get TOC
            print("Fetching Course TOC...")
            resp = session.get(toc_url)
            if resp.status_code != 200:
                print(f"Failed to fetch TOC. Status: {resp.status_code}. Falling back to default yt-dlp.")
                output_template = f"{base_download_dir}/%(playlist)s/%(chapter_number)s - %(chapter)s/%(playlist_index)s - %(title)s.%(ext)s"
                cmd = ["yt-dlp", "--cookies", cookie_file, "-o", output_template, "--format", "bestvideo+bestaudio/best", "--merge-output-format", "mp4", "--embed-metadata", course_url]
                try:
                    subprocess.run(cmd, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error: {e}")
                continue
                
            toc = resp.json()
            
            # 3. Iterate and Download
            # Structure: List of objects. Objects have 'label' and 'children'.
            
            module_idx = 1
            total_modules = len(toc)
            
            for module in toc:
                module_label = module.get('label', f"Module {module_idx}")
                module_label = re.sub(r'[\\/*?"<>|]', "", module_label).strip()
                module_dir_name = f"{module_idx:02d} - {module_label}"
                
                # Check for children (lessons)
                children = module.get('children', [])
                if not children:
                    # If it has a URL and no children, treat as lesson in root module
                    if module.get('url'):
                        children = [module]  # Treat itself as single child
                        module_dir_name = "00 - Introduction_or_Misc"

                if not children:
                    continue

                print(f"\n--- Module {module_idx}/{total_modules}: {module_label} ---")
                
                lesson_idx = 1
                for lesson in children:
                    lesson_label = lesson.get('label', f"Lesson {lesson_idx}")
                    lesson_label = re.sub(r'[\\/*?"<>|]', "", lesson_label).strip()
                    lesson_filename = f"{lesson_idx:02d} - {lesson_label}.mp4"
                    
                    lesson_url = lesson.get('url')
                    if not lesson_url:
                        continue
                        
                    # Output path: Downloads/Course Title/Module/Lesson.mp4
                    output_path = os.path.join(base_download_dir, course_title, module_dir_name, lesson_filename)
                    
                    # Create directory if needed
                    output_dir = os.path.dirname(output_path)
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    
                    # Check if file exists (simple resume)
                    if os.path.exists(output_path):
                        print(f"Skipping (exists): {lesson_filename}")
                        lesson_idx += 1
                        continue

                    print(f"Downloading: {lesson_filename}")
                    
                    # Call yt-dlp for this specific VIDEO URL
                    cmd = [
                        "yt-dlp",
                        "--cookies", cookie_file,
                        "-o", output_path,
                        "--format", "bestvideo+bestaudio/best",
                        "--merge-output-format", "mp4",
                        "--embed-metadata",
                        lesson_url
                    ]
                    
                    try:
                        subprocess.run(cmd, check=True)
                    except subprocess.CalledProcessError:
                        print(f"Failed to download: {lesson_label}")
                    except KeyboardInterrupt:
                        print("\nInterrupted by user. Exiting.")
                        return  # Exit main loop and function

                    lesson_idx += 1
                
                module_idx += 1
                
            print(f"\nCourse '{course_title}' download complete!")
            
        except Exception as e:
            print(f"An error occurred: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
