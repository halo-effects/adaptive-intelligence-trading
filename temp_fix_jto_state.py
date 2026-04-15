"""Fix JTO tp_type in both state.json and status.json. Bot must be dead."""
import json, os

for fname in ["state.json", "status.json"]:
    path = os.path.join(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm", fname)
    with open(path) as f:
        data = json.load(f)
    
    jto = data.get("coins", {}).get("JTO/USDT", {})
    if jto:
        old = jto.get("tp_type", "?")
        jto["tp_type"] = "trailing"
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
        print(f"{fname}: JTO tp_type {old} -> trailing")
    else:
        print(f"{fname}: JTO not found")
