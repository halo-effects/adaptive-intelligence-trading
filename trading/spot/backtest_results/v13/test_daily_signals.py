"""
V13 Signal Test: Analyze daily indicators at known phase transitions.
Focus: BTC, ETH, SOL from Sep 2024 → present (one full cycle).

Outputs a readable table showing indicator values at key dates,
plus a scan for when each signal would have fired.
"""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "candles.db"

# Test coins — use USDC pairs for longer history, fall back to USDT
TEST_COINS = ["BTC/USDC", "ETH/USDC", "SOL/USDC"]


def load_daily(conn, symbol, start_date="2024-07-01"):
    """Load daily candles + indicators from DB. Start early for SMA warmup."""
    df = pd.read_sql_query(
        "SELECT * FROM candles_daily WHERE symbol=? AND date>=? ORDER BY date",
        conn, params=(symbol, start_date)
    )
    if len(df) == 0:
        # Try USDT pair
        alt = symbol.replace("/USDC", "/USDT")
        df = pd.read_sql_query(
            "SELECT * FROM candles_daily WHERE symbol=? AND date>=? ORDER BY date",
            conn, params=(alt, start_date)
        )
        if len(df) > 0:
            print(f"  Using {alt} (no USDC data from {start_date})")
    return df


def load_cfgi(conn, symbol):
    """Load CFGI daily values for a coin."""
    coin = symbol.split("/")[0]
    df = pd.read_sql_query(
        "SELECT date, cfgi FROM cfgi_daily WHERE symbol=? ORDER BY date",
        conn, params=(coin,)
    )
    # Clean date format — strip time component if present
    df['date'] = df['date'].str[:10]
    return df.set_index('date')['cfgi']


def _cfgi_get(cfgi_series, date_str, default=np.nan):
    """Safe CFGI lookup that handles duplicate index entries."""
    val = cfgi_series.get(date_str[:10], default)
    if isinstance(val, pd.Series):
        return val.iloc[-1] if len(val) > 0 else default
    return val


