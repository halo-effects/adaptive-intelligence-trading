import json

paper_path = r"C:\Users\Never\.openclaw\workspace\docs\data\v14-pm\status.json"
live_path = r"C:\Users\Never\.openclaw\workspace\docs\data\v14-pm-live\status.json"

with open(paper_path) as f:
    paper = json.load(f)
with open(live_path) as f:
    live = json.load(f)

paper_coins = list(paper.get("coins", {}).keys())
live_coins = list(live.get("coins", {}).keys())

print(f"Paper PM (v14-pm): {len(paper_coins)} coins: {paper_coins[:5]}")
print(f"Live PM (v14-pm-live): {len(live_coins)} coins: {live_coins}")
print(f"Paper equity: ${paper.get('equity', '?')}")
print(f"Live equity: ${live.get('equity', '?')}")
