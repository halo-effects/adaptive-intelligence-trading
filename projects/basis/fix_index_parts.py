#!/usr/bin/env python3
"""Remove Part # references from COMPLETE_INDEX.md"""
import re

path = r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs\COMPLETE_INDEX.md'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

original = content

# Type 1: Section headers like "### SDK Reference — Modules (Part 3)"
# Remove " (Part #)" suffix
content = re.sub(r' \(Part \d+\)', '', content)

# Type 2: TOC entries like "2033  Part 5 — Strategy Playbooks ★"
# Remove "Part # — " or "Part # - " prefix, keep the line number and title
content = re.sub(r'^(\s*\d+\s+)Part \d+\s*[-–—]\s*', r'\1', content, flags=re.MULTILINE)

changes = sum(1 for a, b in zip(original.splitlines(), content.splitlines()) if a != b)

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print(f"Done — {changes} lines changed")

# Show the changed lines
for i, (old, new) in enumerate(zip(original.splitlines(), content.splitlines()), 1):
    if old != new:
        print(f"  L{i}: {old.strip()}")
        print(f"    → {new.strip()}")
