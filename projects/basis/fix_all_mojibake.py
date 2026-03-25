#!/usr/bin/env python3
"""Fix ALL remaining mojibake in COMPLETE.md by reversing the double-encoding."""

path = r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs\COMPLETE.md'
with open(path, 'rb') as f:
    data = f.read()

original_len = len(data)

# Strategy: decode as UTF-8, then try to reverse the cp1252 double-encoding
# For each known mojibake pattern, replace with the correct UTF-8

# Build replacement map at the byte level
# Original UTF-8 bytes were misread as cp1252, then re-encoded to UTF-8
# To reverse: find the double-encoded bytes, replace with original UTF-8

# cp1252 byte -> Unicode char -> UTF-8 bytes (for the special 0x80-0x9F range)
cp1252_to_unicode = {
    0x80: '\u20ac', 0x82: '\u201a', 0x83: '\u0192', 0x84: '\u201e',
    0x85: '\u2026', 0x86: '\u2020', 0x87: '\u2021', 0x88: '\u02c6',
    0x89: '\u2030', 0x8a: '\u0160', 0x8b: '\u2039', 0x8c: '\u0152',
    0x8e: '\u017d', 0x91: '\u2018', 0x92: '\u2019', 0x93: '\u201c',
    0x94: '\u201d', 0x95: '\u2022', 0x96: '\u2013', 0x97: '\u2014',
    0x98: '\u02dc', 0x99: '\u2122', 0x9a: '\u0161', 0x9b: '\u203a',
    0x9c: '\u0153', 0x9e: '\u017e', 0x9f: '\u0178',
}

def double_encode(char):
    """Given a Unicode char, return its double-encoded byte sequence."""
    utf8_bytes = char.encode('utf-8')
    # Interpret each byte as cp1252
    result = b''
    for b in utf8_bytes:
        if b < 0x80:
            result += bytes([b])
        elif b in cp1252_to_unicode:
            result += cp1252_to_unicode[b].encode('utf-8')
        else:
            # 0x80-0xFF outside special range: cp1252 = latin-1 = direct Unicode
            result += chr(b).encode('utf-8')
    return result

# Characters we know are in the file (from scan)
targets = [
    '\u2013',  # en-dash –
    '\u2014',  # em-dash —
    '\u00b7',  # middle dot ·
    '\u274c',  # cross mark ❌
    '\u26a0',  # warning sign ⚠
    '\u2705',  # check mark ✅
    '\u2248',  # almost equal ≈
    '\u2265',  # greater or equal ≥
    '\u00b1',  # plus-minus ±
    '\u2190',  # left arrow ←
    '\u00d7',  # multiplication ×
    '\u201c',  # left double quote "
    '\u201d',  # right double quote "
    '\u2018',  # left single quote '
    '\u2019',  # right single quote '
    '\u2026',  # ellipsis …
    '\u2022',  # bullet •
    '\u2264',  # less or equal ≤
    '\u00a0',  # non-breaking space
]

print("Replacements:")
total = 0
for char in targets:
    encoded = double_encode(char)
    correct = char.encode('utf-8')
    count = data.count(encoded)
    if count > 0:
        data = data.replace(encoded, correct)
        print(f"  {repr(char)} ({char}): {count}x  [{encoded.hex(' ')} -> {correct.hex(' ')}]")
        total += count

# Also fix Â· (middle dot with stray Â prefix)
# Â = c3 82, · = c2 b7 — the double-encoding of 0xB7 (·)
# Actually Â· could be: original byte b7 (·) read as cp1252 = · (same), 
# then with leading c2 from UTF-8 encoding of 0xB7. Let me check differently.
# The Â is from byte 0xC2 being interpreted as cp1252 (which is Â).
# So original bytes were c2 b7 (UTF-8 for ·), read as cp1252: c2=Â, b7=·
# Then re-encoded: Â=c3 82, ·=c2 b7. So double-encoded = c3 82 c2 b7
ab_count = data.count(b'\xc3\x82\xc2\xb7')
if ab_count > 0:
    data = data.replace(b'\xc3\x82\xc2\xb7', '\u00b7'.encode('utf-8'))
    print(f"  '·' (Â· pattern): {ab_count}x")
    total += ab_count

# Check for stray Â before other chars (common double-encoding of 2-byte UTF-8)
# Â followed by common chars: ±, ², ³, etc.
for byte_val in range(0xa0, 0x100):
    orig_char = chr(byte_val)
    # Double-encoded: c3 82 + c2 XX or c3 83 + ...
    orig_utf8 = orig_char.encode('utf-8')  # c2 XX or c3 XX
    if len(orig_utf8) == 2:
        lead = orig_utf8[0]  # c2 or c3
        trail = orig_utf8[1]
        # cp1252 interpretation of lead byte
        double_lead = chr(lead).encode('utf-8')
        double_trail = chr(trail).encode('utf-8')
        double = double_lead + double_trail
        count = data.count(double)
        if count > 0 and double != orig_utf8:  # avoid self-replacement
            data = data.replace(double, orig_utf8)
            print(f"  {repr(orig_char)} (U+{byte_val:04X}): {count}x  [{double.hex(' ')} -> {orig_utf8.hex(' ')}]")
            total += count

print(f"\nTotal: {total} replacements")
print(f"File size: {original_len} -> {len(data)} bytes")

with open(path, 'wb') as f:
    f.write(data)

# Verify line count unchanged
lines = data.count(b'\n')
print(f"Lines: {lines + 1}")
