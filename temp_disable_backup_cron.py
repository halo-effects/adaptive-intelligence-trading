import json

path = r"C:\Users\Never\.openclaw\cron\jobs.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)

for job in data["jobs"]:
    if job["id"] == "54c4e60f-4c8d-4875-bd8b-042b0b46a8cf":
        job["enabled"] = False
        print("Disabled:", job["name"])
        break

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)
print("Saved")
