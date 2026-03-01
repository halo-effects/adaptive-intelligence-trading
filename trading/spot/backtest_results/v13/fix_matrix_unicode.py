#!/usr/bin/env python3
"""Fix unicode dashes in v13_dca_transition_matrix.py"""

path = 'v13_dca_transition_matrix.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace em-dash patterns with regular hyphens
content = content.replace("{'─'", "{'−'")  # Temp mark
content = content.replace("'─'", "'-'")    # Fix main dashes
content = content.replace("{'−'", "{'−'")  # Keep marked

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed unicode dashes in matrix")
