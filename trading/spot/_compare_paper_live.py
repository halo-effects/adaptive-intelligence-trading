"""Compare paper vs live trade characteristics."""
import csv, json, statistics

def load_trades(path):
    with open(path) as f:
        return list(csv.DictReader(f))

def analyze(trades, label):
    if not trades:
        print(f"\n=== {label}: NO TRADES ===")
        return
    
    returns = []
    pnls = []
    investments = []
    layers_list = []
    durations = []
    
    for t in trades:
        ret = float(t.get("return_pct", 0) or 0)
        pnl = float(t.get("pnl", 0) or 0)
        inv = float(t.get("invested", 0) or 0)
        layers = int(t.get("layers", 0) or 0)
        dur = float(t.get("duration_h", 0) or 0)
        
        returns.append(ret)
        pnls.append(pnl)
        investments.append(inv)
        layers_list.append(layers)
        durations.append(dur)
    
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Total trades:     {len(trades)}")
    print(f"  Win rate:         {len(wins)/len(returns)*100:.1f}%")
    print(f"  Total PnL:        ${sum(pnls):,.2f}")
    print(f"  Avg PnL/trade:    ${statistics.mean(pnls):,.2f}")
    print(f"  Median PnL:       ${statistics.median(pnls):,.2f}")
    print()
    print(f"  RETURN % DISTRIBUTION:")
    print(f"    Mean:           {statistics.mean(returns):.2f}%")
    print(f"    Median:         {statistics.median(returns):.2f}%")
    print(f"    Std Dev:        {statistics.stdev(returns):.2f}%")
    print(f"    Min:            {min(returns):.2f}%")
    print(f"    Max:            {max(returns):.2f}%")
    
    # Percentile buckets
    sorted_ret = sorted(returns)
    n = len(sorted_ret)
    print(f"    P10:            {sorted_ret[int(n*0.1)]:.2f}%")
    print(f"    P25:            {sorted_ret[int(n*0.25)]:.2f}%")
    print(f"    P50:            {sorted_ret[int(n*0.5)]:.2f}%")
    print(f"    P75:            {sorted_ret[int(n*0.75)]:.2f}%")
    print(f"    P90:            {sorted_ret[int(n*0.9)]:.2f}%")
    
    print()
    print(f"  LAYERS DISTRIBUTION:")
    layer_counts = {}
    for l in layers_list:
        layer_counts[l] = layer_counts.get(l, 0) + 1
    for l in sorted(layer_counts.keys()):
        pct = layer_counts[l] / len(layers_list) * 100
        avg_ret = statistics.mean([returns[i] for i in range(len(returns)) if layers_list[i] == l])
        avg_pnl = statistics.mean([pnls[i] for i in range(len(pnls)) if layers_list[i] == l])
        print(f"    {l} layers: {layer_counts[l]:>4} trades ({pct:>5.1f}%) | avg return: {avg_ret:.2f}% | avg PnL: ${avg_pnl:.2f}")
    
    print()
    print(f"  INVESTMENT SIZE:")
    print(f"    Mean:           ${statistics.mean(investments):,.2f}")
    print(f"    Median:         ${statistics.median(investments):,.2f}")
    print(f"    Min:            ${min(investments):,.2f}")
    print(f"    Max:            ${max(investments):,.2f}")
    
    print()
    print(f"  DURATION:")
    print(f"    Mean:           {statistics.mean(durations):.1f}h")
    print(f"    Median:         {statistics.median(durations):.1f}h")
    
    # Multi-layer trades (where the DCA grid depth matters)
    multi = [(returns[i], pnls[i], layers_list[i], investments[i]) for i in range(len(returns)) if layers_list[i] >= 3]
    if multi:
        print()
        print(f"  DEEP GRID TRADES (3+ layers):")
        print(f"    Count:          {len(multi)} ({len(multi)/len(returns)*100:.1f}%)")
        print(f"    Avg return:     {statistics.mean([m[0] for m in multi]):.2f}%")
        print(f"    Avg PnL:        ${statistics.mean([m[1] for m in multi]):.2f}")
        print(f"    Avg invested:   ${statistics.mean([m[3] for m in multi]):,.2f}")

# Load data
paper_trades = load_trades("trading/spot/paper/v14_portfolio/trades.csv")
live_trades = load_trades("trading/spot/live/v14pm/trades.csv")

analyze(paper_trades, "V14PM PAPER (Hyperliquid, $50K)")
analyze(live_trades, "V14PM LIVE (Aster, $300 seed)")

# Direct comparison: what's structurally different?
print()
print("=" * 60)
print("  KEY STRUCTURAL DIFFERENCES")
print("=" * 60)

paper_returns = [float(t.get("return_pct", 0) or 0) for t in paper_trades]
live_returns = [float(t.get("return_pct", 0) or 0) for t in live_trades]

paper_layers = [int(t.get("layers", 0) or 0) for t in paper_trades]
live_layers = [int(t.get("layers", 0) or 0) for t in live_trades]

print(f"  Paper avg return: {statistics.mean(paper_returns):.2f}% vs Live: {statistics.mean(live_returns):.2f}%")
print(f"  Paper avg layers: {statistics.mean(paper_layers):.1f} vs Live: {statistics.mean(live_layers):.1f}")
print(f"  Paper multi-layer%: {sum(1 for l in paper_layers if l >= 2)/len(paper_layers)*100:.1f}% vs Live: {sum(1 for l in live_layers if l >= 2)/len(live_layers)*100:.1f}%")

# The key insight: higher layers = higher return because TP is calculated on 
# the AVERAGE entry price. More layers = lower avg entry = bigger gap to TP target.
print()
print("  WHY MULTI-LAYER TRADES EARN MORE:")
print("  - 1 layer: TP at entry + 1.5% = exactly 1.5% return")
print("  - 2 layers: avg entry is lower, TP still 1.5% above avg = >1.5% from first entry")
print("  - 5 layers: avg entry much lower, TP 1.5% above avg = 4-6% from first entry")
print("  - Paper sees more deep grid trades because:")
print("    a) Larger capital ($50K vs $300) = bigger positions that survive deeper dips")
print("    b) Hyperliquid has real price discovery (fills at actual market)")
print("    c) Aster thin liquidity means entries are already inflated (bad avg)")
