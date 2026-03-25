#!/usr/bin/env python3
"""Map all double-encoded UTF-8 via cp1252 patterns in COMPLETE.md."""

path = r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs\COMPLETE.md'
with open(path, 'rb') as f:
    data = f.read()

# Double-encoding: real UTF-8 bytes were read as cp1252, then re-encoded to UTF-8
# To find them: try decoding as UTF-8, look for sequences that are cp1252-of-UTF-8
text = data.decode('utf-8')

# Build reverse map: for each common Unicode char, what does its double-encoded form look like?
test_chars = {
    '—': '\u2014',  # em-dash
    '–': '\u2013',  # en-dash
    '"': '\u201c',  # left double quote
    '"': '\u201d',  # right double quote
    ''': '\u2018',  # left single quote
    ''': '\u2019',  # right single quote
    '…': '\u2026',  # ellipsis
    '×': '\u00d7',  # multiplication sign
    '≈': '\u2248',  # almost equal
    '≥': '\u2265',  # greater or equal
    '≤': '\u2264',  # less or equal
    '±': '\u00b1',  # plus-minus
    '⚠': '\u26a0',  # warning
    '✓': '\u2713',  # check
    '★': '\u2605',  # star
    '†': '\u2020',  # dagger
    '→': '\u2192',  # right arrow (already fixed, but check)
    '├': '\u251c',  # box drawing (already fixed)
    '└': '\u2514',  # box drawing (already fixed)
    '│': '\u2502',  # box drawing (already fixed)
    '─': '\u2500',  # box drawing (already fixed)
    '≠': '\u2260',  # not equal
    '•': '\u2022',  # bullet
}

# For each char, compute what double-encoding produces
found = {}
for name, char in test_chars.items():
    utf8_bytes = char.encode('utf-8')
    try:
        mangled = utf8_bytes.decode('cp1252')
        double_encoded = mangled.encode('utf-8')
        mangled_str = mangled  # this is what appears in the file
        count = data.count(double_encoded)
        if count > 0:
            found[name] = (count, mangled_str, double_encoded.hex(' '))
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass

print("Remaining mojibake in COMPLETE.md:")
print(f"{'Char':<6} {'Count':>6}  {'Appears as':<20} {'Hex bytes'}")
print("-" * 70)
total = 0
for name, (count, appears, hexb) in sorted(found.items(), key=lambda x: -x[1][0]):
    print(f"{name:<6} {count:>6}  {repr(appears):<20} {hexb}")
    total += count
print(f"\nTotal: {total} mojibake instances remaining")
