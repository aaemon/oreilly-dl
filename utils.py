import os
import http.cookiejar
import requests

def load_cookies(cookie_file):
    """
    Loads cookies from a Netscape-formatted cookie file.
    Returns a RequestsCookieJar.
    """
    cj = http.cookiejar.MozillaCookieJar(cookie_file)
    cj.load(ignore_discard=True, ignore_expires=True)
    return cj

def find_cookie_file():
    """
    Looks for cookie.txt or cookies.txt in the current directory.
    Returns the filename if found, else None.
    """
    for filename in ['cookie.txt', 'cookies.txt']:
        if os.path.exists(filename):
            print(f"Found cookie file: {filename}")
            return filename
    return None

def get_legacy_session(cookie_file):
    """
    Creates a requests session with loaded cookies.
    """
    session = requests.Session()
    session.cookies = load_cookies(cookie_file)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    })
    return session
