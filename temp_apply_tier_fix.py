"""Apply tier cap enforcement fix to run_v14_portfolio_live_aster.py"""
import re

path = r"C:\Users\Never\.openclaw\workspace\trading\spot\run_v14_portfolio_live_aster.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Find the rebalance loop where new engines are created
old_block = '''            for sym, alloc in allocations.items():
                if sym not in self.coins:
                    if self.bot_state != BotState.RUNNING:
                        logger.info(f"Skipping new coin {sym} \u2014 bot state is {self.bot_state}")
                        continue
                    logger.info(f"Creating engine for new coin {sym} (alloc=${alloc:.2f})")
                    cs = CoinState(sym, alloc)'''

new_block = '''            # Enforce tier coin cap: count existing coins with open positions
            active_count = sum(
                1 for cs_ in self.coins.values()
                if cs_.engine and cs_.engine._engine
                and (cs_.engine._engine.long_coins > 0 or cs_.engine._engine.short_coins > 0)
            )
            tier_cap = self.router.tier_coin_cap
            logger.info(f"Rebalance gate: {active_count} active positions, tier cap = {tier_cap}")

            for sym, alloc in allocations.items():
                if sym not in self.coins:
                    if self.bot_state != BotState.RUNNING:
                        logger.info(f"Skipping new coin {sym} \u2014 bot state is {self.bot_state}")
                        continue
                    # Gate: don't exceed tier coin cap with new engines
                    if tier_cap > 0 and active_count >= tier_cap:
                        logger.info(
                            f"Skipping new coin {sym} \u2014 at tier cap "
                            f"({active_count}/{tier_cap} active positions)"
                        )
                        continue
                    logger.info(f"Creating engine for new coin {sym} (alloc=${alloc:.2f})")
                    cs = CoinState(sym, alloc)'''

if old_block in content:
    content = content.replace(old_block, new_block, 1)
    print("Block 1 replaced (tier cap guard)")
else:
    print("ERROR: Could not find rebalance loop block")
    import sys; sys.exit(1)

# Add active_count increment
old_line = "                    self.coins[sym] = cs\n                    # Set leverage on exchange for new coin"
new_line = "                    self.coins[sym] = cs\n                    active_count += 1  # Track newly added coin toward cap\n                    # Set leverage on exchange for new coin"

if old_line in content:
    content = content.replace(old_line, new_line, 1)
    print("Block 2 replaced (active_count increment)")
else:
    print("WARNING: Could not find increment location")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("File saved")

# Verify
import py_compile
py_compile.compile(path, doraise=True)
print("Compiles OK")

# Double-check
with open(path) as f:
    for i, line in enumerate(f, 1):
        if "active_count" in line or "tier_cap" in line or "Rebalance gate" in line:
            print(f"  Line {i}: {line.rstrip()[:100]}")
