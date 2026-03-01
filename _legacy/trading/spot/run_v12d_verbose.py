#!/usr/bin/env python3
"""Wrapper to run V12 chained backtest with verbose logging for all engines."""
import logging
import sys
from pathlib import Path

# Fix path like the original does
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Set ALL loggers to INFO before any imports
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", force=True)
for name in ["trading", "trading.spot", "trading.spot.backtest_engine_v12",
             "trading.spot.backtest_engine_v9", "trading.spot.backtest_engine_v3",
             "trading.spot.distribution_scorer", "trading.spot.ta_top_scorer"]:
    logging.getLogger(name).setLevel(logging.INFO)

# Now import and run
from run_v12_chained import main
main()
