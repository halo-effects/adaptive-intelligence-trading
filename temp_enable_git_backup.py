"""Re-enable the git backup cron."""
import json
cron_path = r"C:\Users\Never\.openclaw\cron\jobs.json"
with open(cron_path, encoding='utf-8') as f:
    data = json.load(f)
for j in data['jobs']:
    if 'Workspace Git Backup' in j.get('name', ''):
        j['enabled'] = True
        print(f'Re-enabled: {j["name"]}')
with open(cron_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
