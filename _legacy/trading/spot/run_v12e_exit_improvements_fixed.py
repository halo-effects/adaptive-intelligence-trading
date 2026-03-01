#!/usr/bin/env python3
"""V12e Exit Improvements Runner — Price Discovery Mode + CFGI Hard Gate

Runs V12e backtests with two exit improvements:
1. Price discovery mode (already implemented)
2. CFGI >= 75 hard gate on EXIT transitions

Tests all 9 combinations: 3 coins × 3 profiles
"""
import sys
import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

# Configuration
PYTHON = r"C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe"
WORKSPACE = Path(__file__).resolve().parent

COINS = {
    "btc": {"symbol": "BTC/USDT", "data": "binance_BTC_1h.csv", "ath": 109000},
    "eth": {"symbol": "ETH/USDT", "data": "binance_ETH_1h.csv", "ath": 4878},
    "sol": {"symbol": "SOL/USDT", "data": "binance_SOL_1h.csv", "ath": 260}
}

PROFILES = ["low", "medium", "high"]

RESULTS_DIR = WORKSPACE / "backtest_results" / "v12e_exit_improvements"

def main():
    print(f"""
{'='*80}
V12e EXIT IMPROVEMENTS BACKTEST SUITE
Price Discovery Mode + CFGI >= 75 Hard Gate
{'='*80}

Running 9 backtests: 3 coins × 3 profiles
Output: {RESULTS_DIR}
""")
    
    # Create results directory
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # First, create our modified backtest engine with CFGI hard gate
    create_modified_engine()
    
    # Store all results for comparison table
    all_results = {}
    
    # Run all combinations
    for coin_key, coin_config in COINS.items():
        for profile in PROFILES:
            run_key = f"{coin_key}_{profile}"
            print(f"\n{'-'*60}")
            print(f"Running: {coin_key.upper()} {profile}")
            print(f"{'-'*60}")
            
            result = run_backtest(coin_key, coin_config, profile)
            all_results[run_key] = result
    
    # Generate comparison report
    generate_results_report(all_results)
    
    print(f"\n{'='*80}")
    print("BACKTEST SUITE COMPLETE")
    print(f"Results saved to: {RESULTS_DIR}")
    print(f"{'='*80}")

def create_modified_engine():
    """Create modified backtest engine with CFGI >= 75 hard gate"""
    source_engine = WORKSPACE / "backtest_engine_v12.py"
    modified_engine = WORKSPACE / "backtest_engine_v12e_exit_improved.py"
    
    # Read the original engine
    engine_code = source_engine.read_text(encoding='utf-8')
    
    # Add CFGI hard gate method to DailyScorerConductor class
    cfgi_gate_method = '''
    
    def cfgi_allows_exit(self, ts_1h_ms: int) -> bool:
        """Check if CFGI >= 75 allows EXIT transition.
        
        Returns True if CFGI >= 75 or no CFGI data available.
        Returns False if CFGI < 75 (veto the exit).
        """
        if not self._cfgi_history:
            return True  # No CFGI data available, don't block
            
        # Convert timestamp to date string for CFGI lookup
        dt = pd.Timestamp(ts_1h_ms, unit='ms', tz='UTC').normalize()
        date_str = dt.strftime("%Y-%m-%d")
        
        if date_str not in self._cfgi_history:
            return True  # No CFGI data for this date, don't block
            
        cfgi_score = self._cfgi_history[date_str]
        
        if cfgi_score < 75:
            logger.info(f"  🚫 CFGI HARD GATE: EXIT vetoed — CFGI={cfgi_score:.0f} < 75")
            return False
            
        return True
'''
    
    # Insert the method into DailyScorerConductor class
    class_insert_point = "    def weekly_confirms_exit_price_discovery(self, df_1h: pd.DataFrame, current_price: float) -> bool:"
    engine_code = engine_code.replace(class_insert_point, cfgi_gate_method + "\n    def weekly_confirms_exit_price_discovery(self, df_1h: pd.DataFrame, current_price: float) -> bool:")
    
    # Now I need to add the CFGI gate checks to all the exit transitions
    # This is complex because we need to modify multiple specific locations
    
    # Split into lines for easier manipulation
    lines = engine_code.split('\n')
    
    # Find and modify all instances of self._transition_to_exit calls
    for i, line in enumerate(lines):
        if 'self._transition_to_exit(price, ts, ts_ms, daily_score)' in line and i > 2:
            # Check the context to see if this needs CFGI gate
            context = '\n'.join(lines[max(0, i-10):i+3])
            
            # If it's after a price discovery or weekly confirmation check, add CFGI gate
            if ('price_discovery' in context or 'weekly_confirms' in context or 
                'should_exit' in context):
                # Get the indentation of the current line
                indent = len(line) - len(line.lstrip())
                
                # Replace with CFGI-gated version
                lines[i] = ' ' * indent + 'if self._conductor.cfgi_allows_exit(ts_ms):'
                lines.insert(i+1, ' ' * (indent + 4) + 'self._transition_to_exit(price, ts, ts_ms, daily_score)')
                
    # Join back together
    engine_code = '\n'.join(lines)
    
    # Write the modified engine
    modified_engine.write_text(engine_code, encoding='utf-8')
    print(f"Created modified engine: {modified_engine}")

