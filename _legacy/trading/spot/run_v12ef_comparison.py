#!/usr/bin/env python3
"""V12e vs V12f Comparison Backtest — ETH/SOL/ZEC shared capital.

Runs the same 3-coin shared-capital backtest twice:
  V12e: Equal allocation ($3,333 per coin)
  V12f: Phase-weighted allocation (SPRING 3×, MARKUP 2×, DCA 1×)

Both use identical V12 lifecycle engines with shorts ENABLED.
"""
import sys
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List
from dataclasses import dataclass, asdict

import pandas as pd
import numpy as np

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.backtest_engine_v12 import SpotBacktestEngineV12, LifecyclePhase
from trading.spot.candle_db import CandleDB
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v12ef_comparison"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

KNOWN_ATH = {
    "ETH/USDC": 4878.0, "ETH/USDT": 4878.0,
    "SOL/USDC": 260.0, "SOL/USDT": 260.0,
    "BTC/USDC": 109588.0, "BTC/USDT": 109588.0,
    "ZEC/USDT": 724.0,
}

# V12f phase weights
PHASE_WEIGHTS = {
    "SPRING": 3,
    "MARKUP": 2,
    "DCA": 1,
    "EXIT": 0,
    "MARKDOWN": 0,
}


def create_engine(symbol: str, capital: float, profile: str) -> SpotBacktestEngineV12:
    """Create a V12 engine with shorts ENABLED."""
    params = {
        "symbol": symbol,
        "capital": capital,
        "timeframe": "1h",
        "profile": profile,
        # Conductor
        "v12_exit_threshold": 50.0,
        "v12_mcap_ath_pct": 0.25,
        "v12_commitment_hours": 48,
        # Exit engine
        "v12_initial_trail_pct": 3.0,
        "v12_trail_floor_pct": 1.5,
        "v12_trail_tighten_per_day": 0.5,
        "v12_rally_sell_pct": 1.5,
        "v12_urgency_day_moderate": 4,
        "v12_urgency_day_aggressive": 7,
        "v12_urgency_day_force": 14,
        # Shorts ENABLED for lifecycle play
        "v12_short_enabled": True,
        "v12_short_tier1_deploy": 0.60,
        "v12_short_tier2_deploy": 0.80,
        "v12_short_tier3_deploy": 0.90,
        "v12_short_trail_pct": 10.0,
        "v12_short_sl_pct": 15.0,
        # Spring
        "v12_spring_tier1_discount": 25.0,
        "v12_spring_tier2_discount": 35.0,
        "v12_spring_tier3_discount": 45.0,
        "v12_spring_tier1_deploy": 0.60,
        "v12_spring_tier2_deploy": 0.80,
        "v12_spring_tier3_deploy": 0.90,
        "v12_spring_tp_pct": 15.0,
        # Markup
        "v12_markup_deploy_pct": {"low": 0.50, "medium": 0.70, "high": 0.90}.get(profile, 0.70),
        "v12_markup_trail_pct": 10.0,
        "v12_markup_trail_tighten_score": 30.0,
        "v12_markup_trail_tight_pct": 5.0,
        "v12_markup_pullback_pct": 5.0,
        "v12_markup_pullback_deploy_pct": 0.15,
        "v12_markup_max_adds": 2,
    }
    return SpotBacktestEngineV12(**params)


def compute_phase_allocations(total_capital: float, phases: Dict[str, str]) -> Dict[str, float]:
    """V12f: phase-weighted allocation."""
    available = total_capital * 0.9  # 10% reserve
    min_per_coin = total_capital * 0.04  # 1 base order minimum
    
    weights = {s: PHASE_WEIGHTS.get(p, 1) for s, p in phases.items()}
    total_w = sum(weights.values())
    
    if total_w == 0:
        return {s: min_per_coin for s in phases}
    
    allocs = {}
    for s, w in weights.items():
        raw = (w / total_w) * available
        allocs[s] = max(raw, min_per_coin)
    
    # Scale down if over budget
    total_alloc = sum(allocs.values())
    if total_alloc > available:
        scale = available / total_alloc
        allocs = {s: a * scale for s, a in allocs.items()}
    
    return allocs


