"""Quick backtest: 0.2% callback vs 0.25% and 0.3%"""
import sqlite3, numpy as np

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
conn = sqlite3.connect(DB)

COINS = ["TAO/USDT", "ZEC/USDT", "FET/USDT", "JTO/USDT", "HYPE/USDT"]
CAP = 50000; PC = CAP / 5
BO = 0.30; TP = 0.015; SO_DEV = 0.025; SO_MULT = 1.5; MAX_L = 12
TF = 0.00035; MF = 0.00025

def get_candles(sym):
    rows = conn.execute(
        "SELECT timestamp,open,high,low,close FROM candles WHERE symbol=? AND timeframe='1h' ORDER BY timestamp",
        (sym,)).fetchall()
    return rows[-365*24:] if len(rows) > 365*24 else rows

def sim(candles, act, cb):
    cap = PC; pnl = 0; trades = 0; wins = 0; tpnls = []
    coins = 0.0; avg = 0.0; layers = 0; cost = 0.0
    ta = False; tp = 0.0
    for ts, o, h, l, c in candles:
        if c <= 0: continue
        if coins > 0:
            fill = None; taker = False
            if act is None:
                if h >= avg*(1+TP): fill = avg*(1+TP)
            else:
                activation = avg*(1+act)
                if ta:
                    tp = max(tp, h); trigger = tp*(1-cb)
                    if l <= trigger: fill = trigger; taker = True
                elif h >= activation:
                    ta = True; tp = h; trigger = tp*(1-cb)
                    if l <= trigger: fill = trigger; taker = True
            if fill:
                p = coins*fill; fee = p*(TF if taker else MF); pn = p-cost-fee
                pnl += pn; cap += p-fee; trades += 1
                if pn > 0: wins += 1
                tpnls.append(pn/cost*100 if cost > 0 else 0)
                coins=0;avg=0;layers=0;cost=0;ta=False;tp=0;continue
        if layers >= MAX_L: continue
        buy = layers == 0 or (layers >= 1 and c <= avg*(1-SO_DEV))
        if buy and cap > 1:
            order = min(PC*BO*(SO_MULT**layers), cap)
            fee = order*TF; cap -= (order+fee)
            nc = order/c; ov = coins*avg; coins += nc
            avg = (ov+order)/coins if coins > 0 else c
            cost += order+fee; layers += 1; ta = False; tp = 0
    if coins > 0:
        p = coins*candles[-1][4]; fee = p*TF; pn = p-cost-fee
        pnl += pn; trades += 1
        if pn > 0: wins += 1
        tpnls.append(pn/cost*100 if cost > 0 else 0)
    return pnl, trades, wins, tpnls

configs = [
    ("Fixed 1.5%", None, None),
    ("Trail 1.5/0.2%", 0.015, 0.002),
    ("Trail 1.5/0.3%", 0.015, 0.003),
    ("Trail 1.5/0.5%", 0.015, 0.005),
]

print(f"{'Config':<20} {'PnL':>10} {'ROI':>7} {'Trades':>7} {'Win%':>6} {'Avg%':>7} {'vs Fixed':>10}")
print("-" * 70)
fp = None
for name, act, cb in configs:
    tp = tw = 0; tpnl = 0; all_p = []
    for coin in COINS:
        cand = get_candles(coin)
        if not cand: continue
        p, t, w, ps = sim(cand, act, cb)
        tpnl += p; tp += t; tw += w; all_p.extend(ps)
    roi = tpnl/CAP*100; wr = tw/tp*100 if tp > 0 else 0
    avg_p = np.mean(all_p) if all_p else 0
    if fp is None: fp = tpnl
    diff = tpnl - fp
    print(f"{name:<20} ${tpnl:>8,.0f} {roi:>6.1f}% {tp:>6} {wr:>5.1f}% {avg_p:>6.2f}% ${diff:>8,.0f}")
