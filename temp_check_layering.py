"""Check JTO and TAO layering math against V14 DCA grid config."""
import os, sys, json
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")
from dotenv import load_dotenv
load_dotenv(r"C:\Users\Never\.openclaw\workspace\.env")
import ccxt

exchange = ccxt.aster({
    "apiKey": os.getenv("ASTER_API_KEY"),
    "secret": os.getenv("ASTER_API_SECRET"),
    "options": {"defaultType": "swap"},
})
exchange.load_markets()

# V14 DCA Grid Parameters (from V14Config, high profile)
BO_PCT = 0.30        # 30% base order
SO_DEV = 0.025       # 2.5% between safety orders
SO_MULT = 1.5        # 1.5x volume per layer
TP_PCT = 0.015       # 1.5% take profit
MAX_LAYERS = 12      # high profile

# State file
state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
with open(state_path) as f:
    state = json.load(f)

for sym in ["JTO/USDT", "TAO/USDT"]:
    print(f"\n{'='*60}")
    print(f"  {sym}")
    print(f"{'='*60}")
    
    cs = state.get("coins", {}).get(sym, {})
    eng = cs.get("engine_state", {})
    alloc = cs.get("allocated_capital", 0)
    eng_cap = eng.get("capital", 0)
    
    print(f"\nAllocation: ${alloc:.2f}")
    print(f"Engine capital (remaining): ${eng_cap:.2f}")
    print(f"Long coins: {eng.get('long_coins', 0)}")
    print(f"Long avg entry: ${eng.get('long_avg_entry', 0)}")
    print(f"Long layers: {eng.get('long_layers', 0)}")
    print(f"Long cost: ${eng.get('long_cost', 0):.2f}")
    print(f"Long TP: ${eng.get('long_tp', 0)}")
    
    # Exchange position
    aster_sym = f"{sym}:USDT"
    positions = exchange.fetch_positions([aster_sym])
    for p in positions:
        if abs(float(p.get("contracts", 0))) > 0:
            ex_qty = float(p["contracts"])
            ex_entry = float(p["entryPrice"])
            ex_notional = abs(float(p.get("notional", 0)))
            print(f"\nExchange: {ex_qty} @ ${ex_entry}, notional=${ex_notional:.2f}")
    
    # Current price
    ticker = exchange.fetch_ticker(aster_sym)
    current_price = float(ticker.get("last", 0))
    print(f"Current price: ${current_price}")
    
    # Expected grid math
    print(f"\n--- Expected Grid Math ---")
    # L1 = BO_PCT * allocated_capital
    l1_usd = BO_PCT * alloc
    print(f"L1 order size: {BO_PCT*100:.0f}% of ${alloc:.2f} = ${l1_usd:.2f}")
    
    # L2 trigger = entry * (1 - SO_DEV)
    entry = eng.get("long_avg_entry", 0)
    if entry > 0:
        l2_trigger = entry * (1 - SO_DEV)
        print(f"L2 trigger price: ${entry:.4f} * (1 - {SO_DEV}) = ${l2_trigger:.4f}")
        print(f"Current vs L2 trigger: ${current_price:.4f} {'< SHOULD TRIGGER' if current_price <= l2_trigger else '> not yet'}")
        
        # L2 size = L1 * SO_MULT
        l2_usd = l1_usd * SO_MULT
        print(f"L2 order size: ${l1_usd:.2f} * {SO_MULT} = ${l2_usd:.2f}")
        
        # L3 trigger
        if eng.get("long_layers", 0) >= 2:
            l2_entry = eng.get("long_avg_entry", 0)  # avg after L2
            l3_trigger = l2_entry * (1 - SO_DEV)
            l3_usd = l2_usd * SO_MULT
            print(f"\nL3 trigger: ${l3_trigger:.4f}")
            print(f"L3 order size: ${l3_usd:.2f}")
            print(f"Current vs L3 trigger: ${current_price:.4f} {'< SHOULD TRIGGER' if current_price <= l3_trigger else '> not yet'}")
    
    # TP math
    avg_entry = eng.get("long_avg_entry", 0)
    if avg_entry > 0:
        expected_tp = avg_entry * (1 + TP_PCT)
        actual_tp = eng.get("long_tp", 0)
        print(f"\nTP: avg_entry ${avg_entry:.6f} * 1.015 = ${expected_tp:.6f}")
        print(f"Actual TP in state: ${actual_tp}")
        if abs(expected_tp - actual_tp) > 0.0001:
            print(f"  ⚠️ MISMATCH: diff = ${abs(expected_tp - actual_tp):.6f}")
        else:
            print(f"  ✅ Match")
    
    # Open orders
    print(f"\nOpen orders on exchange:")
    orders = exchange.fetch_open_orders(aster_sym)
    for o in orders:
        otype = o.get("info", {}).get("type", "?")
        act = o.get("info", {}).get("activatePrice", "")
        cb = o.get("info", {}).get("priceRate", "")
        oprice = o.get("price", "")
        print(f"  id={o['id']} type={otype} side={o['side']} qty={o.get('amount')} price={oprice} activate={act} cb={cb}%")
