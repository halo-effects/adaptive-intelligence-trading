"""Apply tier cap enforcement fix to run_v14_portfolio_live_aster.py"""

path = r"C:\Users\Never\.openclaw\workspace\trading\spot\run_v14_portfolio_live_aster.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

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
    print("Tier cap guard applied")
else:
    if "Rebalance gate:" in content:
        print("Tier cap guard already present")
    else:
        print("ERROR: Cannot find target block")
        import sys; sys.exit(1)

old_line = "                    self.coins[sym] = cs\n                    # Set leverage on exchange for new coin"
new_line = "                    self.coins[sym] = cs\n                    active_count += 1  # Track newly added coin toward cap\n                    # Set leverage on exchange for new coin"
if old_line in content and "active_count += 1" not in content:
    content = content.replace(old_line, new_line, 1)
    print("Active count increment applied")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

import py_compile
py_compile.compile(path, doraise=True)
print("Compiles OK")
