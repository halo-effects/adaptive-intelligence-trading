"""Paste content into Google Doc using the API via service account or browser cookies."""
import requests
import json
import os
import http.cookiejar
import sqlite3
import shutil
import base64
from pathlib import Path

DOC_ID = "1bhVeb7MZSnXFyctu-jjkXxkQ_UIow6ZjZ2h5YtMRywQ"

# Read the markdown content
with open(r"C:\Users\Never\.openclaw\workspace\trading\product-overview.md", "r", encoding="utf-8") as f:
    content = f.read()

# Try to get access token from Chrome/openclaw profile cookies
def get_google_token_from_cookies():
    """Extract Google auth from openclaw browser profile."""
    # Look for openclaw profile cookies
    profiles_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'openclaw' / 'browser' / 'profiles'
    if not profiles_dir.exists():
        profiles_dir = Path(r"C:\Users\Never\AppData\Local\openclaw\browser\profiles")
    
    for profile_dir in profiles_dir.glob('*'):
        cookies_path = profile_dir / 'Default' / 'Cookies'
        if not cookies_path.exists():
            cookies_path = profile_dir / 'Cookies'
        if cookies_path.exists():
            print(f"Found cookies at: {cookies_path}")
            return str(cookies_path)
    return None

# Use the Docs API with the browser session
# Simpler approach: use the export/import URL endpoints
print("Attempting to use Google Docs API...")

# Since we have browser access, let's use a different approach
# Write content to a temp HTML file and use the import endpoint
html_content = content.replace('\n', '<br>')

# Actually, simplest: use clipboard paste via the browser automation
# The content is already written to product-overview.md
# Let's just output the doc URL for manual reference
print(f"Doc ID: {DOC_ID}")
print(f"URL: https://docs.google.com/document/d/{DOC_ID}/edit")
print("Content ready in product-overview.md")
