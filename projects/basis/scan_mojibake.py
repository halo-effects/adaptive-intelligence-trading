#!/usr/bin/env python3
"""Scan COMPLETE.md for remaining mojibake patterns."""
import re
from collections import Counter

path = r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs\COMPLETE.md'
with open(path, 'rb') as f:
    data = f.read()

# Known mojibake prefix: \xc3\xa2 (which is UTF-8 for â, the start of double-encoded sequences)
# Find all occurrences with surrounding context
patterns = re.findall(rb'\xc3\xa2.{1,6}', data)
c = Counter()
for p in patterns:
    c[p[:5]] += 1

print("All \\xc3\\xa2 patterns (first 5 bytes):")
for pat, cnt in c.most_common(30):
    try:
        # Try to decode as if it were valid UTF-8
        decoded = pat.decode('utf-8', errors='replace')
    except:
        decoded = '?'
    print(f"  {pat.hex(' ')} ({cnt}x) repr={repr(pat)} text={decoded}")

# Specifically check for em-dash mojibake: â€" in cp1252-as-utf8
# Real em-dash is \xe2\x80\x94 in UTF-8
# Double-encoded: \xc3\xa2 \xe2\x82\xac \xe2\x80\x9c  or similar
emdash_mojibake = b'\xc3\xa2\xe2\x82\xac'  # partial prefix
count = data.count(emdash_mojibake)
print(f"\n\\xc3\\xa2\\xe2\\x82\\xac prefix: {count} instances")

# Show context around first few
lines = data.split(b'\n')
for i, line in enumerate(lines, 1):
    if emdash_mojibake in line:
        print(f"  Line {i}: ...{line[max(0,line.find(emdash_mojibake)-20):line.find(emdash_mojibake)+30].decode('utf-8', errors='replace')}...")
        if i > 20:  # limit output
            remaining = sum(1 for l in lines[i:] if emdash_mojibake in l)
            if remaining:
                print(f"  ...and {remaining} more lines")
            break
