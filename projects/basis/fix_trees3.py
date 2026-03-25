#!/usr/bin/env python3
"""Fix mojibake by direct character-sequence replacement in decision tree code blocks."""

filepath = r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs\COMPLETE.md'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# From the byte analysis, the mojibake sequences are:
# â"œâ"€  = â + " + œ + â + " + €  → should be ├─
# â"'    = â + " + '              → should be │  (note: ' is right single quote or apostrophe)
# â""â"€  = â + " + " + â + " + €  → should be └─  (different middle char)
# â†'    = â + † + '              → should be →

# Let me identify the exact chars by reading from the file
import re

# Find decision trees section
dt_start = content.find('## Decision Trees')
dt_end = content.find('# Why Each Action Matters')
section = content[dt_start:dt_end]

# Extract unique mojibake sequences from code blocks
blocks = re.findall(r'```\n(.*?)```', section, re.DOTALL)
print(f"Found {len(blocks)} code blocks")

# Collect all unique non-ASCII sequences
for i, block in enumerate(blocks):
    print(f"\nBlock {i+1} unique non-ASCII chars:")
    seen = set()
    for j, ch in enumerate(block):
        if ord(ch) > 127 and ch not in seen:
            # Get context
            ctx = block[max(0,j-2):j+3]
            print(f"  U+{ord(ch):04X} ({ch!r}) in context: {repr(ctx)}")
            seen.add(ch)

# Now let's identify the 3-char mojibake patterns
# Search for â followed by any char followed by specific chars
patterns = set()
for block in blocks:
    for j in range(len(block)-2):
        if block[j] == '\u00e2':  # â
            seq = block[j:j+3]
            if any(ord(c) > 127 for c in seq[1:]):
                patterns.add(repr(seq))

print("\nAll 3-char patterns starting with â:")
for p in sorted(patterns):
    print(f"  {p}")
