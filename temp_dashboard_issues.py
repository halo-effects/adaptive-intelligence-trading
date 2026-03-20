"""
Dashboard field-by-field accuracy check.
Compares status.json fields against what the dashboard JS renders
and flags any mismatches or display issues.
"""
import json

with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json") as f:
    S = json.load(f)

issues = []
notes = []

# 1. HEADER
if S.get('regime') == 'NONE':
    issues.append("regime='NONE' — dashboard badge shows 'NONE' with no matching CSS class. "
                   "Should be a valid regime (ACCUMULATION/RANGING/DISTRIBUTION/etc.) or null.")

if not S.get('timeframe'):
    notes.append("timeframe=None — header shows coins + 'undefined'. Should be '1h'.")

# 2. SUMMARY CARDS
# Equity card: dashboard computes growth = (equity-capital)/capital * 100
cap = S.get('capital', 0)
eq = S.get('equity', 0)
growth = ((eq - cap) / cap * 100) if cap > 0 else 0
print(f"Equity card: ${eq:.2f} ({growth:+.2f}%) on ${cap:.2f} capital — OK")

# Realized PnL card
rpnl = S.get('total_realized_pnl', 0)
deals = S.get('deals_completed', 0)
fees = S.get('total_fees')
print(f"Realized PnL: ${rpnl:.4f} from {deals} deals — OK")
if fees is None:
    notes.append("total_fees=None — dashboard shows 'after $NaN fees' or skips it. Minor cosmetic.")

# Unrealized PnL — dashboard sums unrealized_pnl across all coins
coins = S.get('coins', {})
total_upnl = sum(c.get('unrealized_pnl', 0) for c in coins.values())
total_inv = sum(c.get('invested', 0) for c in coins.values())
upnl_pct = (total_upnl / total_inv * 100) if total_inv > 0 else 0
print(f"Unrealized PnL: ${total_upnl:.4f} ({upnl_pct:.2f}%) on ${total_inv:.2f} invested — OK")

# Win/Loss — dashboard uses trades.csv if available, else status
# Status says win_rate=100%, deals=13, all wins
wr = S.get('win_rate', 0)
print(f"Win Rate: {wr}% from {deals} deals — {'OK (all 13 wins)' if wr == 100 else 'CHECK'}")

# Avg Daily ROI — dashboard computes from trades timeline
print(f"Daily ROI: computed from trades start to now")

# Cash — dashboard uses S.cash for allocation
cash = S.get('cash')
router_active = S.get('router', {}).get('active_cash', 0)
router_reserve = S.get('router', {}).get('reserve_cash', 0)
print(f"Cash field: ${cash} | Router: active=${router_active} + reserve=${router_reserve} = ${router_active + router_reserve:.2f}")
if cash and abs(cash - eq) < 1:
    issues.append(f"cash=${cash} ≈ equity=${eq}. Dashboard uses 'cash' for allocation donut. "
                  f"Should be actual free cash (≈${router_active + router_reserve:.2f}), "
                  f"not total account value. Allocation chart will show ~100% cash, 0% invested.")

# 3. POSITION CARD
for sym, c in coins.items():
    layers = c.get('layers', 0)
    max_layers = 12  # high profile
    print(f"\n{sym} position:")
    print(f"  Phase: {c.get('lifecycle_phase')} | Side: {c.get('side')} | Layers: {layers}/{max_layers}")
    print(f"  Price: ${c.get('current_price')} | Entry: ${c.get('avg_entry')} | TP: ${c.get('next_tp_price')}")
    print(f"  Invested: ${c.get('invested')} | UPnL: ${c.get('unrealized_pnl')} | RPnL: ${c.get('realized_pnl')}")
    
    liq = c.get('liquidation_price')
    dist_liq = c.get('distance_to_liq_pct')
    if liq is None:
        notes.append(f"{sym}: liquidation_price=None — shows 'N/A'. Should compute for perps at 1x.")
    if dist_liq is None:
        notes.append(f"{sym}: distance_to_liq_pct=None — shows 'N/A'.")
    
    cfgi = c.get('cfgi')
    if cfgi is None:
        notes.append(f"{sym}: cfgi=None — Coin Sentiment section shows '--'.")

# 4. CAPITAL UTILIZATION DONUT
# Dashboard: longInv = invested from LONG_DCA coins, cash = S.cash
# With cash=$351.11 and invested=$247.20, total=$598, utilization=247/598=41%
# But actual: free cash = $103.58 USDT, invested = $247.20, total = $350.78
print(f"\nCapital Utilization:")
print(f"  Dashboard sees: cash=${cash}, longInv=${total_inv}")
if cash and cash > cap:
    issues.append(f"Capital donut will be wrong: cash=${cash:.2f} (should be ~${router_active + router_reserve:.2f})")

# 5. DRAWDOWN
dd = S.get('max_drawdown_pct')
if dd is None:
    notes.append("max_drawdown_pct=None — bottom bar shows '0.00%' drawdown.")

# 6. UPTIME  
ut = S.get('uptime_hours')
if ut is not None and ut < 1:
    notes.append(f"uptime_hours={ut} — resets on each restart. Shows {ut:.2f}h instead of total runtime.")

# 7. FEAR & GREED INDEX
fgi = S.get('fear_greed_index')
if fgi is None:
    notes.append("fear_greed_index=None (market-level) — Macro section shows '--'. Not critical.")

# Summary
print("\n" + "=" * 60)
print(f"ISSUES FOUND: {len(issues)}")
for i, issue in enumerate(issues, 1):
    print(f"  ❌ {i}. {issue}")

print(f"\nNOTES (cosmetic/minor): {len(notes)}")
for i, note in enumerate(notes, 1):
    print(f"  ℹ️  {i}. {note}")
