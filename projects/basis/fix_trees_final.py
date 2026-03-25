#!/usr/bin/env python3
"""Fix mojibake box-drawing characters via exact byte replacement."""

filepath = r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs\COMPLETE.md'

with open(filepath, 'rb') as f:
    raw = f.read()

# Exact byte replacements (from analysis)
replacements = [
    # ├─  (branch)
    (b'\xc3\xa2"\xc5\x93\xc3\xa2"\xe2\x82\xac', '├─'.encode('utf-8')),
    # └─  (last branch)
    (b'\xc3\xa2""\xc3\xa2"\xe2\x82\xac', '└─'.encode('utf-8')),
    # │   (continuation) - must come after ├─ and └─ to avoid partial matches
    (b'\xc3\xa2"\'', '│'.encode('utf-8')),
    # →   (arrow)
    (b'\xc3\xa2\xe2\x80\xa0\'', '→'.encode('utf-8')),
]

for old_bytes, new_bytes in replacements:
    count = raw.count(old_bytes)
    raw = raw.replace(old_bytes, new_bytes)
    old_display = old_bytes.decode('utf-8', errors='replace')
    new_display = new_bytes.decode('utf-8')
    print(f"Replaced {count}x: {old_display!r} → {new_display!r}")

with open(filepath, 'wb') as f:
    f.write(raw)

print("\nDone! Verifying...")

# Verify
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

import re
dt_start = content.find('## Decision Trees')
dt_end = content.find('# Why Each Action Matters')
section = content[dt_start:dt_end]
blocks = re.findall(r'```\n(.*?)```', section, re.DOTALL)
for i, block in enumerate(blocks):
    print(f"\nBlock {i+1} preview:")
    for line in block.split('\n')[:4]:
        print(f"  {line}")
