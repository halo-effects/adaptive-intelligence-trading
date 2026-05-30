"""Replace _detect_capital_change with new balance-comparison approach."""

with open("trading/spot/run_v14_portfolio_live_aster.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find the method boundaries
start_marker = "    def _detect_capital_change(self):"
end_marker = "    # \u2500\u2500 Per-Coin Regime Flagging"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx < 0 or end_idx < 0:
    print(f"ERROR: Could not find method boundaries. start={start_idx}, end={end_idx}")
    exit(1)

old_method = content[start_idx:end_idx]
print(f"Found old method: {len(old_method)} chars, lines {content[:start_idx].count(chr(10))+1}-{content[:end_idx].count(chr(10))+1}")

new_method = '''    def _detect_capital_change(self):
        """Detect deposits/withdrawals via consecutive balance comparison.

        Approach (2026-05-11 rewrite):
          Compare current USDT balance to previous snapshot, accounting for
          realized PnL and funding that occurred between snapshots.

          expected = prev_balance + realized_pnl_delta + funding_delta
          drift   = actual - expected

          If abs(drift) > threshold, it's a deposit (drift > 0) or
          withdrawal (drift < 0).

        This is immune to unrealized PnL fluctuations because we compare
        USDT total balance and only adjust for known cash flows (realized
        trades + funding). Unrealized PnL is included in usdt_total by the
        exchange, but it's included in BOTH the previous and current
        snapshots, so it cancels out in the delta.

        Threshold: max($5, 2% of tracked capital) to filter noise/rounding.
        Suppressed for 3 cycles after startup (DEX-as-truth init).
        """
        if self._exchange_usdt_total <= 0:
            return  # No exchange data yet

        # Suppress during startup (DEX-as-truth sets this)
        if time.time() < getattr(self, '_deposit_detect_suppress_until', 0):
            # Still learning -- just snapshot current state
            self._prev_usdt_balance = self._exchange_usdt_total
            self._prev_realized_pnl = self._cumulative_realized_pnl
            self._prev_cumulative_funding = sum(
                cs.cumulative_funding for cs in self.coins.values()
            )
            return

        prev_bal = getattr(self, '_prev_usdt_balance', None)
        if prev_bal is None:
            # First cycle -- just record baseline
            self._prev_usdt_balance = self._exchange_usdt_total
            self._prev_realized_pnl = self._cumulative_realized_pnl
            self._prev_cumulative_funding = sum(
                cs.cumulative_funding for cs in self.coins.values()
            )
            return

        # Calculate deltas since last snapshot
        pnl_delta = self._cumulative_realized_pnl - getattr(
            self, '_prev_realized_pnl', self._cumulative_realized_pnl
        )
        funding_now = sum(cs.cumulative_funding for cs in self.coins.values())
        funding_delta = funding_now - getattr(
            self, '_prev_cumulative_funding', funding_now
        )

        expected_balance = prev_bal + pnl_delta + funding_delta
        actual_balance = self._exchange_usdt_total
        drift = actual_balance - expected_balance

        # Update snapshots for next cycle
        self._prev_usdt_balance = actual_balance
        self._prev_realized_pnl = self._cumulative_realized_pnl
        self._prev_cumulative_funding = funding_now

        # Apply threshold
        threshold = max(CAPITAL_DRIFT_MIN_USD, self._tracked_capital * CAPITAL_DRIFT_MIN_PCT)
        if abs(drift) < threshold:
            return  # Normal fluctuation (rounding, micro-fees)

        # Classify and record
        if drift > 0:
            tx_type = "deposit"
            tx_amount = drift
        else:
            tx_type = "withdrawal"
            tx_amount = abs(drift)

        drift_pct = (drift / self._tracked_capital * 100) if self._tracked_capital > 0 else 0

        # Record to ledger
        note = f"Auto-detected via balance comparison (drift ${drift:+.2f}, {drift_pct:+.1f}%)"
        record_ledger_transaction(LEDGER_PATH, tx_type, tx_amount, note=note)

        # Update tracked capital
        old_capital = self._tracked_capital
        if tx_type == "deposit":
            self._tracked_capital += tx_amount
        else:
            self._tracked_capital -= tx_amount

        # Resize router (adjusts pools, tier cap, split -- all hysteresis-aware)
        self.router.resize(self._tracked_capital)
        self.capital = self._tracked_capital

        emoji = "\\U0001f4e5" if tx_type == "deposit" else "\\U0001f4e4"  # deposit / withdrawal
        send_telegram(
            f"{emoji} {TG_PREFIX} <b>{tx_type.capitalize()} detected: ${tx_amount:.2f}</b>\\n"
            f"Balance drift: ${drift:+.2f} ({drift_pct:+.1f}%)\\n"
            f"Capital: ${old_capital:.2f} -> ${self._tracked_capital:.2f}\\n"
            f"Tier: {self.router.tier_coin_cap} coins | "
            f"Split: {EQUITY_TIER_SPLITS[self.router._split_tier_index][1]*100:.0f}/"
            f"{EQUITY_TIER_SPLITS[self.router._split_tier_index][2]*100:.0f}\\n"
            f"Recorded in capital ledger."
        )
        logger.info(
            f"{tx_type.capitalize()} detected: ${tx_amount:.2f} "
            f"(capital ${old_capital:.2f} -> ${self._tracked_capital:.2f})"
        )
        self._save_state()

'''

content = content[:start_idx] + new_method + content[end_idx:]

with open("trading/spot/run_v14_portfolio_live_aster.py", "w", encoding="utf-8") as f:
    f.write(content)

print("DONE. Method replaced successfully.")
