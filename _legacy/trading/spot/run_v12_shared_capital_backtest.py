#!/usr/bin/env python3
"""V12 Shared-Capital Multi-Coin Backtest — True tick-by-tick capital pool.

Unlike the V12f rotation backtest overlay, this runs all coins simultaneously
on every candle tick with a SHARED capital pool. Capital flows naturally:

  - Each coin's engine gets cash from the shared pool
  - When TPs hit (deals close), freed cash returns to pool
  - Pool capital routes to coins in MARKUP/SPRING phases first
  - DCA coins get remaining capital
  - MARKDOWN/EXIT coins get no new capital (existing positions ride out)

Usage:
    python -u trading/spot/run_v12_shared_capital_backtest.py \
        --symbols SOL/USDT ETH/USDT ZEC/USDT \
        --start 2024-08-21 --end 2026-02-22 \
        --profile medium --capital 10000
"""
import sys
import json
import logging
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
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

RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v12_shared_capital"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Known ATH prices
KNOWN_ATH = {
    "ETH/USDC": 4878.0, "ETH/USDT": 4878.0,
    "SOL/USDC": 260.0, "SOL/USDT": 260.0,
    "BTC/USDC": 109588.0, "BTC/USDT": 109588.0,
    "ZEC/USDT": 724.0,
    "XRP/USDT": 3.40, "DOGE/USDT": 0.74,
    "BNB/USDT": 793.0, "HYPE/USDC": 35.0,
    "ASTER/USDT": 1.50,
}


@dataclass
class RotationEvent:
    timestamp_ms: int
    timestamp: str
    event: str          # "capital_freed", "capital_deployed", "phase_change"
    coin: str
    phase: str
    amount: float       # dollars moved
    pool_after: float   # pool balance after event
    detail: str = ""


