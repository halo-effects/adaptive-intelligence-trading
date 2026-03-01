"""
V13 Isolated Gate Tests — Find best signal combinations for 3 major transitions.

For each known transition, test every signal and combination at that exact moment.
Goal: find gates that fire on real transitions, DON'T fire on false signals.
"""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "candles.db"

# ══════════════════════════════════════════════════════════════
# GROUND TRUTH — manually identified transitions (Sep 2024 -> present)
# ══════════════════════════════════════════════════════════════

TRANSITIONS = {
    "BTC/USDC": [
        {"date": "2024-10-15", "type": "RANGING_TO_MARKUP", "desc": "Breakout above $67K, pre-election rally starts"},
        {"date": "2024-12-20", "type": "MARKUP_TO_RANGING", "desc": "ATH rejection ~$108K, begins consolidation"},
        {"date": "2025-02-10", "type": "RANGING_TO_MARKDOWN", "desc": "Breaks below SMA50, markdown begins"},
        # FALSE SIGNALS — corrections that should NOT trigger phase change
        {"date": "2024-11-25", "type": "FALSE_EXIT", "desc": "Mid-markup correction $99K->$93K, resumes up"},
        {"date": "2024-12-10", "type": "FALSE_EXIT", "desc": "Pre-ATH dip $97K, resumes to $108K"},
    ],
    "ETH/USDC": [
        {"date": "2024-11-10", "type": "RANGING_TO_MARKUP", "desc": "Breakout with BTC, $2400->$4000"},
        {"date": "2024-12-10", "type": "MARKUP_TO_RANGING", "desc": "Rejection from $4K, distribution starts"},
        {"date": "2025-01-20", "type": "RANGING_TO_MARKDOWN", "desc": "Failed to hold, markdown accelerates"},
        # FALSE SIGNALS
        {"date": "2024-12-25", "type": "FALSE_EXIT", "desc": "Xmas dip to $3335, bounced back"},
    ],
    "SOL/USDC": [
        {"date": "2024-10-20", "type": "RANGING_TO_MARKUP", "desc": "Breakout above $160, rally to $260+"},
        {"date": "2024-12-20", "type": "MARKUP_TO_RANGING", "desc": "Rejection from highs, consolidation"},
        {"date": "2025-02-03", "type": "RANGING_TO_MARKDOWN", "desc": "Sharp decline from $216, markdown confirmed"},
        # FALSE SIGNALS
        {"date": "2024-11-26", "type": "FALSE_EXIT", "desc": "Mid-markup dip $234->$231, resumes"},
        {"date": "2025-01-09", "type": "FALSE_EXIT", "desc": "Dip to $185, rallied back to $252"},
    ],
}


def load_daily(conn, symbol):
    """Load daily candles with indicators from DB."""
    df = pd.read_sql_query(
        "SELECT * FROM candles_daily WHERE symbol=? ORDER BY date",
        conn, params=(symbol,)
    )
    return df


def safe_cfgi_get(cfgi_series, date_str):
    """Safe CFGI lookup."""
    val = cfgi_series.get(date_str[:10], np.nan)
    if isinstance(val, pd.Series):
        return val.iloc[-1] if len(val) > 0 else np.nan
    return val


def load_cfgi(conn, symbol):
    """Load CFGI daily values."""
    coin = symbol.split("/")[0]
    df = pd.read_sql_query(
        "SELECT date, cfgi FROM cfgi_daily WHERE symbol=? ORDER BY date",
        conn, params=(coin,)
    )
    df['date'] = df['date'].str[:10]
    return df.set_index('date')['cfgi']


def get_indicators_at(df, cfgi, date, lookback_days=14):
    """Get all indicator values at a specific date + context from recent days."""
    idx = df[df['date'] <= date].index
    if len(idx) == 0:
        return None
    
    i = idx[-1]
    row = df.iloc[i]
    
    # Get CFGI and recent CFGI
    cfgi_val = safe_cfgi_get(cfgi, date)
    
    # CFGI trend (last 14 days)
    cfgi_values = []
    for d in range(lookback_days):
        dt = (pd.Timestamp(date) - pd.Timedelta(days=d)).strftime('%Y-%m-%d')
        v = safe_cfgi_get(cfgi, dt)
        if not (isinstance(v, float) and np.isnan(v)):
            cfgi_values.append(v)
    
    cfgi_max_14d = max(cfgi_values) if cfgi_values else np.nan
    cfgi_min_14d = min(cfgi_values) if cfgi_values else np.nan
    cfgi_change_14d = cfgi_values[0] - cfgi_values[-1] if len(cfgi_values) >= 2 else 0
    
    return {
        'date': date,
        'price': row['close'],
        'sma50': row['sma50'],
        'sma200': row['sma200'],
        'price_vs_sma50': row['price_vs_sma50'],
        'price_vs_sma200': row['price_vs_sma200'],
        'sma50_slope': row['sma50_slope'],
        'sma200_slope': row['sma200_slope'],
        'sma50_above_sma200': row['sma50'] > row['sma200'] if not pd.isna(row['sma50']) else None,
        'bb_width': row['bb_width'],
        'bb_pct': row['bb_pct'],
        'adx': row['adx'],
        'plus_di': row['plus_di'],
        'minus_di': row['minus_di'],
        'di_bullish': row['plus_di'] > row['minus_di'] if not pd.isna(row['plus_di']) else None,
        'rsi14': row['rsi14'],
        'atr_pct': row['atr_pct'],
        'consec_hh_hl': int(row['consec_hh_hl']),
        'consec_lh_ll': int(row['consec_lh_ll']),
        'cfgi': cfgi_val,
        'cfgi_max_14d': cfgi_max_14d,
        'cfgi_min_14d': cfgi_min_14d,
        'cfgi_change_14d': cfgi_change_14d,
    }


