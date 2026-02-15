# 🎰 Martingale DCA Crypto Backtester

Research-only backtesting system for Martingale/DCA trading strategies on crypto markets.

**⚠️ NO live trading. NO API keys. NO real money. Research only.**

## Quick Start

```powershell
cd C:\Users\Never\.openclaw\workspace
C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe -m trading.backtest_runner
```

## Architecture

| File | Purpose |
|------|---------|
| `config.py` | Strategy parameters dataclass |
| `data_fetcher.py` | OHLCV data from Binance (ccxt), CSV caching |
| `indicators.py` | ADX, ATR, RSI, BBW, Hurst, EMA, Volume SMA |
| `regime_detector.py` | Classifies market as CHOPPY/RANGING/MILD_TREND/TRENDING/EXTREME |
| `martingale_engine.py` | Core backtester — simulates deals with base + safety orders |
| `coin_screener.py` | Ranks coins by Martingale friendliness |
| `optimizer.py` | Grid search over TP%, SOs, deviation, multipliers, timeframes |
| `backtest_runner.py` | Full pipeline → HTML report at `results/report.html` |

## How It Works

1. **Screen** top USDT pairs by volume, ATR%, Hurst exponent, BBW
2. **Backtest** each with default Martingale params across timeframes
3. **Optimize** top combos via grid search (TP not anchored — found by optimizer)
4. **Report** interactive Plotly charts: equity curves, regime overlays, heatmaps

## Key Design Decisions

- **Regime gating**: New deals only open in CHOPPY or RANGING markets
- **Existing deals continue** regardless of regime shift
- **Fees + slippage** applied on every fill
- **Timeframe is optimized** alongside strategy parameters
- **Take profit is not hardcoded** — optimizer tests 0.5% to 5.0%

## Testing Data Fetcher

```powershell
C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe -m trading.data_fetcher
```
