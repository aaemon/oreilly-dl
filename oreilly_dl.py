#!/usr/bin/env python3
import sys
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

    while True:
        course_url = input("\nEnter Course URL (or 'q' to quit): ").strip()
        if course_url.lower() == 'q':
            break
        
        if not course_url:
            continue
            
        # Optimization: yt-dlp works best with the API URL for O'Reilly courses.
        # Browser URL: https://learning.oreilly.com/course/title/isbn/
        # Target URL: https://learning.oreilly.com/api/v1/book/isbn/
        
        import re
        isbn_match = re.search(r'/(?:course|videos|library/view)/[^/]+/([^/]+)/', course_url)
        if isbn_match:
            isbn = isbn_match.group(1)
            print(f"Detected ISBN: {isbn}")
            # Use the API URL which yt-dlp's safari:course extractor definitely supports
            download_url = f"https://learning.oreilly.com/api/v1/book/{isbn}/"
            print(f"Converted to API URL for downloader: {download_url}")
        else:
            # Fallback to whatever user provided
            download_url = course_url

        print(f"\nProcessing: {download_url}")
        
        # Construct yt-dlp command
        # Output template: Course Title / Chapter Number - Chapter Title / Index - Title.ext
        # We use %(playlist)s for Course Title (usually works for O'Reilly)
        # %(chapter_number)s and %(chapter)s for Module
        # %(title)s for Lesson
        
        # Note: If chapter info is missing, yt-dlp might put it in NA directories.
        # We can use autonumber if needed, but let's try the requested structure.
        
        output_template = "%(playlist)s/%(chapter_number)02d - %(chapter)s/%(playlist_index)s - %(title)s.%(ext)s"
        
        cmd = [
            "yt-dlp",
            "--cookies", cookie_file,
            "-o", output_template,
            "--format", "bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            "--embed-metadata", # Useful to keep metadata
            download_url
        ]
        
        try:
            print("Starting download... (Press Ctrl+C to cancel current course)")
            subprocess.run(cmd, check=True)
            print(f"Successfully finished: {course_url}")
        except subprocess.CalledProcessError as e:
            print(f"Download interrupted or failed: {e}")
        except KeyboardInterrupt:
            print("\nDownload canceled by user.")
        except FileNotFoundError:
            print("Error: yt-dlp not found. Please install it (pip install yt-dlp).")

if __name__ == "__main__":
    main()
