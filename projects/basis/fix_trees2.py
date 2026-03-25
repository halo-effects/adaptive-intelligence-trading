#!/usr/bin/env python3
"""Fix mojibake in COMPLETE.md - approach 2: byte-level analysis."""

filepath = r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs\COMPLETE.md'

with open(filepath, 'rb') as f:
    raw = f.read()

# Find "How long will it be idle?" and dump surrounding bytes
idx = raw.find(b'How long will it be idle?')
sample = raw[idx+25:idx+80]
print("Hex around tree 1:")
print(' '.join(f'{b:02x}' for b in sample))
print("As text:", sample.decode('utf-8', errors='replace'))

# The mojibake pattern: UTF-8 bytes → decoded as cp1252 → re-encoded as UTF-8
# So to fix: encode back to cp1252 to recover original UTF-8 bytes
# But we can only do this for the affected sections

# Let's try: for each code block in the decision trees section,
# take the text, encode to cp1252, decode as utf-8
idx_start = raw.find(b'## Decision Trees')
idx_end = raw.find(b'# Why Each Action Matters')
section = raw[idx_start:idx_end]
print(f"\nDecision tree section: bytes {idx_start}-{idx_end}")

# Try the round-trip on just the code blocks
import re
text = section.decode('utf-8')
blocks = list(re.finditer(r'```\n(.*?)```', text, re.DOTALL))
print(f"Found {len(blocks)} code blocks")

for i, m in enumerate(blocks):
    block_text = m.group(1)
    try:
        # Encode as cp1252 to get back the original UTF-8 bytes
        recovered_bytes = block_text.encode('cp1252')
        fixed = recovered_bytes.decode('utf-8')
        print(f"\nBlock {i+1} FIXED preview:")
        print(fixed[:200])
    except (UnicodeEncodeError, UnicodeDecodeError) as e:
        print(f"\nBlock {i+1} round-trip failed: {e}")
        # Show the problematic chars
        for j, ch in enumerate(block_text[:100]):
            if ord(ch) > 127:
                print(f"  pos {j}: U+{ord(ch):04X} ({ch!r})")
