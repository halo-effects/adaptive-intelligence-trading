#!/usr/bin/env python3
"""Complete mojibake scan - find ALL double-encoded characters."""

path = r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs\COMPLETE.md'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Common mojibake patterns (what appears -> what it should be)
replacements = {
    'â€"': '—',   # em-dash
    'â€"': '–',   # en-dash (same visual but different)
    'â€œ': '"',   # left double quote
    'â€\x9d': '"',  # right double quote  
    'â€˜': ''',   # left single quote
    'â€™': ''',   # right single quote
    'â€¦': '…',   # ellipsis
    'â€¢': '•',   # bullet
    'Â±': '±',    # plus-minus
    'Ã—': '×',    # multiplication
    'â‰ˆ': '≈',   # almost equal
    'â‰¥': '≥',   # greater or equal
    'â‰¤': '≤',   # less or equal
    'âš ': '⚠',   # warning sign
    'â†\x90': '←', # left arrow
    'âœ…': '✅',  # check mark
    'â\x9dŒ': '❌', # cross mark
    'Â·': '·',    # middle dot
}

from collections import Counter
counts = Counter()
for pattern, replacement in replacements.items():
    c = text.count(pattern)
    if c > 0:
        counts[pattern] = (c, replacement)

print(f"{'Appears as':<20} {'Count':>6}  {'Should be':<6}")
print("-" * 40)
total = 0
for pattern, (count, repl) in sorted(counts.items(), key=lambda x: -x[1][0]):
    print(f"{repr(pattern):<20} {count:>6}  {repr(repl)}")
    total += count

print(f"\nTotal: {total} replacements needed")

# Also check for Â followed by a space (artifact of Â being left over)
c_a_space = text.count('Â ')
if c_a_space:
    print(f"\n'Â ' (stray Â + space): {c_a_space} instances")
