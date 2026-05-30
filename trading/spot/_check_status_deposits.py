import json

with open("trading/spot/live/v14pm/status.json") as f:
    d = json.load(f)

print(f"seed_capital:       ${d.get('seed_capital')}")
print(f"capital:            ${d.get('capital')}")
print(f"tracked_capital:    ${d.get('tracked_capital')}")
print(f"equity:             ${d.get('equity')}")
print(f"total_deposits:     ${d.get('total_deposits')}")
print(f"total_withdrawals:  ${d.get('total_withdrawals')}")
print(f"net_deposits:       ${d.get('net_deposits')}")
print(f"total_realized_pnl: ${d.get('total_realized_pnl')}")
print()

# Dashboard growth calc
cap = d.get("seed_capital") or 300
eq = d.get("equity") or 0
net_dep = d.get("net_deposits") or 0
growth = (eq - cap - net_dep) / cap * 100 if cap > 0 else 0
print(f"Dashboard growth: ({eq} - {cap} - {net_dep}) / {cap} = {growth:.2f}%")
print(f"Expected: close to ({d.get('total_realized_pnl',0)}/{cap}*100) = {d.get('total_realized_pnl',0)/cap*100:.2f}%")
