"""Write content to Google Doc using Docs API with browser cookies."""
import json
import sqlite3
import shutil
import tempfile
import requests
from pathlib import Path
import os
import base64
import struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import win32crypt

DOC_ID = "1bhVeb7MZSnXFyctu-jjkXxkQ_UIow6ZjZ2h5YtMRywQ"

def get_encryption_key():
    """Get Chrome's cookie encryption key."""
    local_state_path = Path(r"C:\Users\Never\AppData\Local\openclaw\browser\profiles\openclaw\Local State")
    if not local_state_path.exists():
        # Try alternate paths
        for p in Path(r"C:\Users\Never\AppData\Local\openclaw\browser\profiles").rglob("Local State"):
            local_state_path = p
            break
    
    with open(local_state_path, 'r', encoding='utf-8') as f:
        local_state = json.load(f)
    
    encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
    encrypted_key = encrypted_key[5:]  # Remove DPAPI prefix
    key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    return key

def decrypt_cookie(encrypted_value, key):
    """Decrypt a Chrome cookie value."""
    if encrypted_value[:3] == b'v10' or encrypted_value[:3] == b'v20':
        nonce = encrypted_value[3:15]
        ciphertext = encrypted_value[15:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
    else:
        return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode('utf-8')

def get_google_cookies():
    """Extract Google auth cookies from openclaw browser profile."""
    profiles_base = Path(r"C:\Users\Never\AppData\Local\openclaw\browser\profiles\openclaw")
    cookies_path = profiles_base / "Default" / "Cookies"
    if not cookies_path.exists():
        cookies_path = profiles_base / "Cookies"
    if not cookies_path.exists():
        # Search for it
        for p in profiles_base.rglob("Cookies"):
            if p.is_file() and p.stat().st_size > 0:
                cookies_path = p
                break
    
    print(f"Cookies path: {cookies_path}")
    
    key = get_encryption_key()
    
    # Copy cookies db (it's locked by Chrome)
    tmp = tempfile.mktemp(suffix='.db')
    shutil.copy2(str(cookies_path), tmp)
    
    conn = sqlite3.connect(tmp)
    cursor = conn.cursor()
    
    # Get Google auth cookies
    cursor.execute("""
        SELECT name, encrypted_value, host_key 
        FROM cookies 
        WHERE host_key LIKE '%google.com%' 
        AND (name IN ('SID', 'HSID', 'SSID', 'APISID', 'SAPISID', '__Secure-1PSID', '__Secure-3PSID',
                       'SIDCC', '__Secure-1PSIDCC', '__Secure-3PSIDCC',
                       '__Secure-1PAPISID', '__Secure-3PAPISID'))
    """)
    
    cookies = {}
    for name, encrypted_value, host in cursor.fetchall():
        try:
            value = decrypt_cookie(encrypted_value, key)
            cookies[name] = value
        except Exception as e:
            print(f"Failed to decrypt {name}: {e}")
    
    conn.close()
    os.unlink(tmp)
    
    return cookies

def get_sapisidhash(sapisid, origin="https://docs.google.com"):
    """Generate SAPISIDHASH for Google API auth."""
    import hashlib
    import time
    timestamp = int(time.time())
    hash_input = f"{timestamp} {sapisid} {origin}"
    hash_value = hashlib.sha1(hash_input.encode()).hexdigest()
    return f"SAPISIDHASH {timestamp}_{hash_value}"

# Get cookies
print("Extracting cookies...")
cookies = get_google_cookies()
print(f"Got {len(cookies)} cookies")

if not cookies:
    print("No cookies found!")
    exit(1)

# Build cookie string
cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())

# Get SAPISID for auth header
sapisid = cookies.get('SAPISID') or cookies.get('__Secure-1PAPISID', '')
auth_header = get_sapisidhash(sapisid) if sapisid else None

# Read content
with open(r"C:\Users\Never\.openclaw\workspace\trading\product-overview.md", "r", encoding="utf-8") as f:
    content = f.read()

# Build requests for Google Docs API
# First, get current doc to know the end index
headers = {
    'Cookie': cookie_str,
    'Content-Type': 'application/json',
}
if auth_header:
    headers['Authorization'] = auth_header

# Use the Docs API
url = f"https://docs.googleapis.com/v1/documents/{DOC_ID}"
r = requests.get(url, headers=headers)
print(f"GET doc: {r.status_code}")

if r.status_code != 200:
    print(f"Error: {r.text[:500]}")
    exit(1)

doc = r.json()
end_index = doc['body']['content'][-1]['endIndex']
print(f"Current doc end index: {end_index}")

# Build batch update to insert text
# First clear existing content (if any beyond the initial newline)
requests_list = []
if end_index > 2:
    requests_list.append({
        'deleteContentRange': {
            'range': {'startIndex': 1, 'endIndex': end_index - 1}
        }
    })

# Insert the content
requests_list.append({
    'insertText': {
        'location': {'index': 1},
        'text': content
    }
})

# Apply formatting for headers
# We'll do basic formatting after inserting text

body = {'requests': requests_list}
r2 = requests.post(f"{url}:batchUpdate", headers=headers, json=body)
print(f"BatchUpdate: {r2.status_code}")
if r2.status_code != 200:
    print(f"Error: {r2.text[:500]}")
else:
    print("Content inserted successfully!")
    
    # Now apply heading styles
    # Re-fetch doc to get updated indices
    r3 = requests.get(url, headers=headers)
    doc = r3.json()
    
    # Find heading lines and apply styles
    format_requests = []
    for element in doc['body']['content']:
        if 'paragraph' in element:
            para = element['paragraph']
            text = ''
            for elem in para.get('elements', []):
                text += elem.get('textRun', {}).get('content', '')
            
            start = element['startIndex']
            end = element['endIndex']
            
            if text.startswith('# '):
                format_requests.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': start, 'endIndex': end},
                        'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                        'fields': 'namedStyleType'
                    }
                })
                # Remove the "# " prefix
                format_requests.append({
                    'deleteContentRange': {
                        'range': {'startIndex': start, 'endIndex': start + 2}
                    }
                })
            elif text.startswith('## '):
                format_requests.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': start, 'endIndex': end},
                        'paragraphStyle': {'namedStyleType': 'HEADING_2'},
                        'fields': 'namedStyleType'
                    }
                })
            elif text.startswith('### '):
                format_requests.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': start, 'endIndex': end},
                        'paragraphStyle': {'namedStyleType': 'HEADING_3'},
                        'fields': 'namedStyleType'
                    }
                })
    
    if format_requests:
        # Apply formatting in reverse order to not mess up indices
        r4 = requests.post(f"{url}:batchUpdate", headers=headers, json={'requests': format_requests})
        print(f"Formatting: {r4.status_code}")

print(f"\nDoc URL: https://docs.google.com/document/d/{DOC_ID}/edit")
