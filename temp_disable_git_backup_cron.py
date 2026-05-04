"""Temporarily disable the OpenClaw git backup cron."""
import json

cron_path = r"C:\Users\Never\.openclaw\cron\jobs.json"
with open(cron_path, encoding='utf-8') as f:
    data = json.load(f)

found = False
for j in data['jobs']:
    if 'Workspace Git Backup' in j.get('name', ''):
        j['enabled'] = False
        found = True
        print(f"Disabled: {j['name']}")

if found:
    with open(cron_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print("Saved")
else:
    print("Not found")