def get_fg(fg_data: dict, ts_ms: int) -> int:
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return fg_data.get(dt.strftime("%Y-%m-%d"), 50)


def run_backtest(symbols, capital, profile, coin_dfs, fg_data, mode="v12e"):
    """Run one backtest. mode='v12e' (equal) or 'v12f' (phase-weighted)."""
    
    # Build unified timestamp index
    all_ts = set()
    for df in coin_dfs.values():
        all_ts.update(df["timestamp"].astype(int).tolist())
    all_ts = sorted(all_ts)
    
    coin_ts_idx = {}
    for symbol, df in coin_dfs.items():
        coin_ts_idx[symbol] = {int(row["timestamp"]): i for i, row in df.iterrows()}
    
    # Initialize engines
    if mode == "v12e":
        # Equal allocation
        per_coin = capital / len(symbols)
        engines = {}
        for symbol in symbols:
            engine = create_engine(symbol, per_coin, profile)
            engine.prepare_step(coin_dfs[symbol])
            engines[symbol] = engine
        pool = 0.0
    else:
        # V12f: need to detect initial phases first
        # Run 100 warmup steps to get initial phase, then allocate
        engines = {}
        for symbol in symbols:
            engine = create_engine(symbol, capital / len(symbols), profile)  # temp equal
            engine.prepare_step(coin_dfs[symbol])
            engines[symbol] = engine
        
        # Run warmup to detect phases
        for ts in all_ts[:200]:
            for symbol in symbols:
                if ts in coin_ts_idx[symbol]:
                    idx = coin_ts_idx[symbol][ts]
                    if idx >= 100:
                        engines[symbol].step(idx)
        
        # Get phases after warmup
        initial_phases = {s: engines[s]._lifecycle_phase.value for s in symbols}
        logger.info("[V12f] Initial phases after warmup: %s", initial_phases)
        
        # Compute weighted allocation
        allocs = compute_phase_allocations(capital, initial_phases)
        logger.info("[V12f] Phase-weighted allocations: %s", 
                    {s: f"${a:.0f}" for s, a in allocs.items()})
        
        # Recreate engines with correct capital
        engines = {}
        for symbol in symbols:
            engine = create_engine(symbol, allocs[symbol], profile)
            engine.prepare_step(coin_dfs[symbol])
            engines[symbol] = engine
        pool = capital - sum(allocs.values())
    
    # Track state
    prev_cash = {s: engines[s].get_cash() for s in symbols}
    prev_phase = {s: engines[s]._lifecycle_phase.value for s in symbols}
    prev_completed = {s: len(engines[s].completed_deals) for s in symbols}
    equity_history = []
    events = []
    warmup = 100
    tick_count = 0
    
    for ts in all_ts:
        tick_count += 1
        current_prices = {}
        
        for symbol in symbols:
            if ts not in coin_ts_idx[symbol]:
                continue
            idx = coin_ts_idx[symbol][ts]
            if idx < warmup:
                continue
            engines[symbol].step(idx)
            current_prices[symbol] = float(coin_dfs[symbol].iloc[idx]["close"])
        
        if not current_prices:
            continue
        
        # Detect events that trigger V12f reallocation
        rebalance_trigger = False
        for symbol in symbols:
            if symbol not in current_prices:
                continue
            engine = engines[symbol]
            phase = engine._lifecycle_phase.value
            
            # Phase change
            if phase != prev_phase[symbol]:
                events.append({
                    "ts": ts, "type": "phase_change", "coin": symbol,
                    "detail": f"{prev_phase[symbol]}->{phase}"
                })
                rebalance_trigger = True
                prev_phase[symbol] = phase
            
            # Deal completed (TP hit or cycle end)
            n_completed = len(engine.completed_deals)
            if n_completed > prev_completed[symbol]:
                freed = engine.get_cash() - prev_cash[symbol]
                if freed > 10:
                    events.append({
                        "ts": ts, "type": "capital_freed", "coin": symbol,
                        "detail": f"${freed:.0f} freed, phase={phase}"
                    })
                    rebalance_trigger = True
                prev_completed[symbol] = n_completed
            
            prev_cash[symbol] = engine.get_cash()
        
        # V12f rebalancing: route freed capital to best opportunity
        if mode == "v12f" and rebalance_trigger:
            # Collect excess cash from EXIT/MARKDOWN coins
            for symbol in symbols:
                if symbol not in current_prices:
                    continue
                phase = engines[symbol]._lifecycle_phase.value
                if phase in ("EXIT", "MARKDOWN"):
                    excess = engines[symbol].get_cash()
                    if excess > 50:
                        engines[symbol].set_cash(0)
                        pool += excess
            
            # Route pool to highest-priority coins
            if pool > 100:
                phases = {s: engines[s]._lifecycle_phase.value for s in symbols if s in current_prices}
                allocs = compute_phase_allocations(pool, phases)
                
                # Only deploy to SPRING/MARKUP coins
                for s, alloc in allocs.items():
                    phase = phases[s]
                    if phase in ("SPRING", "MARKUP") and alloc > 50:
                        deploy = min(alloc, pool * 0.9)  # keep some reserve
                        engines[s].set_cash(engines[s].get_cash() + deploy)
                        pool -= deploy
                        events.append({
                            "ts": ts, "type": "capital_deployed", "coin": s,
                            "detail": f"+${deploy:.0f} to {s} ({phase}), pool=${pool:.0f}"
                        })
            
            for symbol in symbols:
                prev_cash[symbol] = engines[symbol].get_cash()
        
        # Equity snapshot (daily)
        if tick_count % 24 == 0:
            total_eq = pool
            coin_eq = {}
            for s, eng in engines.items():
                p = current_prices.get(s)
                eq = eng.get_equity(p) if p else eng.get_cash()
                total_eq += eq
                coin_eq[s] = eq
            equity_history.append({
                "ts": ts,
                "date": datetime.fromtimestamp(ts/1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                "equity": round(total_eq, 2),
                "pool": round(pool, 2),
                "coins": {s: round(v, 2) for s, v in coin_eq.items()},
                "phases": {s: engines[s]._lifecycle_phase.value for s in symbols},
            })
    
    # Force close all positions
    total_equity = pool
    coin_results = {}
    for symbol, engine in engines.items():
        df = coin_dfs[symbol]
        last_price = float(df.iloc[-1]["close"])
        last_ts = str(df.iloc[-1]["timestamp"])
        
        # Force close everything
        for deal in list(engine.deals):
            engine._force_close_deal(deal, last_price, last_ts)
        if engine._markup_position_qty > 0:
            engine._close_markup_position(last_price, last_ts, "backtest_end")
        engine._force_sell_all_exit_lots(last_price, last_ts, "backtest_end")
        engine._close_exit_short(last_price, last_ts, "backtest_end")
        for entry in engine._spring_entries:
            if not entry.get("closed"):
                entry["closed"] = True
                engine.cash += entry["qty"] * last_price
        
        final_eq = engine.get_cash()
        total_equity += final_eq
        
        coin_results[symbol] = {
            "final_equity": round(final_eq, 2),
            "deals_completed": len(engine.completed_deals),
            "final_phase": engine._lifecycle_phase.value,
            "exit_phases": engine._v12_exit_phases,
            "spring_phases": engine._v12_spring_phases,
            "markdown_phases": engine._v12_markdown_phases,
            "markup_phases": engine._v12_markup_phases,
            "short_pnl": round(engine._v12_short_pnl, 2),
            "spring_pnl": round(engine._v12_spring_pnl, 2),
            "markup_pnl": round(engine._v12_markup_pnl, 2),
        }
    
    return_pct = (total_equity - capital) / capital * 100
    
    return {
        "mode": mode,
        "total_equity": round(total_equity, 2),
        "return_pct": round(return_pct, 2),
        "pool": round(pool, 2),
        "coin_results": coin_results,
        "events": events,
        "equity_history": equity_history,
    }


def main():
    symbols = ["SOL/USDT", "ETH/USDT", "ZEC/USDT"]
    capital = 10000
    profile = "medium"
    start_date = "2024-10-01"
    end_date = "2026-02-22"
    
    logger.info("=" * 60)
    logger.info("V12e vs V12f COMPARISON BACKTEST")
    logger.info("Symbols: %s", symbols)
    logger.info("Capital: $%d | Profile: %s", capital, profile)
    logger.info("Period: %s -> %s", start_date, end_date)
    logger.info("Shorts: ENABLED")
    logger.info("=" * 60)
    
    # Load data
    db = CandleDB()
    fg_data = load_historical_fear_greed()
    
    start_ms = int(datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    
    coin_dfs = {}
    for symbol in symbols:
        df = db.get_candles(symbol, "1h", start_ms, end_ms)
        if df.empty:
            # Fallback: try CSV
            token = symbol.split("/")[0]
            csv_path = Path(__file__).resolve().parent / "data" / "rotation_test" / f"{token}_USDT_1h.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                df = df[(df["timestamp"] >= start_ms) & (df["timestamp"] <= end_ms)].reset_index(drop=True)
        if df.empty:
            raise ValueError(f"No data for {symbol}")
        df["fear_greed"] = df["timestamp"].apply(lambda ts: get_fg(fg_data, int(ts)))
        coin_dfs[symbol] = df.reset_index(drop=True)
        logger.info("Loaded %d candles for %s", len(df), symbol)
    
    # Run V12e (equal allocation)
    logger.info("\n" + "=" * 40)
    logger.info("Running V12e (equal allocation)...")
    t0 = time.time()
    v12e = run_backtest(symbols, capital, profile, coin_dfs, fg_data, mode="v12e")
    t1 = time.time()
    logger.info("V12e done in %.1fs", t1 - t0)
    
    # Run V12f (phase-weighted)
    logger.info("\n" + "=" * 40)
    logger.info("Running V12f (phase-weighted allocation)...")
    t0 = time.time()
    v12f = run_backtest(symbols, capital, profile, coin_dfs, fg_data, mode="v12f")
    t1 = time.time()
    logger.info("V12f done in %.1fs", t1 - t0)
    
    # Save results
    results = {"v12e": v12e, "v12f": v12f}
    out_path = RESULTS_DIR / f"comparison_{profile}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    # Print comparison
    print()
    print("=" * 70)
    print(f"V12e vs V12f COMPARISON — {profile} profile, ${capital:,}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Coins: {', '.join(symbols)}")
    print(f"Shorts: ENABLED")
    print("=" * 70)
    print()
    print(f"{'':20s}  {'V12e (equal)':>15s}  {'V12f (weighted)':>15s}  {'Delta':>10s}")
    print("-" * 65)
    print(f"{'Total Return':20s}  {v12e['return_pct']:>14.1f}%  {v12f['return_pct']:>14.1f}%  {v12f['return_pct']-v12e['return_pct']:>+9.1f}%")
    print(f"{'Final Equity':20s}  ${v12e['total_equity']:>13,.0f}  ${v12f['total_equity']:>13,.0f}  ${v12f['total_equity']-v12e['total_equity']:>+8,.0f}")
    print()
    
    for sym in symbols:
        e_cr = v12e["coin_results"][sym]
        f_cr = v12f["coin_results"][sym]
        print(f"  {sym}:")
        print(f"    V12e: ${e_cr['final_equity']:>8,.0f} | Deals: {e_cr['deals_completed']:>3d} | Short PnL: ${e_cr['short_pnl']:>7,.0f} | Phase: {e_cr['final_phase']}")
        print(f"    V12f: ${f_cr['final_equity']:>8,.0f} | Deals: {f_cr['deals_completed']:>3d} | Short PnL: ${f_cr['short_pnl']:>7,.0f} | Phase: {f_cr['final_phase']}")
        print(f"    Exits: {e_cr['exit_phases']}/{f_cr['exit_phases']} | Springs: {e_cr['spring_phases']}/{f_cr['spring_phases']} | Markdowns: {e_cr['markdown_phases']}/{f_cr['markdown_phases']} | Markups: {e_cr['markup_phases']}/{f_cr['markup_phases']}")
        print()
    
    print(f"V12f events: {len(v12f['events'])} (phase changes + capital routing)")
    print("=" * 70)
    
    logger.info("Results saved to %s", out_path)


if __name__ == "__main__":
    main()