# ══════════════════════════════════════════════════════════════
# GATE DEFINITIONS — each returns True/False
# ══════════════════════════════════════════════════════════════

def gate_golden_cross(ind):
    """SMA50 > SMA200 (bullish trend)"""
    return ind['sma50_above_sma200'] == True

def gate_death_cross(ind):
    """SMA50 < SMA200 (bearish trend)"""
    return ind['sma50_above_sma200'] == False

def gate_price_above_sma50(ind):
    """Price > SMA50"""
    v = ind['price_vs_sma50']
    return v is not None and not pd.isna(v) and v > 0

def gate_price_below_sma50(ind):
    """Price < SMA50"""
    v = ind['price_vs_sma50']
    return v is not None and not pd.isna(v) and v < 0

def gate_price_above_sma200(ind):
    """Price > SMA200"""
    v = ind['price_vs_sma200']
    return v is not None and not pd.isna(v) and v > 0

def gate_price_below_sma200(ind):
    """Price < SMA200"""
    v = ind['price_vs_sma200']
    return v is not None and not pd.isna(v) and v < 0

def gate_sma50_slope_positive(ind):
    """SMA50 trending up (slope > 0.3%)"""
    v = ind['sma50_slope']
    return v is not None and not pd.isna(v) and v > 0.3

def gate_sma50_slope_negative(ind):
    """SMA50 trending down (slope < -0.3%)"""
    v = ind['sma50_slope']
    return v is not None and not pd.isna(v) and v < -0.3

def gate_adx_trending(ind):
    """ADX > 25 (strong trend)"""
    v = ind['adx']
    return v is not None and not pd.isna(v) and v > 25

def gate_adx_ranging(ind):
    """ADX < 20 (no trend)"""
    v = ind['adx']
    return v is not None and not pd.isna(v) and v < 20

def gate_di_bullish(ind):
    """+DI > -DI (bullish momentum)"""
    return ind['di_bullish'] == True

def gate_di_bearish(ind):
    """-DI > +DI (bearish momentum)"""
    return ind['di_bullish'] == False

def gate_rsi_above_50(ind):
    """RSI > 50 (bullish momentum)"""
    v = ind['rsi14']
    return v is not None and not pd.isna(v) and v > 50

def gate_rsi_below_50(ind):
    """RSI < 50 (bearish momentum)"""
    v = ind['rsi14']
    return v is not None and not pd.isna(v) and v < 50

def gate_rsi_overbought(ind):
    """RSI > 70 (overbought)"""
    v = ind['rsi14']
    return v is not None and not pd.isna(v) and v > 70

def gate_cfgi_greed(ind):
    """CFGI > 60 (greed territory)"""
    v = ind['cfgi']
    return v is not None and not (isinstance(v, float) and np.isnan(v)) and v > 60

def gate_cfgi_fear(ind):
    """CFGI < 40 (fear territory)"""
    v = ind['cfgi']
    return v is not None and not (isinstance(v, float) and np.isnan(v)) and v < 40

def gate_cfgi_declining(ind):
    """CFGI dropped > 15 points in last 14 days"""
    v = ind['cfgi_change_14d']
    return v is not None and not (isinstance(v, float) and np.isnan(v)) and v < -15

def gate_cfgi_was_greedy(ind):
    """CFGI was >= 70 in last 14 days"""
    v = ind['cfgi_max_14d']
    return v is not None and not (isinstance(v, float) and np.isnan(v)) and v >= 70

def gate_hh_hl_3(ind):
    """3+ consecutive higher highs + higher lows"""
    return ind['consec_hh_hl'] >= 3

def gate_lh_ll_3(ind):
    """3+ consecutive lower highs + lower lows"""
    return ind['consec_lh_ll'] >= 3

def gate_bb_narrow(ind):
    """Bollinger Band width < 12% (ranging)"""
    v = ind['bb_width']
    return v is not None and not pd.isna(v) and v < 12


