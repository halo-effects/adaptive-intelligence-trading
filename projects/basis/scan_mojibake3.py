#!/usr/bin/env python3
"""Deep scan: find ALL double-encoded cp1252 sequences."""

path = r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs\COMPLETE.md'
with open(path, 'rb') as f:
    data = f.read()

# The c3 a2 e2 82 ac prefix = â€ which is the double-encoding of bytes e2 80 XX
# where e2->â(c3 a2), 80->€(e2 82 ac), XX->next cp1252 char
# So we need to find c3 a2 e2 82 ac followed by the third byte's cp1252->utf8

# Map cp1252 byte -> utf8 encoding for the special range 0x80-0x9F
cp1252_special = {
    0x80: '€', 0x81: '\x81', 0x82: '‚', 0x83: 'ƒ', 0x84: '„', 0x85: '…',
    0x86: '†', 0x87: '‡', 0x88: 'ˆ', 0x89: '‰', 0x8a: 'Š', 0x8b: '‹',
    0x8c: 'Œ', 0x8d: '\x8d', 0x8e: 'Ž', 0x8f: '\x8f',
    0x90: '\x90', 0x91: ''', 0x92: ''', 0x93: '"', 0x94: '"', 0x95: '•',
    0x96: '–', 0x97: '—', 0x98: '˜', 0x99: '™', 0x9a: 'š', 0x9b: '›',
    0x9c: 'œ', 0x9d: '\x9d', 0x9e: 'ž', 0x9f: 'Ÿ',
}

# Build mapping: for any 3-byte UTF-8 char (e2 XX YY), the double-encoded form is:
# â(c3 a2) + cp1252(XX)->utf8 + cp1252(YY)->utf8
# Find all such triples
from collections import Counter
import re

# Find all c3 a2 sequences and collect the full mojibake + what it should be
results = Counter()
i = 0
while i < len(data) - 2:
    if data[i:i+2] == b'\xc3\xa2':
        # This is double-encoded 'â' - start of a 3-byte UTF-8 char
        # Consume the full mojibake sequence (variable length)
        # Original byte was 0xe2, next two bytes also need un-mangling
        # Collect bytes until we have the full original 3-byte sequence
        orig_bytes = [0xe2]
        j = i + 2
        for _ in range(2):  # need 2 more original bytes
            if j >= len(data):
                break
            b = data[j]
            if b < 0x80:
                orig_bytes.append(b)
                j += 1
            elif 0x80 <= b <= 0x9f:
                # This byte is NOT valid UTF-8 lead for cp1252 specials
                # but it would have been encoded by cp1252->utf8
                # Actually it won't appear raw - it was already re-encoded
                # Need to figure out the cp1252 re-encoding
                break
            elif b == 0xc3 and j+1 < len(data):
                # c3 XX = UTF-8 for U+00XX where XX = next byte
                orig_bytes.append(data[j+1] + 0x40)
                j += 2
            elif b == 0xc2 and j+1 < len(data):
                orig_bytes.append(data[j+1])
                j += 2
            elif b == 0xc5 and j+1 < len(data):
                # c5 XX -> cp1252 char
                cp_char = bytes([b, data[j+1]]).decode('utf-8')
                # reverse: find which cp1252 byte produces this
                for k, v in cp1252_special.items():
                    if v == cp_char:
                        orig_bytes.append(k)
                        break
                j += 2
            elif b == 0xcb and j+1 < len(data):
                cp_char = bytes([b, data[j+1]]).decode('utf-8')
                for k, v in cp1252_special.items():
                    if v == cp_char:
                        orig_bytes.append(k)
                        break
                j += 2
            elif b == 0xe2 and j+2 < len(data):
                cp_char = bytes([b, data[j+1], data[j+2]]).decode('utf-8')
                for k, v in cp1252_special.items():
                    if v == cp_char:
                        orig_bytes.append(k)
                        break
                j += 3
            else:
                break
        
        if len(orig_bytes) == 3:
            try:
                real_char = bytes(orig_bytes).decode('utf-8')
                mangled = data[i:j].decode('utf-8', errors='replace')
                results[(real_char, mangled, data[i:j].hex(' '))] += 1
            except:
                pass
        i = j
    else:
        i += 1

print(f"{'Real char':<10} {'Count':>6}  {'Appears as':<20}")
print("-" * 50)
total = 0
for (real, mangled, hexb), cnt in results.most_common():
    print(f"{repr(real):<10} {cnt:>6}  {repr(mangled):<20} {hexb}")
    total += cnt
print(f"\nTotal: {total} double-encoded characters remaining")
