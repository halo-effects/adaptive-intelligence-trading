#!/usr/bin/env python3
"""Fix the remaining 192 em-dash mojibake instances.

The pattern c3 a2 e2 82 ac 22 is a triple-encoding artifact:
Original: — (em-dash, U+2014, UTF-8: e2 80 94)
Step 1: bytes e2 80 94 read as cp1252 → â € "  
Step 2: the " (U+201D, right double quote) got further mangled to ASCII " (0x22)
Result: â€" as c3 a2 e2 82 ac 22

Replace all c3 a2 e2 82 ac 22 with e2 80 94 (correct em-dash UTF-8).
"""

path = r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs\COMPLETE.md'

with open(path, 'rb') as f:
    data = f.read()

# The mojibake pattern for em-dash
old = b'\xc3\xa2\xe2\x82\xac\x22'  # â€"  (with ASCII ")
new = '\u2014'.encode('utf-8')       # — (em-dash)

count = data.count(old)
print(f"em-dash mojibake (c3 a2 e2 82 ac 22): {count} instances")

data = data.replace(old, new)

# Also check for en-dash variant: 0x93 in cp1252 = " (left double quote) 
# But could also appear as ASCII-ified version
# Actually, let's verify there's nothing else with the â€ prefix
prefix = b'\xc3\xa2\xe2\x82\xac'
remaining = data.count(prefix)
print(f"Remaining â€ prefix instances after fix: {remaining}")

with open(path, 'wb') as f:
    f.write(data)

# Verify
lines = data.count(b'\n') + 1
print(f"Lines: {lines}")

# Final scan - any c3 a2 left?
c3a2 = data.count(b'\xc3\xa2')
print(f"Remaining c3 a2 sequences: {c3a2}")
# Also check for Â (c3 82) followed by non-standard
c382 = data.count(b'\xc3\x82')
print(f"Remaining c3 82 (Â) sequences: {c382}")