# ══════════════════════════════════════════════════════════════
# GATE COMBINATIONS for each transition type
# ══════════════════════════════════════════════════════════════

GATE_COMBOS = {
    "RANGING_TO_MARKUP": {
        "G1: Price > SMA50": [gate_price_above_sma50],
        "G2: SMA50 slope +": [gate_sma50_slope_positive],
        "G3: +DI > -DI": [gate_di_bullish],
        "G4: RSI > 50": [gate_rsi_above_50],
        "G5: CFGI > 60": [gate_cfgi_greed],
        "G6: Golden cross": [gate_golden_cross],
        "G7: 3x HH+HL": [gate_hh_hl_3],
        "C1: Price>SMA50 + slope + DI bull": [gate_price_above_sma50, gate_sma50_slope_positive, gate_di_bullish],
        "C2: Price>SMA50 + CFGI>60": [gate_price_above_sma50, gate_cfgi_greed],
        "C3: Price>SMA50 + slope + RSI>50": [gate_price_above_sma50, gate_sma50_slope_positive, gate_rsi_above_50],
        "C4: Golden cross + CFGI>60": [gate_golden_cross, gate_cfgi_greed],
        "C5: Price>SMA50 + slope + CFGI>60 + DI bull": [gate_price_above_sma50, gate_sma50_slope_positive, gate_cfgi_greed, gate_di_bullish],
    },
    "MARKUP_TO_RANGING": {
        "G1: Price < SMA50": [gate_price_below_sma50],
        "G2: SMA50 slope -": [gate_sma50_slope_negative],
        "G3: -DI > +DI": [gate_di_bearish],
        "G4: RSI < 50": [gate_rsi_below_50],
        "G5: ADX < 20": [gate_adx_ranging],
        "G6: BB narrow < 12%": [gate_bb_narrow],
        "G7: CFGI declining (>15pt drop)": [gate_cfgi_declining],
        "G8: CFGI was greedy + now declining": [gate_cfgi_was_greedy, gate_cfgi_declining],
        "C1: -DI>+DI + RSI<50": [gate_di_bearish, gate_rsi_below_50],
        "C2: Price<SMA50 + -DI>+DI": [gate_price_below_sma50, gate_di_bearish],
        "C3: ADX<20 + BB<12%": [gate_adx_ranging, gate_bb_narrow],
        "C4: RSI<50 + CFGI declining + was greedy": [gate_rsi_below_50, gate_cfgi_declining, gate_cfgi_was_greedy],
        "C5: -DI>+DI + CFGI declining": [gate_di_bearish, gate_cfgi_declining],
    },
    "RANGING_TO_MARKDOWN": {
        "G1: Price < SMA50": [gate_price_below_sma50],
        "G2: Price < SMA200": [gate_price_below_sma200],
        "G3: SMA50 slope -": [gate_sma50_slope_negative],
        "G4: -DI > +DI": [gate_di_bearish],
        "G5: RSI < 50": [gate_rsi_below_50],
        "G6: CFGI < 40": [gate_cfgi_fear],
        "G7: ADX trending (>25)": [gate_adx_trending],
        "G8: 3x LH+LL": [gate_lh_ll_3],
        "C1: Price<SMA50 + -DI>+DI + CFGI<40": [gate_price_below_sma50, gate_di_bearish, gate_cfgi_fear],
        "C2: Price<SMA50 + slope- + RSI<50": [gate_price_below_sma50, gate_sma50_slope_negative, gate_rsi_below_50],
        "C3: -DI>+DI + ADX>25 + CFGI<40": [gate_di_bearish, gate_adx_trending, gate_cfgi_fear],
        "C4: Price<SMA50 + -DI>+DI + slope-": [gate_price_below_sma50, gate_di_bearish, gate_sma50_slope_negative],
    },
}

# FALSE_EXIT should NOT trigger any exit/markdown gates
FALSE_GATE_COMBOS = {
    "FALSE_EXIT": {
        # Test all MARKUP_TO_RANGING and RANGING_TO_MARKDOWN gates
        # They should all return FALSE (not fire) during corrections
    }
}


def test_gates(ind, gates):
    """Test a gate combination. Returns True only if ALL gates pass."""
    return all(gate(ind) for gate in gates)