def detect_phase_signals(df, cfgi):
    """Scan daily data and detect phase transition signals.
    
    Returns list of detected signals with dates and reasons.
    """
    signals = []
    
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        date = row['date']
        
        # Get CFGI for this date
        cfgi_val = _cfgi_get(cfgi, date)
        cfgi_prev = _cfgi_get(cfgi, prev['date'])
        
        # --- RANGING SIGNALS ---
        # ADX < 20 + BB width contracting
        if not pd.isna(row['adx']) and row['adx'] < 20 and not pd.isna(row['bb_width']) and row['bb_width'] < 10:
            signals.append({
                'date': date, 'signal': 'RANGING',
                'reason': f"ADX={row['adx']:.1f}<20, BB_width={row['bb_width']:.1f}%<10%",
                'price': row['close'], 'cfgi': cfgi_val
            })
        
        # --- MARKUP SIGNALS ---
        # SMA50 crosses above SMA200 (golden cross)
        if (not pd.isna(row['sma50']) and not pd.isna(row['sma200']) and
            not pd.isna(prev['sma50']) and not pd.isna(prev['sma200'])):
            if prev['sma50'] <= prev['sma200'] and row['sma50'] > row['sma200']:
                signals.append({
                    'date': date, 'signal': 'MARKUP_GOLDEN_CROSS',
                    'reason': f"SMA50={row['sma50']:.0f} crossed above SMA200={row['sma200']:.0f}",
                    'price': row['close'], 'cfgi': cfgi_val
                })
        
        # Price above SMA50 + SMA50 slope positive + CFGI > 50
        if (not pd.isna(row['price_vs_sma50']) and row['price_vs_sma50'] > 0 and
            not pd.isna(row['sma50_slope']) and row['sma50_slope'] > 0.5 and
            not pd.isna(cfgi_val) and cfgi_val > 50):
            signals.append({
                'date': date, 'signal': 'MARKUP_TREND',
                'reason': f"Price>{row['sma50']:.0f}(SMA50), slope={row['sma50_slope']:.2f}%, CFGI={cfgi_val:.0f}>50",
                'price': row['close'], 'cfgi': cfgi_val
            })
        
        # 3+ consecutive higher highs and higher lows
        if row['consec_hh_hl'] >= 3:
            signals.append({
                'date': date, 'signal': 'MARKUP_STRUCTURE',
                'reason': f"{int(row['consec_hh_hl'])} consecutive HH+HL days",
                'price': row['close'], 'cfgi': cfgi_val
            })
        
        # --- DISTRIBUTION / "TOP IS IN" SIGNALS ---
        # RSI divergence: price making new highs but RSI declining
        if (not pd.isna(row['rsi14']) and row['rsi14'] < 60 and
            not pd.isna(row['price_vs_sma50']) and row['price_vs_sma50'] > 5):
            signals.append({
                'date': date, 'signal': 'DISTRIBUTION_RSI_DIV',
                'reason': f"RSI={row['rsi14']:.0f}<60 but price {row['price_vs_sma50']:.1f}% above SMA50",
                'price': row['close'], 'cfgi': cfgi_val
            })
        
        # CFGI declining from greed: was ≥70, now <50
        if (not pd.isna(cfgi_val) and cfgi_val < 50 and not pd.isna(cfgi_prev) and cfgi_prev >= 50):
            # Check if CFGI was ≥70 in the last 14 days
            recent_dates = [(pd.Timestamp(date) - pd.Timedelta(days=d)).strftime('%Y-%m-%d') for d in range(1, 15)]
            recent_cfgi = [_cfgi_get(cfgi, d) for d in recent_dates]
            if any(c >= 70 for c in recent_cfgi if not isinstance(c, float) or not np.isnan(c)):
                signals.append({
                    'date': date, 'signal': 'DISTRIBUTION_CFGI_DROP',
                    'reason': f"CFGI dropped to {cfgi_val:.0f} from greed (was ≥70 in last 14d)",
                    'price': row['close'], 'cfgi': cfgi_val
                })
        
        # SMA50 crosses below SMA200 (death cross)
        if (not pd.isna(row['sma50']) and not pd.isna(row['sma200']) and
            not pd.isna(prev['sma50']) and not pd.isna(prev['sma200'])):
            if prev['sma50'] >= prev['sma200'] and row['sma50'] < row['sma200']:
                signals.append({
                    'date': date, 'signal': 'MARKDOWN_DEATH_CROSS',
                    'reason': f"SMA50={row['sma50']:.0f} crossed below SMA200={row['sma200']:.0f}",
                    'price': row['close'], 'cfgi': cfgi_val
                })
        
        # --- MARKDOWN SIGNALS ---
        # 3+ consecutive lower highs and lower lows
        if row['consec_lh_ll'] >= 3:
            signals.append({
                'date': date, 'signal': 'MARKDOWN_STRUCTURE',
                'reason': f"{int(row['consec_lh_ll'])} consecutive LH+LL days",
                'price': row['close'], 'cfgi': cfgi_val
                })
        
        # Price below SMA200 + SMA50 slope negative
        if (not pd.isna(row['price_vs_sma200']) and row['price_vs_sma200'] < 0 and
            not pd.isna(row['sma50_slope']) and row['sma50_slope'] < -0.5):
            signals.append({
                'date': date, 'signal': 'MARKDOWN_TREND',
                'reason': f"Price below SMA200 ({row['price_vs_sma200']:.1f}%), SMA50 slope={row['sma50_slope']:.2f}%",
                'price': row['close'], 'cfgi': cfgi_val
            })
    
    return signals


def print_indicator_snapshot(df, cfgi, date, label=""):
    """Print all indicator values at a specific date."""
    row = df[df['date'] == date]
    if len(row) == 0:
        # Find nearest date
        all_dates = df['date'].values
        idx = np.searchsorted(all_dates, date)
        if idx >= len(all_dates):
            idx = len(all_dates) - 1
        date = all_dates[idx]
        row = df[df['date'] == date]
    
    if len(row) == 0:
        print(f"  No data for {date}")
        return
    
    r = row.iloc[0]
    cfgi_val = cfgi.get(date[:10], np.nan)
    if isinstance(cfgi_val, pd.Series):
        cfgi_val = cfgi_val.iloc[-1] if len(cfgi_val) > 0 else np.nan
    
    print(f"\n  {'='*60}")
    print(f"  {label} — {date} — Price: ${r['close']:.2f}")
    print(f"  {'='*60}")
    print(f"  SMA50: {r['sma50']:.2f}  |  SMA200: {r['sma200']:.2f}")
    print(f"  Price vs SMA50: {r['price_vs_sma50']:+.1f}%  |  vs SMA200: {r['price_vs_sma200']:+.1f}%")
    print(f"  SMA50 slope: {r['sma50_slope']:.3f}%  |  SMA200 slope: {r['sma200_slope']:.3f}%")
    print(f"  BB width: {r['bb_width']:.1f}%  |  BB position: {r['bb_pct']:.2f}")
    print(f"  ADX: {r['adx']:.1f}  |  +DI: {r['plus_di']:.1f}  |  -DI: {r['minus_di']:.1f}")
    print(f"  RSI(14): {r['rsi14']:.1f}  |  ATR%: {r['atr_pct']:.2f}%")
    print(f"  Consec HH+HL: {int(r['consec_hh_hl'])}  |  Consec LH+LL: {int(r['consec_lh_ll'])}")
    print(f"  CFGI: {cfgi_val:.0f}" if not pd.isna(cfgi_val) else "  CFGI: N/A")


