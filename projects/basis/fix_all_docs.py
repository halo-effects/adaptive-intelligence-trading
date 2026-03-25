#!/usr/bin/env python3
"""Fix mojibake box-drawing and arrow characters across all basis-docs .md files."""
import os
import glob

docs_dir = r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs'

replacements = [
    (b'\xc3\xa2"\xc5\x93\xc3\xa2"\xe2\x82\xac', '├─'.encode('utf-8')),
    (b'\xc3\xa2""\xc3\xa2"\xe2\x82\xac', '└─'.encode('utf-8')),
    (b'\xc3\xa2"\'', '│'.encode('utf-8')),
    (b'\xc3\xa2\xe2\x80\xa0\'', '→'.encode('utf-8')),
]

files = glob.glob(os.path.join(docs_dir, '*.md'))
total_fixes = 0

for filepath in sorted(files):
    fname = os.path.basename(filepath)
    if fname == 'COMPLETE.md':
        continue  # already fixed

    with open(filepath, 'rb') as f:
        raw = f.read()

    file_fixes = 0
    for old_bytes, new_bytes in replacements:
        count = raw.count(old_bytes)
        if count > 0:
            raw = raw.replace(old_bytes, new_bytes)
            file_fixes += count

    if file_fixes > 0:
        with open(filepath, 'wb') as f:
            f.write(raw)
        print(f"  {fname}: {file_fixes} replacements")
        total_fixes += file_fixes
    else:
        print(f"  {fname}: clean")

print(f"\nTotal: {total_fixes} replacements across {len(files)-1} files")
