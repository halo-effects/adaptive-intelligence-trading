"""Verify TAO trade PnL accuracy."""
import csv, json
from pathlib import Path

# Check trades.csv for the latest TAO trade
csv_path = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\trades.csv")
if csv_path.exists():
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        tao_trades = [r for r in reader if "TAO" in r.get("symbol", "")]
    
    if tao_trades:
        last = tao_trades[-1]
        print("Latest TAO trade from CSV:")
        for k, v in last.items():
            print(f"  {k}: {v}")
        
        # Manual PnL check
        sell_price = float(last.get("sell_price", last.get("exit_price", 0)))
        avg_entry = float(last.get("avg_entry", last.get("entry_price", 0)))
        qty = float(last.get("qty", last.get("quantity", 0)))
        cost = float(last.get("cost", last.get("invested", 0)))
        pnl = float(last.get("pnl", 0))
        
        if avg_entry > 0 and sell_price > 0:
            expected_pnl = (sell_price - avg_entry) * qty
            pnl_pct_on_entry = (sell_price - avg_entry) / avg_entry * 100
            pnl_pct_on_cost = (pnl / cost * 100) if cost > 0 else 0
            print(f"\n  Manual check:")
            print(f"    Sell: ${sell_price:.6f}, Avg entry: ${avg_entry:.6f}")
            print(f"    Qty: {qty}, Cost: ${cost:.2f}")
            print(f"    Price gain: {pnl_pct_on_entry:.2f}%")
            print(f"    PnL on cost: {pnl_pct_on_cost:.2f}%")
            print(f"    Expected PnL: ${expected_pnl:.2f}")
            print(f"    Reported PnL: ${pnl:.2f}")

# Check status.json for current TAO state
print("\n--- Current status ---")
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json") as f:
    data = json.load(f)
tao = data.get("coins", {}).get("TAO/USDT", {})
print(f"  Layers: {tao.get('layers')}")
print(f"  Invested: ${tao.get('invested', 0):.2f}")
print(f"  Realized PnL: ${tao.get('realized_pnl', 0):.2f}")

# Check bot log for the fill details
print("\n--- Bot log ---")
import subprocess
result = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "Select-String -Path C:\\Users\\Never\\.openclaw\\workspace\\trading\\spot\\live\\v14pm\\bot.log -Pattern 'TAO.*Deal|TAO.*fill|TAO.*SELL|TAO.*pnl|TAO.*trail' | Select-Object -Last 10 | ForEach-Object { $_.Line.Trim().Substring(0, [Math]::Min(150, $_.Line.Trim().Length)) }"],
    capture_output=True, text=True, timeout=10
)
print(result.stdout)
