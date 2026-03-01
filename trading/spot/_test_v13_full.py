"""Full V13 backfill test: 4 coins, $10K, high profile, Sept 2024."""
import logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(message)s")
logger = logging.getLogger("test")
logger.setLevel(logging.INFO)

from trading.spot.run_v13_paper import V13PaperBot, CANONICAL_SYMBOLS

bot = V13PaperBot(
    symbols=CANONICAL_SYMBOLS,
    capital=10000.0,
    exchange="hyperliquid",
    profile="high",
    start_date="2024-09-01",
)
logger.info(f"Coins: {bot.symbols}, Capital: ${bot.capital}, Profile: {bot.profile}")

# Suppress engine-level info during backfill (too noisy)
logging.getLogger("trading.spot.v13_lifecycle_engine").setLevel(logging.WARNING)
logging.getLogger("v13_paper").setLevel(logging.WARNING)

bot.backfill()

# Results
logger.info("=" * 60)
logger.info("BACKFILL RESULTS")
logger.info("=" * 60)
total_pnl = 0
total_deals = 0
for sym, engine in bot.engines.items():
    pnl_pct = (engine.realized_pnl / (bot.capital / len(bot.symbols))) * 100
    logger.info(
        f"{sym:12s}: phase={engine.phase:10s} | deals={engine.deals_completed:3d} | "
        f"PnL=${engine.realized_pnl:8.2f} ({pnl_pct:+.1f}%) | "
        f"DD={engine.max_drawdown_pct:.1f}% | "
        f"markup_cycles={engine.markup_cycles_completed} | "
        f"shorts={engine.shorts_enabled} | "
        f"layers={engine.dca_layers}"
    )
    total_pnl += engine.realized_pnl
    total_deals += engine.deals_completed

logger.info(f"\nTotal: ${total_pnl:.2f} PnL, {total_deals} deals, "
            f"{len(bot.tracker.trades)} trades logged")
logger.info(f"Cash: ${bot.cash:.2f}")

# Show phase transitions
for sym, engine in bot.engines.items():
    if engine.markup_cycles_completed > 0 or engine.phase != "DCA":
        logger.info(f"\n{sym} phase history: current={engine.phase}")
