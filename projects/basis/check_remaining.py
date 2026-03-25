#!/usr/bin/env python3
path = r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs\COMPLETE.md'
with open(path, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
for i, line in enumerate(lines, 1):
    if b'\xc3\xa2' in line:
        idx = line.find(b'\xc3\xa2')
        context = line[max(0,idx-20):idx+20]
        print(f"  L{i}: {context.decode('utf-8', errors='replace')}")
