"""Fix broken emoji in security dashboard HTML."""
import re

path = r"C:\Users\Never\.openclaw\workspace\dashboard\security.html"

with open(path, "rb") as f:
    raw = f.read()

# Map of icon context -> proper HTML entity
replacements = {
    b"System Overview": (b"&#x1F4BB; System Overview"),
    b"Resources": (b"&#x1F4CA; Resources"),
    b"Network": (b"&#x1F310; Network"),
    b"Security Status": (b"&#x1F512; Security Status"),
    b"OpenClaw Gateway": (b"&#x26A1; OpenClaw Gateway"),
    b"Services": (b"&#x2699; Services"),
    b"Open Ports": (b"&#x1F50C; Open Ports"),
    b"Active Connections": (b"&#x1F517; Active Connections"),
    b"Recent Logins": (b"&#x1F464; Recent Logins"),
    b"Startup Programs": (b"&#x1F680; Startup Programs"),
    b"Top Processes": (b"&#x1F50D; Top Processes"),
    b"Scheduled Tasks": (b"&#x1F4CB; Scheduled Tasks"),
}

# Replace each h2 icon span with clean version
for context, clean_text in replacements.items():
    # Match: <span class="icon">ANYTHING</span> CONTEXT
    pattern = rb'<span class="icon">[^<]*</span>\s*' + context
    replacement = b'<span class="icon"></span> ' + clean_text
    raw = re.sub(pattern, replacement, raw)

# Also fix bare h2 with broken emoji (System Overview has no span)
raw = re.sub(rb'<h2>[^\x00-\x7f]+\s*System Overview', b'<h2>&#x1F4BB; System Overview', raw)

# Fix title
raw = raw.replace(b'\xc3\xa2\xe2\x82\xac\xe2\x80\x9c', b'\xe2\x80\x94')  # em dash

with open(path, "wb") as f:
    f.write(raw)

print("Fixed!")