class SharedCapitalBacktest:
    """Tick-by-tick multi-coin backtest with shared capital pool."""

    def __init__(self, symbols: List[str], capital: float, profile: str,
                 aggressiveness: str = "balanced"):
        self.symbols = symbols
        self.initial_capital = capital
        self.profile = profile
        self.aggressiveness = aggressiveness
        self.reserve_pct = 0.10

        # The shared pool — all free cash lives here
        self.pool = capital
        
        # Track how much each coin's engine "owns" from the pool
        # This is the cash the engine has + its deployed capital
        self.coin_cash: Dict[str, float] = {}
        
        # Engines
        self.engines: Dict[str, SpotBacktestEngineV12] = {}
        
        # Tracking
        self.rotation_events: List[RotationEvent] = []
        self.equity_history: List[dict] = []
        self.phase_history: List[dict] = []
        
    def _create_engine(self, symbol: str, capital: float) -> SpotBacktestEngineV12:
        """Create a V12 engine for a coin with given starting capital."""
        params = {
            "symbol": symbol,
            "capital": capital,
            "timeframe": "1h",
            "profile": self.profile,
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
            # Shorts DISABLED — spot only, no futures
            "v12_short_enabled": False,
            # Spring
            "v12_spring_tier1_discount": 25.0,
            "v12_spring_tier2_discount": 35.0,
            "v12_spring_tier3_discount": 45.0,
            "v12_spring_tier1_deploy": 0.60,
            "v12_spring_tier2_deploy": 0.80,
            "v12_spring_tier3_deploy": 0.90,
            "v12_spring_tp_pct": 15.0,
            # Markup
            "v12_markup_deploy_pct": {"low": 0.50, "medium": 0.70, "high": 0.90}.get(self.profile, 0.70),
            "v12_markup_trail_pct": 10.0,
            "v12_markup_trail_tighten_score": 30.0,
            "v12_markup_trail_tight_pct": 5.0,
            "v12_markup_pullback_pct": 5.0,
            "v12_markup_pullback_deploy_pct": 0.15,
            "v12_markup_max_adds": 2,
        }
        
        # Adjust spring discounts by aggressiveness
        if self.aggressiveness == "balanced":
            for k in ("v12_spring_tier1_discount", "v12_spring_tier2_discount", "v12_spring_tier3_discount"):
                params[k] *= 0.85
        elif self.aggressiveness == "aggressive":
            for k in ("v12_spring_tier1_discount", "v12_spring_tier2_discount", "v12_spring_tier3_discount"):
                params[k] *= 0.70
        
        return SpotBacktestEngineV12(**params)

    def run(self, start_date: str, end_date: str) -> dict:
        """Run the shared-capital backtest."""
        db = CandleDB()
        fg_data = load_historical_fear_greed()
        
        start_ms = int(datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
        end_ms = int(datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
        
        # Load candle data for all coins
        coin_dfs: Dict[str, pd.DataFrame] = {}
        for symbol in self.symbols:
            df = db.get_candles(symbol, "1h", start_ms, end_ms)
            if df.empty:
                raise ValueError(f"No candle data for {symbol}")
            # Add fear/greed
            df["fear_greed"] = df["timestamp"].apply(
                lambda ts: self._get_fg(fg_data, int(ts))
            )
            coin_dfs[symbol] = df.reset_index(drop=True)
            logger.info("Loaded %d candles for %s", len(df), symbol)
        
        logger.info("Loading F&G data...")
        logger.info("F&G loaded: %d entries", len(fg_data))
        
        # Build unified timestamp index (union of all coins' timestamps)
        all_ts = set()
        for df in coin_dfs.values():
            all_ts.update(df["timestamp"].astype(int).tolist())
        all_ts = sorted(all_ts)
        logger.info("Unified timeline: %d timestamps", len(all_ts))
        
        # Build timestamp→index lookup for each coin
        coin_ts_idx: Dict[str, Dict[int, int]] = {}
        for symbol, df in coin_dfs.items():
            coin_ts_idx[symbol] = {int(row["timestamp"]): i for i, row in df.iterrows()}
        
        # ── Initialize engines ──
        # Start with equal allocation
        initial_per_coin = self.initial_capital / len(self.symbols)
        for symbol in self.symbols:
            logger.info("Creating engine for %s...", symbol)
            engine = self._create_engine(symbol, initial_per_coin)
            logger.info("Calling prepare_step for %s (%d candles)...", symbol, len(coin_dfs[symbol]))
            engine.prepare_step(coin_dfs[symbol])
            logger.info("prepare_step done for %s", symbol)
            self.engines[symbol] = engine
            self.coin_cash[symbol] = initial_per_coin
        
        self.pool = 0.0  # All capital is distributed to engines initially
        
        # Track previous cash per engine to detect TP hits
        prev_cash: Dict[str, float] = {s: engine.get_cash() for s, engine in self.engines.items()}
        prev_phase: Dict[str, str] = {s: "DCA" for s in self.symbols}
        
        # ── Main loop: tick through every timestamp ──
        warmup = 100  # Skip first 100 candles (indicator warmup)
        tick_count = 0
        
        for ts in all_ts:
            tick_count += 1
            
            # Step each engine that has data at this timestamp
            current_prices: Dict[str, float] = {}
            for symbol in self.symbols:
                if ts not in coin_ts_idx[symbol]:
                    continue
                idx = coin_ts_idx[symbol][ts]
                if idx < warmup:
                    continue
                
                engine = self.engines[symbol]
                engine.step(idx)
                current_prices[symbol] = float(coin_dfs[symbol].iloc[idx]["close"])
            
            if not current_prices:
                continue
            
            # ── Detect phase changes → trigger capital rebalancing ──
            rebalance_needed = False
            for symbol, engine in self.engines.items():
                if symbol not in current_prices:
                    continue
                phase = engine._lifecycle_phase.value
                if phase != prev_phase[symbol]:
                    self.rotation_events.append(RotationEvent(
                        timestamp_ms=ts,
                        timestamp=datetime.fromtimestamp(ts/1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
                        event="phase_change",
                        coin=symbol,
                        phase=phase,
                        amount=0,
                        pool_after=self.pool,
                        detail=f"{prev_phase[symbol]} -> {phase}",
                    ))
                    rebalance_needed = True
                    prev_phase[symbol] = phase
            
            # ── Detect TP hits (cash increased meaningfully) ──
            for symbol, engine in self.engines.items():
                if symbol not in current_prices:
                    continue
                current_cash = engine.get_cash()
                cash_delta = current_cash - prev_cash[symbol]
                
                # Only capture large cash increases as "freed capital"
                # Small fluctuations are normal DCA operation
                if cash_delta > 50:
                    rebalance_needed = True
                
                prev_cash[symbol] = current_cash
            
            # ── Rebalance only on meaningful events ──
            if rebalance_needed:
                # Step 1: Collect idle cash from MARKDOWN/EXIT coins
                for symbol, engine in self.engines.items():
                    if symbol not in current_prices:
                        continue
                    phase = engine._lifecycle_phase.value
                    if phase in ("MARKDOWN", "EXIT"):
                        idle_cash = engine.get_cash()
                        if idle_cash > 50:
                            engine.set_cash(0)
                            self.pool += idle_cash
                            self.rotation_events.append(RotationEvent(
                                timestamp_ms=ts,
                                timestamp=datetime.fromtimestamp(ts/1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
                                event="capital_freed",
                                coin=symbol,
                                phase=phase,
                                amount=idle_cash,
                                pool_after=self.pool,
                                detail=f"Idle cash from {symbol} ({phase})",
                            ))
                
                # Step 2: Collect excess cash from DCA coins that have more than
                # their fair share (freed from TPs). Don't starve active grids though.
                # A DCA coin keeps enough for its next SO; excess goes to pool.
                for symbol, engine in self.engines.items():
                    if symbol not in current_prices:
                        continue
                    phase = engine._lifecycle_phase.value
                    if phase == "DCA":
                        current_cash = engine.get_cash()
                        deployed = engine.get_deployed()
                        # Keep enough for the DCA grid (deployed * 2 as buffer)
                        # but if cash far exceeds that, skim the excess
                        fair_share = self.initial_capital / len(self.symbols)
                        excess = current_cash - fair_share
                        if excess > 100:
                            skim = excess * 0.5  # Take half the excess, leave buffer
                            engine.set_cash(current_cash - skim)
                            self.pool += skim
                
                # Step 3: Deploy pool to opportunity coins
                reserve = self.initial_capital * self.reserve_pct
                available = max(0, self.pool - reserve)
                
                if available > 100:
                    # Priority: MARKUP > SPRING > DCA (only if underfunded)
                    markup_coins = [s for s in self.symbols if s in current_prices 
                                   and self.engines[s]._lifecycle_phase == LifecyclePhase.MARKUP]
                    spring_coins = [s for s in self.symbols if s in current_prices 
                                   and self.engines[s]._lifecycle_phase == LifecyclePhase.SPRING]
                    
                    targets = markup_coins if markup_coins else spring_coins
                    
                    if targets:
                        per_coin = available / len(targets)
                        for symbol in targets:
                            engine = self.engines[symbol]
                            engine.set_cash(engine.get_cash() + per_coin)
                            self.pool -= per_coin
                            
                            self.rotation_events.append(RotationEvent(
                                timestamp_ms=ts,
                                timestamp=datetime.fromtimestamp(ts/1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
                                event="capital_deployed",
                                coin=symbol,
                                phase=engine._lifecycle_phase.value,
                                amount=per_coin,
                                pool_after=self.pool,
                                detail=f"Pool -> {symbol} ({engine._lifecycle_phase.value})",
                            ))
                    elif not markup_coins and not spring_coins:
                        # No opportunity coins — distribute back to DCA coins equally
                        dca_coins = [s for s in self.symbols if s in current_prices 
                                    and self.engines[s]._lifecycle_phase == LifecyclePhase.DCA]
                        if dca_coins:
                            per_coin = available / len(dca_coins)
                            for symbol in dca_coins:
                                engine = self.engines[symbol]
                                engine.set_cash(engine.get_cash() + per_coin)
                                self.pool -= per_coin
                
                # Update prev_cash after rebalance
                for symbol, engine in self.engines.items():
                    prev_cash[symbol] = engine.get_cash()
            
            # ── Record equity snapshot (every 24 candles = daily) ──
            if tick_count % 24 == 0:
                total_equity = self.pool
                coin_equities = {}
                for symbol, engine in self.engines.items():
                    price = current_prices.get(symbol)
                    if price:
                        eq = engine.get_equity(price)
                    else:
                        eq = engine.get_cash()
                    total_equity += eq
                    coin_equities[symbol] = eq
                
                self.equity_history.append({
                    "timestamp_ms": ts,
                    "timestamp": datetime.fromtimestamp(ts/1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                    "total_equity": round(total_equity, 2),
                    "pool": round(self.pool, 2),
                    "coins": {s: round(v, 2) for s, v in coin_equities.items()},
                    "phases": {s: self.engines[s]._lifecycle_phase.value for s in self.symbols},
                })
        
        # ── Force close all positions at end ──
        logger.info("Backtest complete. Closing all positions...")
        total_equity = self.pool
        coin_results = {}
        
        for symbol, engine in self.engines.items():
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
                    pnl = (last_price - entry["price"]) * entry["qty"]
                    entry["closed"] = True
                    engine.cash += entry["qty"] * last_price
            
            final_equity = engine.get_cash()
            total_equity += final_equity
            
            coin_results[symbol] = {
                "final_equity": round(final_equity, 2),
                "initial_allocation": round(self.initial_capital / len(self.symbols), 2),
                "deals_completed": len(engine.completed_deals),
                "lifecycle_phase_final": engine._lifecycle_phase.value,
                "exit_phases": engine._v12_exit_phases,
                "spring_phases": engine._v12_spring_phases,
                "markdown_phases": engine._v12_markdown_phases,
                "markup_phases": engine._v12_markup_phases,
                "short_pnl": round(engine._v12_short_pnl, 2),
                "spring_pnl": round(engine._v12_spring_pnl, 2),
                "markup_pnl": round(engine._v12_markup_pnl, 2),
            }
            
            logger.info("  %s: $%.0f -> $%.0f (phase: %s, deals: %d)", 
                        symbol, self.initial_capital / len(self.symbols),
                        final_equity, engine._lifecycle_phase.value,
                        coin_results[symbol]["deals_completed"])
        
        total_return_pct = (total_equity - self.initial_capital) / self.initial_capital * 100
        
        # Count rotation events by type
        rotation_summary = {}
        for evt in self.rotation_events:
            rotation_summary[evt.event] = rotation_summary.get(evt.event, 0) + 1
        
        result = {
            "config": {
                "symbols": self.symbols,
                "initial_capital": self.initial_capital,
                "profile": self.profile,
                "aggressiveness": self.aggressiveness,
                "start_date": start_date,
                "end_date": end_date,
            },
            "summary": {
                "total_equity": round(total_equity, 2),
                "total_return_pct": round(total_return_pct, 2),
                "pool_remaining": round(self.pool, 2),
                "rotation_events_count": len(self.rotation_events),
                "rotation_summary": rotation_summary,
            },
            "coin_results": coin_results,
            "rotation_events": [asdict(e) for e in self.rotation_events],
            "equity_history": self.equity_history,
        }
        
        return result
    
    def _get_fg(self, fg_data: dict, ts_ms: int) -> int:
        """Get fear/greed value for a timestamp."""
        if not fg_data:
            return 50
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        date_str = dt.strftime("%Y-%m-%d")
        return fg_data.get(date_str, 50)


def main():
    parser = argparse.ArgumentParser(description="V12 Shared-Capital Multi-Coin Backtest")
    parser.add_argument("--symbols", nargs="+", required=True, help="Coin symbols (e.g. SOL/USDT ETH/USDT ZEC/USDT)")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--capital", type=float, default=10000, help="Total shared capital")
    parser.add_argument("--profile", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--aggressiveness", default="balanced", choices=["conservative", "balanced", "aggressive"])
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("V12 SHARED-CAPITAL BACKTEST")
    logger.info("Symbols: %s", args.symbols)
    logger.info("Capital: $%.0f | Profile: %s | Aggressiveness: %s", args.capital, args.profile, args.aggressiveness)
    logger.info("Period: %s -> %s", args.start, args.end)
    logger.info("=" * 60)
    
    bt = SharedCapitalBacktest(
        symbols=args.symbols,
        capital=args.capital,
        profile=args.profile,
        aggressiveness=args.aggressiveness,
    )
    
    t0 = time.time()
    result = bt.run(args.start, args.end)
    elapsed = time.time() - t0
    
    # Save results
    name = f"{args.aggressiveness}_{args.profile}"
    out_path = RESULTS_DIR / f"{name}.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    # Print summary
    s = result["summary"]
    print()
    print("=" * 60)
    print(f"RESULT: {name}")
    print(f"  Total Return: {s['total_return_pct']:.1f}%")
    print(f"  Final Equity: ${s['total_equity']:,.0f} (from ${args.capital:,.0f})")
    print(f"  Pool Remaining: ${s['pool_remaining']:,.0f}")
    print(f"  Rotation Events: {s['rotation_events_count']}")
    print(f"  Time: {elapsed:.1f}s")
    print()
    for sym, cr in result["coin_results"].items():
        print(f"  {sym}: ${cr['final_equity']:,.0f} | Deals: {cr['deals_completed']} | Phase: {cr['lifecycle_phase_final']}")
        print(f"    Exit: {cr['exit_phases']} | Spring: {cr['spring_phases']} | Markdown: {cr['markdown_phases']} | Markup: {cr['markup_phases']}")
    print("=" * 60)
    
    logger.info("Results saved to %s", out_path)


if __name__ == "__main__":
    main()
