import json, os
path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json"
with open(path) as f:
    s = json.load(f)

tao = s.get("coins", {}).get("TAO/USDT", {})
if tao:
    tao["tp_type"] = "trailing"
    print(f"TAO tp_type set to 'trailing'")

tmp = path + ".tmp"
with open(tmp, "w") as f:
    json.dump(s, f, indent=2)
os.replace(tmp, path)
print("status.json updated")