def run_backtest(coin_key: str, coin_config: dict, profile: str) -> dict:
    """Run a single backtest configuration"""
    
    # Create a runner script for this specific combination
    runner_script = create_backtest_runner(coin_key, coin_config, profile)
    
    try:
        # Run the backtest
        result = subprocess.run(
            [PYTHON, str(runner_script)],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        # Check for results
        result_file = RESULTS_DIR / f"{coin_key}_{profile}_improved.json"
        
        if result.returncode == 0 and result_file.exists():
            # Load and return results
            data = json.loads(result_file.read_text())
            print(f"✅ {coin_key.upper()} {profile}: ROI={data.get('total_pnl_pct', 0):.1f}% | DD={data.get('max_drawdown_pct', 0):.1f}%")
            return data
        else:
            print(f"❌ {coin_key.upper()} {profile}: FAILED")
            print(f"Return code: {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr[:500]}")
            return {"error": "Backtest failed", "total_pnl_pct": 0, "max_drawdown_pct": 0}
            
    except subprocess.TimeoutExpired:
        print(f"⏱️ {coin_key.upper()} {profile}: TIMEOUT")
        return {"error": "Timeout", "total_pnl_pct": 0, "max_drawdown_pct": 0}
    except Exception as e:
        print(f"💥 {coin_key.upper()} {profile}: ERROR - {e}")
        return {"error": str(e), "total_pnl_pct": 0, "max_drawdown_pct": 0}

def create_backtest_runner(coin_key: str, coin_config: dict, profile: str) -> Path:
    """Create a individual backtest runner script"""
    runner_path = RESULTS_DIR / f"run_{coin_key}_{profile}.py"
    
    runner_code = f'''#!/usr/bin/env python3
"""Individual V12e Exit Improvements Backtest: {coin_key.upper()} {profile}"""

import sys
import json
from pathlib import Path

# Add the trading module to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backtest_engine_v12e_exit_improved import SpotBacktestEngineV12
import pandas as pd

def main():
    # Configuration
    symbol = "{coin_config["symbol"]}"
    known_ath = {coin_config["ath"]}
    data_file = Path(__file__).resolve().parent / "data" / "{coin_config["data"]}"
    
    # Load price data
    if not data_file.exists():
        print(f"Data file not found: {{data_file}}")
        return 1
        
    df = pd.read_csv(data_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    print(f"Loaded {{len(df):,}} candles from {{data_file.name}}")
    print(f"Period: {{df.index[0]}} to {{df.index[-1]}}")
    
    # Profile parameters - use existing V12e parameters
    profile_params = get_profile_params("{profile}")
    
    # Fixed parameters for exit improvements test
    params = {{
        "initial_capital": 10000,
        "compound_gains": True,
        "compound_threshold_usd": 500,
        "v12_slippage_pct": 0.0005,  # 0.05% slippage
        "exchange": "aster",  # 0% maker, 0.04% taker
        "symbol": symbol,
        "timeframe": "1h",
        **profile_params
    }}
    
    # Create engine with known ATH for price discovery mode
    engine = SpotBacktestEngineV12(**params)
    engine._conductor._known_historical_ath = known_ath
    engine._conductor._symbol = symbol
    
    print(f"\\nRunning V12e Exit Improvements: {{symbol}} {{profile.upper()}}")
    print(f"Parameters: {{params}}")
    print(f"Known ATH: ${{known_ath:,.0f}}")
    
    # Run backtest
    result = engine.run(df)
    
    # Save results
    output_file = Path(__file__).resolve().parent / "{coin_key}_{profile}_improved.json"
    
    result_data = {{
        "symbol": symbol,
        "profile": "{profile}",
        "known_ath": known_ath,
        "period_start": df.index[0].isoformat(),
        "period_end": df.index[-1].isoformat(),
        "total_pnl_pct": result.total_pnl_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "sharpe_ratio": result.sharpe_ratio,
        "total_trades": result.total_trades,
        "win_rate": result.win_rate_pct,
        "avg_trade_pct": result.avg_trade_pct,
        "exit_phases": len([t for t in result.trade_log if "EXIT" in str(t.reason)]),
        "short_pnl": sum(t.pnl for t in result.trade_log if "short" in str(t.reason).lower()),
        "parameters": params
    }}
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(result_data, f, indent=2)
    
    print(f"\\nResults saved to: {{output_file}}")
    print(f"ROI: {{result.total_pnl_pct:.1f}}%")
    print(f"Max DD: {{result.max_drawdown_pct:.1f}}%")
    print(f"Sharpe: {{result.sharpe_ratio:.2f}}")
    
    return 0

def get_profile_params(profile: str) -> dict:
    """Get profile-specific parameters (matching existing V12e)"""
    if profile == "low":
        return {{
            "dist_exit_threshold": 50,
            "spring_deploy_tiers": [25, 50, 75],  # % of capital per tier
            "spring_score_thresholds": [60, 75, 90],
            "dist_threshold_floor": 30,
            "v12_weekly_dist_veto": False,
            "exit_mcap_ath_pct": 0.25
        }}
    elif profile == "medium":
        return {{
            "dist_exit_threshold": 45,
            "spring_deploy_tiers": [30, 60, 80],
            "spring_score_thresholds": [65, 80, 90],
            "dist_threshold_floor": 25,
            "v12_weekly_dist_veto": False,
            "exit_mcap_ath_pct": 0.30
        }}
    else:  # high
        return {{
            "dist_exit_threshold": 40,
            "spring_deploy_tiers": [35, 65, 85],
            "spring_score_thresholds": [70, 85, 95],
            "dist_threshold_floor": 20,
            "v12_weekly_dist_veto": False,
            "exit_mcap_ath_pct": 0.35
        }}

if __name__ == "__main__":
    sys.exit(main())
'''
    
    runner_path.write_text(runner_code, encoding='utf-8')
    return runner_path

def generate_results_report(all_results: dict):
    """Generate comprehensive results report"""
    
    # Load baseline results for comparison (if available)
    baseline_results = load_baseline_results()
    
    # Generate markdown report
    report_content = f"""# V12e Exit Improvements Backtest Results
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Configuration
- **Price Discovery Mode**: ✅ Enabled (requires weekly confirmation when price > KNOWN_ATH)
- **CFGI Hard Gate**: ✅ Enabled (EXIT requires CFGI >= 75, vetoes if CFGI < 75)
- **Capital**: $10,000
- **Compounding**: True
- **Slippage**: 0.05% (0.0005)
- **Exchange**: Aster (0% maker / 0.04% taker fees)
- **Period**: Oct 2020 → Feb 2026 (all available 1h data)

## Known ATH Values
- **BTC**: $109,000
- **ETH**: $4,878  
- **SOL**: $260

## Results Summary

| Coin | Profile | Improved ROI | Improved DD | Improved Sharpe | Exit Phases | Short PnL | Baseline ROI* | ROI Change |
|------|---------|-------------|-------------|----------------|-------------|-----------|---------------|------------|
"""
    
    # Add results rows
    for coin in ["btc", "eth", "sol"]:
        for profile in ["low", "medium", "high"]:
            key = f"{coin}_{profile}"
            
            if key in all_results:
                r = all_results[key]
                baseline_roi = get_baseline_roi(baseline_results, coin, profile)
                roi_change = ""
                if baseline_roi is not None:
                    change = r.get("total_pnl_pct", 0) - baseline_roi
                    roi_change = f"{change:+.1f}%"
                
                report_content += f"| {coin.upper()} | {profile} | {r.get('total_pnl_pct', 0):.1f}% | {r.get('max_drawdown_pct', 0):.1f}% | {r.get('sharpe_ratio', 0):.2f} | {r.get('exit_phases', 0)} | ${r.get('short_pnl', 0):,.0f} | {baseline_roi or 'N/A'} | {roi_change} |\\n"
            else:
                report_content += f"| {coin.upper()} | {profile} | ERROR | ERROR | ERROR | - | - | - | - |\\n"
    
    report_content += f"""
*Baseline ROI from V12e results without fees/slippage (noted in requirements)

## Impact Analysis

### Price Discovery Mode Impact
When price > KNOWN_ATH (price discovery mode):
- ATH proximity gate becomes meaningless (price IS the ATH)  
- Weekly bearish structure confirmation required before EXIT
- More conservative exits during genuine price discovery periods

### CFGI Hard Gate Impact  
EXIT transitions require CFGI >= 75:
- Prevents exits during fear/panic periods (CFGI < 75)
- Only allows exits when greed is elevated
- Falls back gracefully when CFGI data unavailable

## Detailed Results

"""
    
    # Add detailed results for each run
    for coin in ["btc", "eth", "sol"]:
        report_content += f"### {coin.upper()} Results\\n\\n"
        
        for profile in ["low", "medium", "high"]:
            key = f"{coin}_{profile}"
            if key in all_results:
                r = all_results[key]
                if "error" not in r:
                    report_content += f"""**{profile.upper()} Profile**
- ROI: {r.get('total_pnl_pct', 0):.1f}%
- Max Drawdown: {r.get('max_drawdown_pct', 0):.1f}%  
- Sharpe Ratio: {r.get('sharpe_ratio', 0):.2f}
- Total Trades: {r.get('total_trades', 0)}
- Win Rate: {r.get('win_rate', 0):.1f}%
- Exit Phases: {r.get('exit_phases', 0)}
- Short P&L: ${r.get('short_pnl', 0):,.0f}

"""
                else:
                    report_content += f"**{profile.upper()} Profile**: ❌ {r.get('error', 'Unknown error')}\\n\\n"
        
        report_content += "\\n"
    
    # Save report
    report_file = RESULTS_DIR / "RESULTS.md"
    report_file.write_text(report_content, encoding='utf-8')
    
    # Also save raw results
    raw_results_file = RESULTS_DIR / "raw_results.json"
    with open(raw_results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\\nResults report saved to: {report_file}")

def load_baseline_results() -> dict:
    """Load baseline V12e results for comparison"""
    # Look for existing V12e results
    baseline_dir = WORKSPACE / "backtest_results" / "v12_lifecycle"
    baseline_results = {}
    
    for coin in ["btc", "eth", "sol"]:
        for profile in ["low", "medium", "high"]:
            baseline_file = baseline_dir / f"{coin}_1h_v12e_{profile}.json"
            if baseline_file.exists():
                try:
                    data = json.loads(baseline_file.read_text())
                    baseline_results[f"{coin}_{profile}"] = data
                except Exception:
                    pass
    
    return baseline_results

def get_baseline_roi(baseline_results: dict, coin: str, profile: str) -> float:
    """Get baseline ROI for comparison"""
    key = f"{coin}_{profile}"
    if key in baseline_results:
        return baseline_results[key].get("total_pnl_pct")
    
    # Fallback to hardcoded values from requirements
    baseline_values = {
        "eth_low": 181.3, "eth_medium": 237.3, "eth_high": 314.2,
        "btc_low": 233.0, "btc_medium": 185.0, "btc_high": 463.0,
        "sol_low": 132.1, "sol_medium": 191.9, "sol_high": 184.4
    }
    
    return baseline_values.get(key)

if __name__ == "__main__":
    main()