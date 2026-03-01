"""Quick test: V13 backfill on ETH only."""
import logging
logging.basicConfig(level=logging.WARNING)

from trading.spot.run_v13_paper import V13PaperBot

bot = V13PaperBot(
    symbols=["ETH/USDC"],
    capital=2500.0,
    exchange="hyperliquid",
    profile="medium",
    start_date="2025-01-01",
)
bot.backfill()

engine = bot.engines["ETH/USDC"]
print(f"Phase: {engine.phase}")
print(f"Deals: {engine.deals_completed}")
print(f"Realized PnL: ${engine.realized_pnl:.2f}")
print(f"Max DD: {engine.max_drawdown_pct:.1f}%")
print(f"Markup cycles: {engine.markup_cycles_completed}")
print(f"Shorts enabled: {engine.shorts_enabled}")
print(f"DCA layers: {engine.dca_layers}")
print(f"Trades logged: {len(bot.tracker.trades)}")
for t in bot.tracker.trades:
    print(f"  #{t['deal_id']} {t['symbol']} {t['layers']}L "
          f"${t['invested']:,.0f} -> ${t['pnl']:,.2f} ({t['return_pct']:+.1f}%)")
print(f"\nCash: ${bot.cash:.2f}")
print(f"Per-coin cash: ${bot.per_coin_cash['ETH/USDC']:.2f}")