def main():
    conn = sqlite3.connect(str(DB_PATH))
    
    print("=" * 90)
    print("V13 ISOLATED GATE TESTS")
    print("Testing signal combinations at known phase transitions")
    print("=" * 90)
    
    # Collect results for summary
    all_results = {}
    
    for symbol, transitions in TRANSITIONS.items():
        df = load_daily(conn, symbol)
        cfgi = load_cfgi(conn, symbol)
        
        if len(df) == 0:
            print(f"\n{symbol}: NO DATA")
            continue
        
        print(f"\n{'#' * 90}")
        print(f"# {symbol}")
        print(f"{'#' * 90}")
        
        for trans in transitions:
            date = trans['date']
            ttype = trans['type']
            desc = trans['desc']
            
            ind = get_indicators_at(df, cfgi, date)
            if ind is None:
                print(f"\n  {date} [{ttype}]: NO DATA")
                continue
            
            print(f"\n  --- {date} [{ttype}] ---")
            print(f"  {desc}")
            print(f"  Price: ${ind['price']:.2f} | SMA50: {ind['price_vs_sma50']:+.1f}% | SMA200: {ind['price_vs_sma200']:+.1f}%")
            print(f"  ADX: {ind['adx']:.1f} | +DI: {ind['plus_di']:.1f} | -DI: {ind['minus_di']:.1f} | RSI: {ind['rsi14']:.1f}")
            cfgi_str = f"{ind['cfgi']:.0f}" if ind['cfgi'] is not None and not (isinstance(ind['cfgi'], float) and np.isnan(ind['cfgi'])) else "N/A"
            print(f"  CFGI: {cfgi_str} | Max14d: {ind['cfgi_max_14d']:.0f} | Change14d: {ind['cfgi_change_14d']:+.0f}")
            print(f"  SMA50 slope: {ind['sma50_slope']:.3f}% | BB width: {ind['bb_width']:.1f}% | HH/HL: {ind['consec_hh_hl']} | LH/LL: {ind['consec_lh_ll']}")
            
            # Test appropriate gates
            if ttype == "FALSE_EXIT":
                # Test all exit/markdown gates — they should NOT fire
                print(f"\n  GATE TESTS (should all be FALSE for false exits):")
                for combo_set in ["MARKUP_TO_RANGING", "RANGING_TO_MARKDOWN"]:
                    for name, gates in GATE_COMBOS[combo_set].items():
                        result = test_gates(ind, gates)
                        status = "!! FAIL (false positive) !!" if result else "OK (correctly blocked)"
                        print(f"    [{combo_set}] {name}: {status}")
                        
                        key = f"{combo_set}|{name}"
                        if key not in all_results:
                            all_results[key] = {"real_pass": 0, "real_total": 0, "false_pass": 0, "false_total": 0}
                        all_results[key]["false_total"] += 1
                        if result:
                            all_results[key]["false_pass"] += 1
            else:
                # Test matching gates — they SHOULD fire
                if ttype in GATE_COMBOS:
                    print(f"\n  GATE TESTS (should be TRUE for real transitions):")
                    for name, gates in GATE_COMBOS[ttype].items():
                        result = test_gates(ind, gates)
                        status = "PASS" if result else "MISS"
                        print(f"    {name}: {status}")
                        
                        key = f"{ttype}|{name}"
                        if key not in all_results:
                            all_results[key] = {"real_pass": 0, "real_total": 0, "false_pass": 0, "false_total": 0}
                        all_results[key]["real_total"] += 1
                        if result:
                            all_results[key]["real_pass"] += 1
    
    conn.close()
    
    # ══════════════════════════════════════════════════════════════
    # SUMMARY — which gates work best?
    # ══════════════════════════════════════════════════════════════
    print(f"\n\n{'=' * 90}")
    print("GATE EFFECTIVENESS SUMMARY")
    print(f"{'=' * 90}")
    
    for transition_type in ["RANGING_TO_MARKUP", "MARKUP_TO_RANGING", "RANGING_TO_MARKDOWN"]:
        print(f"\n--- {transition_type} ---")
        print(f"{'Gate':<55} {'Detect':>8} {'FalsePos':>10} {'Score':>7}")
        print("-" * 85)
        
        scored = []
        for key, counts in sorted(all_results.items()):
            if not key.startswith(transition_type + "|"):
                continue
            name = key.split("|", 1)[1]
            
            detect_rate = counts['real_pass'] / counts['real_total'] * 100 if counts['real_total'] > 0 else 0
            false_pos_rate = counts['false_pass'] / counts['false_total'] * 100 if counts['false_total'] > 0 else 0
            
            # Score: detection rate - 2x false positive rate (penalize false positives heavily)
            score = detect_rate - 2 * false_pos_rate
            
            print(f"{name:<55} {counts['real_pass']}/{counts['real_total']} ({detect_rate:>3.0f}%) "
                  f"{counts['false_pass']}/{counts['false_total']} ({false_pos_rate:>3.0f}%)  {score:>+5.0f}")
            scored.append((name, score, detect_rate, false_pos_rate))
        
        if scored:
            best = max(scored, key=lambda x: x[1])
            print(f"\n  >> BEST: {best[0]} (score {best[1]:+.0f}, detect {best[2]:.0f}%, false pos {best[3]:.0f}%)")


if __name__ == "__main__":
    main()