def main():
    conn = sqlite3.connect(str(DB_PATH))
    
    # Key dates for the Sep 2024 → present cycle
    KEY_DATES = {
        "BTC/USDC": {
            "2024-09-01": "Window start — where are we?",
            "2024-10-15": "Pre-breakout rally beginning",
            "2024-11-05": "Election rally — confirmed markup?",
            "2024-12-17": "Near ATH ~$108K — distribution starting?",
            "2025-01-20": "Post-ATH — top is in?",
            "2025-02-03": "Correction or markdown?",
            "2025-02-17": "Latest data",
        },
        "ETH/USDC": {
            "2024-09-01": "Window start",
            "2024-11-05": "Rally with BTC",
            "2024-12-06": "Local top ~$4K",
            "2025-01-07": "Failed to hold highs",
            "2025-02-03": "Markdown or correction?",
            "2025-02-17": "Latest data",
        },
        "SOL/USDC": {
            "2024-09-01": "Window start",
            "2024-11-15": "Rally to ATH area ~$260",
            "2025-01-19": "Local top ~$295",
            "2025-02-03": "Sharp decline",
            "2025-02-17": "Latest data",
        },
    }
    
    for symbol in TEST_COINS:
        print(f"\n{'#'*70}")
        print(f"# {symbol}")
        print(f"{'#'*70}")
        
        df = load_daily(conn, symbol)
        if len(df) == 0:
            print(f"  No daily data — skipping")
            continue
        
        cfgi = load_cfgi(conn, symbol)
        print(f"  Loaded {len(df)} daily candles, {len(cfgi)} CFGI values")
        
        # Snapshots at key dates
        if symbol in KEY_DATES:
            print(f"\n  --- INDICATOR SNAPSHOTS AT KEY DATES ---")
            for date, label in KEY_DATES[symbol].items():
                print_indicator_snapshot(df, cfgi, date, label)
        
        # Scan for phase signals from Sep 2024
        sep_df = df[df['date'] >= '2024-09-01'].copy()
        if len(sep_df) == 0:
            print(f"  No data from Sep 2024")
            continue
        
        signals = detect_phase_signals(sep_df, cfgi)
        
        # Summarize signals by type
        print(f"\n  --- SIGNAL SUMMARY (Sep 2024 -> present) ---")
        signal_types = {}
        for s in signals:
            sig = s['signal']
            if sig not in signal_types:
                signal_types[sig] = []
            signal_types[sig].append(s)
        
        for sig_type in sorted(signal_types.keys()):
            entries = signal_types[sig_type]
            # Group consecutive days — only show first occurrence in each cluster
            clusters = []
            current_cluster = [entries[0]]
            for e in entries[1:]:
                # If within 5 days of last entry in cluster, same cluster
                prev_date = pd.Timestamp(current_cluster[-1]['date'])
                this_date = pd.Timestamp(e['date'])
                if (this_date - prev_date).days <= 5:
                    current_cluster.append(e)
                else:
                    clusters.append(current_cluster)
                    current_cluster = [e]
            clusters.append(current_cluster)
            
            print(f"\n  {sig_type}: {len(clusters)} occurrences ({len(entries)} total days)")
            for cluster in clusters[:10]:  # Show first 10 clusters
                first = cluster[0]
                last = cluster[-1]
                duration = f" ({len(cluster)}d)" if len(cluster) > 1 else ""
                print(f"    {first['date']}{' -> ' + last['date'] if len(cluster) > 1 else ''}{duration}: "
                      f"${first['price']:.0f}, CFGI={first['cfgi']:.0f}" if not pd.isna(first['cfgi']) 
                      else f"    {first['date']}: ${first['price']:.0f}, CFGI=N/A")
    
    conn.close()
    print(f"\n{'='*70}")
    print("DONE — Review indicator snapshots at key dates to validate signal accuracy")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
