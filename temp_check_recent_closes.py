import json

with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json") as f:
    d = json.load(f)

# Check if status.json has closed trades
if "closed_trades" in d:
    for t in d["closed_trades"][-10:]:
        print(t)
elif "recent_trades" in d:
    for t in d["recent_trades"][-10:]:
        print(t)
else:
    print("No closed_trades or recent_trades in status.json")
    print("Keys:", [k for k in d.keys()])
