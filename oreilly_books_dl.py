#!/usr/bin/env python3
import os
import sys
import time
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import utils

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def download_book(session, book_url, output_dir):
    try:
        print(f"Fetching book TOC from {book_url}...")
        response = session.get(book_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title_tag = soup.find('h1', class_='t-title')
        if not title_tag:
             title_tag = soup.find('h1')
        book_title = title_tag.get_text(strip=True) if title_tag else "Unknown_Book"
        book_dir = os.path.join(output_dir, sanitize_filename(book_title))
        
        if not os.path.exists(book_dir):
            os.makedirs(book_dir)
            
        print(f"Downloading '{book_title}' to {book_dir}...")
        
        # Find TOC links
        # O'Reilly book structure varies, but usually there's a TOC list
        # Look for links that are part of the book content
        
        # Strategy: Look for the 'Start reading' link or TOC links
        # Attempt to find the TOC container.
        # Often in a <ol class="toc-list"> or similar.
        
        toc_links = []
        toc_container = soup.find(class_=re.compile(r'toc'))
        if toc_container:
            links = toc_container.find_all('a', href=True)
            for link in links:
                href = link['href']
                if 'http' not in href:
                    full_url = urljoin(book_url, href)
                else:
                    full_url = href
                toc_links.append(full_url)
        else:
             # Fallback: try to find 'Start' button and then follow 'Next' links?
             # That's harder. Let's look for any link that looks like a chapter.
             print("Warning: explicit TOC not found. Trying to extract links from main area.")
             main_content = soup.find('section', itemprop='description') # Description might not have links
             # Actually, often the main page IS the TOC or has a 'Table of Contents' tab.
             # Let's try to query the API for the TOC if possible.
             # API: https://learning.oreilly.com/api/v2/book/{isbn}/
             
             # Extract ISBN from URL
             # /library/view/title/isbn/
             # or /course/title/isbn/
             match = re.search(r'/(?:view|course)/[^/]+/([^/]+)/', book_url)
             if match:
                 isbn = match.group(1)
                 print(f"Detected ISBN: {isbn}. Trying API...")
                 
                 # Try v2 first
                 # If it fails (404), it might be a video course or restricted.
                 
                 api_url_v2 = f"https://learning.oreilly.com/api/v2/book/{isbn}/"
                 api_url_v1 = f"https://learning.oreilly.com/api/v1/book/{isbn}/"
                 
                 found_data = None
                 
                 # Try v2
                 try:
                     resp = session.get(api_url_v2)
                     if resp.status_code == 200:
                         found_data = resp.json()
                         print("Found book metadata via API v2.")
                 except: pass
                 
                 # Try v1 if v2 failed
                 if not found_data:
                     try:
                         resp = session.get(api_url_v1)
                         if resp.status_code == 200:
                             found_data = resp.json()
                             print("Found book metadata via API v1.")
                     except: pass
                 
                 if found_data:
                     # Check format
                     fmt = found_data.get('format')
                     if fmt == 'video':
                         print("\nWARNING: This URL appears to be a VIDEO COURSE, not a book.")
                         print("Please use 'run_course.sh' to download it properly.\n")
                         # We can continue if user really wants, but likely TOC extraction will fail or be weird.
                         # If it's a course, 'chapters' might still exist but be video pointers.
                     
                     chapters_url = found_data.get('chapters_url')
                     if not chapters_url:
                         # v1 might use different structure or just flat list in 'chapters'
                         if 'chapters' in found_data and isinstance(found_data['chapters'], list):
                             # v1 embedding
                             print("Found chapters in metadata.")
                             for chap in found_data['chapters']:
                                 toc_links.append(chap.get('web_url') or chap.get('url'))
                         else:
                             chapters_url = f"{api_url_v2}chapters/" # Guess
                     
                     if not toc_links and chapters_url:
                         try:
                             chap_resp = session.get(chapters_url)
                             if chap_resp.status_code == 200:
                                 chapters_data = chap_resp.json()
                                 # v2 results
                                 if 'results' in chapters_data:
                                     for chap in chapters_data['results']:
                                         toc_links.append(chap.get('web_url') or chap.get('url'))
                                 # v1 might match found_data structure
                         except Exception as e:
                             print(f"Error fetching chapters: {e}")
                 else:
                     print("Could not retrieve metadata from API (v1 or v2).")

        if not toc_links:
            print("Error: Could not find any chapters to download.")
            return

        print(f"Found {len(toc_links)} chapters.")
        
        # Download loop
        for i, chapter_url in enumerate(toc_links):
            print(f"Downloading chapter {i+1}/{len(toc_links)}: {chapter_url}")
            try:
                chap_resp = session.get(chapter_url)
                chap_resp.raise_for_status()
                chap_soup = BeautifulSoup(chap_resp.content, 'html.parser')
                
                # Content cleaning
                # Remove header, footer, navigation
                for element in chap_soup.find_all(class_=re.compile(r'nav|header|footer|sidebar')):
                    element.decompose()
                
                content = str(chap_soup)
                
                # Save
                filename = f"{i+1:03d}_chapter.html"
                with open(os.path.join(book_dir, filename), 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Moderate pace to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"Failed to download chapter {chapter_url}: {e}")

    except Exception as e:
        print(f"Error processing book: {e}")

def main():
    print("O'Reilly Book Downloader")
    print("------------------------")
    
    cookie_file = utils.find_cookie_file()
    if not cookie_file:
        print("Error: cookie.txt or cookies.txt not found.")
        sys.exit(1)
        
    session = utils.get_legacy_session(cookie_file)
    
    book_url = input("Enter the Book URL (e.g., https://learning.oreilly.com/library/view/...): ").strip()
    if not book_url:
        print("Invalid URL.")
        sys.exit(1)
        
    download_book(session, book_url, ".")

if __name__ == "__main__":
    main()
