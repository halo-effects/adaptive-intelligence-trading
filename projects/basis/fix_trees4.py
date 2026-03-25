#!/usr/bin/env python3
"""Find exact mojibake byte sequences for all box-drawing chars."""

filepath = r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs\COMPLETE.md'

with open(filepath, 'rb') as f:
    raw = f.read()

# Find each box-drawing mojibake by looking at lines starting with these patterns
# after "How long will it be idle?"
idx = raw.find(b'How long will it be idle?')
chunk = raw[idx:idx+500]

# Find lines that start with the mojibake chars (after newline)
lines = chunk.split(b'\n')
for i, line in enumerate(lines):
    if len(line) > 0 and line[0] > 127:
        label = "BRANCH" if i < 7 else "?"
        hex_start = ' '.join(f'{b:02x}' for b in line[:12])
        print(f"Line {i}: {hex_start}  ({line[:20]})")

# Also find the └ pattern
print("\n--- Looking for └ pattern ---")
idx2 = raw.find(b'Indefinitely')
if idx2 > 0:
    before = raw[idx2-10:idx2+5]
    print(f"Before 'Indefinitely': {' '.join(f'{b:02x}' for b in before)}")

# And the │ pattern  
print("\n--- Looking for │ pattern ---")
idx3 = raw.find(b'see: trading.buy() then staking.buy()')
if idx3 > 0:
    before = raw[idx3-20:idx3+5]
    print(f"Before 'see: trading': {' '.join(f'{b:02x}' for b in before)}")

# And the → pattern
print("\n--- Looking for → pattern ---")
idx4 = raw.find(b'Leave as USDB')
if idx4 > 0:
    before = raw[idx4-10:idx4+5]
    print(f"Before 'Leave': {' '.join(f'{b:02x}' for b in before)}")
