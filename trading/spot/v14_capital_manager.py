import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("V14CapitalManager")
logger.setLevel(logging.INFO)
# Optional: Add a console handler if one isn't configured globally
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


# ---------------------------------------------------------------------------
# Equity-tiered coin cap
# ---------------------------------------------------------------------------
# Format: (min_equity_inclusive, max_coins)
# Evaluated top-down; first match wins.
EQUITY_TIER_CAPS = [
    (100_000, 10),  # $100K+     -> 10 coins (full diversification)
    ( 20_000,  5),  # $20K-$100K ->  5 coins (proven on paper)
    ( 10_000,  5),  # $10K-$20K  ->  5 coins (intermediate split)
    (  5_000,  5),  # $5K-$10K   ->  5 coins (aggressive turnover)
    (  3_000,  4),  # $3K-$5K    ->  4 coins (demo phase: turnover + depth)
    (    100,  3),  # $100-$3K   ->  3 coins (max turnover at small capital)
]

# ---------------------------------------------------------------------------
# Equity-tiered pool splits (active / reserve)
# ---------------------------------------------------------------------------
# Format: (min_equity_inclusive, active_pct, reserve_pct)
# Evaluated top-down; first match wins.
EQUITY_TIER_SPLITS = [
    (20_000, 0.75, 0.25),  # $20K+     -> 75/25 (proven, deep safety buffer)
    (10_000, 0.80, 0.20),  # $10K-$20K -> 80/20 (intermediate — avoids cliff)
    (   100, 0.90, 0.10),  # <$10K     -> 90/10 (max grid depth, bounded risk)
]

# ---------------------------------------------------------------------------
# Hysteresis — prevents tier flapping from normal PnL fluctuation.
# Upgrade: at the threshold (immediate, no buffer).
# Downgrade: only when equity drops TIER_HYSTERESIS_PCT below the threshold.
# ---------------------------------------------------------------------------
TIER_HYSTERESIS_PCT = 0.05  # 5%


class CapitalRouter:
    """
    Capital Router for V14 Engine.
    Manages the distribution of capital between active and reserve pools,
    dynamic allocation based on DCA Score, and dynamic per-coin caps.

    Tier-aware: max coins and pool split scale with current portfolio equity.
    Hysteresis: upgrades are immediate at threshold; downgrades require equity
    to drop 5% below the current tier's threshold (prevents flapping).
    On a tier drop the cap is enforced on new T1 entries only — existing
    positions are allowed to exit gracefully (handled by the runner).
    """
    def __init__(self, initial_capital: float,
                 cap_tier_index: int = -1,
                 split_tier_index: int = -1):
        self.total_equity = initial_capital

        # Tier state — track indices for hysteresis
        # Pass saved indices on restart; -1 = first call (no prior tier)
        self._cap_tier_index: int = self._apply_hysteresis(
            self.total_equity, cap_tier_index if cap_tier_index >= 0 else None,
            EQUITY_TIER_CAPS, lambda r: r[0])
        self._split_tier_index: int = self._apply_hysteresis(
            self.total_equity, split_tier_index if split_tier_index >= 0 else None,
            EQUITY_TIER_SPLITS, lambda r: r[0])

        # Tier-aware coin cap (-1 = below all thresholds)
        self.tier_coin_cap: int = (
            EQUITY_TIER_CAPS[self._cap_tier_index][1]
            if self._cap_tier_index >= 0 else 0
        )

        # Tier-aware pool split (-1 fallback to 90/10)
        if self._split_tier_index >= 0:
            _, active_pct, reserve_pct = EQUITY_TIER_SPLITS[self._split_tier_index]
        else:
            active_pct, reserve_pct = 0.90, 0.10
        self.active_pool_total = self.total_equity * active_pct
        self.reserve_pool_total = self.total_equity * reserve_pct

        # Track available cash
        self.active_pool_cash = self.active_pool_total
        self.reserve_pool_cash = self.reserve_pool_total

        # Track locked allocations
        self.active_allocations: Dict[str, float] = {}
        self.reserve_allocations: Dict[str, float] = {}

        logger.info(f"Initialized CapitalRouter with ${self.total_equity:.2f} total equity.")
        logger.info(f"Pool split: {active_pct*100:.0f}/{reserve_pct*100:.0f} "
                     f"(Active: ${self.active_pool_total:.2f} / Reserve: ${self.reserve_pool_total:.2f})")
        logger.info(f"Tier coin cap: {self.tier_coin_cap} coins "
                     f"(hysteresis active, {TIER_HYSTERESIS_PCT*100:.0f}% downgrade buffer)")

    # ------------------------------------------------------------------
    # Tier lookups
    # ------------------------------------------------------------------

    @staticmethod
    def get_tier_coin_cap(equity: float) -> int:
        """Return the max allowed simultaneous coin positions for the given equity level.
        NOTE: Raw lookup without hysteresis. Use _apply_hysteresis() for tier transitions.
        """
        for threshold, cap in EQUITY_TIER_CAPS:
            if equity >= threshold:
                return cap
        return 0  # Below $100 — no new positions

    @staticmethod
    def get_tier_split(equity: float) -> Tuple[float, float]:
        """Return (active_pct, reserve_pct) for the given equity level.
        NOTE: Raw lookup without hysteresis. Use _apply_hysteresis() for tier transitions.
        """
        for threshold, active, reserve in EQUITY_TIER_SPLITS:
            if equity >= threshold:
                return (active, reserve)
        return (0.90, 0.10)  # Default for tiny accounts

    @staticmethod
    def _apply_hysteresis(equity: float, current_tier_index: Optional[int],
                          tier_table: list, key_fn) -> int:
        """
        Determine the effective tier index with hysteresis.

        - Upgrade (moving to a higher tier): triggers at the threshold — no buffer.
        - Downgrade (moving to a lower tier): only triggers when equity drops
          TIER_HYSTERESIS_PCT (5%) below the current tier's threshold.

        Parameters:
            equity:             Current portfolio equity.
            current_tier_index: Index into tier_table of the tier we're currently on.
                                None on first call (no prior tier).
            tier_table:         The tier lookup table (EQUITY_TIER_CAPS or EQUITY_TIER_SPLITS).
            key_fn:             Callable that extracts the threshold from a tier entry.

        Returns:
            New tier index into tier_table.
        """
        # Raw lookup — what tier would equity land on without hysteresis?
        # If equity is below all thresholds, return -1 (below minimum)
        raw_index = -1
        for i, row in enumerate(tier_table):
            if equity >= key_fn(row):
                raw_index = i
                break

        # First call or no prior tier — no hysteresis, use raw
        if current_tier_index is None:
            return raw_index

        # Below-minimum: raw_index == -1 means equity is below all thresholds
        if raw_index < 0:
            # Downgrade to below-minimum: apply hysteresis on lowest tier
            if current_tier_index >= 0:
                current_threshold = key_fn(tier_table[current_tier_index])
                downgrade_trigger = current_threshold * (1.0 - TIER_HYSTERESIS_PCT)
                if equity < downgrade_trigger:
                    return -1  # Confirmed: below minimum
                return current_tier_index  # Hold (within buffer)
            return -1  # Already below minimum

        # Upgrade from below-minimum to a valid tier: immediate
        if current_tier_index < 0:
            return raw_index

        # Upgrade (raw is a higher tier = lower index): apply immediately
        if raw_index < current_tier_index:
            return raw_index

        # Same tier: no change
        if raw_index == current_tier_index:
            return current_tier_index

        # Downgrade (raw is a lower tier = higher index): apply hysteresis
        # Stay at current tier unless equity dropped 5% below current tier's threshold
        current_threshold = key_fn(tier_table[current_tier_index])
        downgrade_trigger = current_threshold * (1.0 - TIER_HYSTERESIS_PCT)
        if equity < downgrade_trigger:
            return raw_index  # Confirmed downgrade
        else:
            return current_tier_index  # Hold current tier (within buffer)

    def load_scanner_json(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Utility to read cycle_scanner.json and return the rankings.
        Also enriches each ranking entry with trend_multiplier if available.
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            rankings = []
            # Navigate the windows structure from cycle_scanner.json
            if "windows" in data:
                if "30d" in data["windows"]:
                    rankings = data["windows"]["30d"]["rankings"]
                elif "bear" in data["windows"]:
                    rankings = data["windows"]["bear"]["rankings"]
            elif "30d" in data:
                rankings = data["30d"]
            elif "bear" in data:
                rankings = data["bear"]
            elif isinstance(data, list):
                rankings = data
            else:
                for key, val in data.items():
                    if isinstance(val, list):
                        rankings = val
                        break

            # Enrich rankings with trend multipliers from trend_scores
            trend_scores = data.get("trend_scores", {})
            if trend_scores:
                for entry in rankings:
                    coin = entry.get("coin", entry.get("symbol", "").split("/")[0])
                    if coin in trend_scores:
                        td = trend_scores[coin]
                        entry["trend_multiplier"] = td.get("trend_multiplier", 1.0)
                        entry["trend_direction"] = td.get("direction", "stable")
                    # If no trend data, default multiplier is 1.0 (neutral)
                logger.info(f"Trend scores loaded for {len(trend_scores)} coins")

            return rankings
        except Exception as e:
            logger.error(f"Failed to load scanner JSON from {filepath}: {e}")
            return []

    def rebalance_daily(
        self,
        scanner_rankings: List[Dict[str, Any]],
        current_equity: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Processes the daily scanner data, applies rules, and returns target allocations.

        Rules:
        - Hurdle rate: DCA Score >= 5.0
        - Max coins: determined by equity tier (see EQUITY_TIER_CAPS)
        - Proportional weighting by DCA Score
        - Risk Cap: Max 20% of Active Pool per coin
        - Sidelines: Leftover active pool cash remains unallocated

        If current_equity is provided it overrides self.total_equity for tier
        calculation and updates pool totals accordingly.
        """
        logger.info("Starting daily rebalance...")

        # Update equity snapshot and derive tier cap + split (with hysteresis)
        if current_equity is not None and current_equity > 0:
            prev_equity = self.total_equity
            self.total_equity = current_equity
            if abs(current_equity - prev_equity) > 1.0:
                logger.info(f"Equity updated: ${prev_equity:.2f} → ${current_equity:.2f}")

        # Coin cap — hysteresis-aware
        prev_cap_index = self._cap_tier_index
        self._cap_tier_index = self._apply_hysteresis(
            self.total_equity, self._cap_tier_index, EQUITY_TIER_CAPS, lambda r: r[0])
        prev_cap = self.tier_coin_cap
        self.tier_coin_cap = (
            EQUITY_TIER_CAPS[self._cap_tier_index][1]
            if self._cap_tier_index >= 0 else 0
        )
        if self.tier_coin_cap != prev_cap:
            direction = "▼ DOWN" if self.tier_coin_cap < prev_cap else "▲ UP"
            logger.warning(
                f"Tier coin cap changed {direction}: {prev_cap} → {self.tier_coin_cap} "
                f"(equity=${self.total_equity:.2f})"
            )

        # Pool split — hysteresis-aware
        prev_split_index = self._split_tier_index
        self._split_tier_index = self._apply_hysteresis(
            self.total_equity, self._split_tier_index, EQUITY_TIER_SPLITS, lambda r: r[0])
        if self._split_tier_index >= 0:
            _, active_pct, reserve_pct = EQUITY_TIER_SPLITS[self._split_tier_index]
        else:
            active_pct, reserve_pct = 0.90, 0.10
        self.active_pool_total = self.total_equity * active_pct
        self.reserve_pool_total = self.total_equity * reserve_pct
        if self._split_tier_index != prev_split_index:
            logger.warning(
                f"Pool split changed: → {active_pct*100:.0f}/{reserve_pct*100:.0f} "
                f"(equity=${self.total_equity:.2f})"
            )

        logger.info(f"Equity tier: ${self.total_equity:.2f} → max {self.tier_coin_cap} coins | "
                     f"split {active_pct*100:.0f}/{reserve_pct*100:.0f}")

        # 1. Filter: hurdle rate >= 5.0, apply trend multiplier
        qualifying_coins = []
        for coin_data in scanner_rankings:
            symbol = coin_data.get("symbol") or coin_data.get("coin")
            base_score = coin_data.get("dca_score", 0.0)
            trend_mult = coin_data.get("trend_multiplier", 1.0)
            trend_dir = coin_data.get("trend_direction", "stable")
            
            try:
                base_score_float = float(base_score)
                trend_mult_float = float(trend_mult)
            except (ValueError, TypeError):
                continue
            
            # Trend-adjusted score: Base DCA Score × Trend Multiplier
            # Collapsed scores (mult near 0) effectively gate entry
            adjusted_score = base_score_float * trend_mult_float
                
            if base_score_float >= 5.0:
                qualifying_coins.append({
                    "symbol": symbol,
                    "dca_score": base_score_float,
                    "trend_multiplier": trend_mult_float,
                    "trend_direction": trend_dir,
                    "adjusted_score": adjusted_score,
                })
        
        # 2. Sort descending by trend-adjusted score (not raw score)
        qualifying_coins.sort(key=lambda x: x["adjusted_score"], reverse=True)
        
        # 3. Apply tier coin cap (never exceeds cap regardless of how many qualify)
        max_coins = self.tier_coin_cap
        top_coins = qualifying_coins[:max_coins]
        
        if not top_coins:
            if max_coins == 0:
                logger.warning(f"Equity ${self.total_equity:.2f} is below $100 minimum. No positions allowed.")
            else:
                logger.warning("No coins met the >= 5.0 hurdle rate. All capital goes to sidelines.")
            return {}

        # 4. Calculate total adjusted score
        total_score = sum(c["adjusted_score"] for c in top_coins)
        if total_score <= 0:
            logger.warning("All coins have zero adjusted score — skipping allocation")
            return {}
        
        # 5. Proportional weighting by adjusted score & dynamic max cap per coin
        # Scale cap inversely with number of coins:
        #   1 coin → 100%, 2 → 60%, 3 → 47%, 5 → 36%, 10 → 28%
        cap_pct = min(1.0, 0.20 + (0.80 / max(len(top_coins), 1)))
        max_cap_per_coin = cap_pct * self.active_pool_total
        target_allocations = {}
        
        for c in top_coins:
            raw_allocation = (c["adjusted_score"] / total_score) * self.active_pool_total
            final_allocation = min(raw_allocation, max_cap_per_coin)
            target_allocations[c["symbol"]] = final_allocation
            logger.debug(
                f"{c['symbol']}: Base={c['dca_score']:.1f} × Trend={c['trend_multiplier']:.2f} "
                f"= Adj={c['adjusted_score']:.1f} → ${final_allocation:.2f}"
            )

        # 6. Sidelines cash routing
        total_allocated = sum(target_allocations.values())
        sidelines_cash = self.active_pool_total - total_allocated
        
        logger.info(f"Rebalance complete. {len(top_coins)}/{max_coins} coin slots filled.")
        for c in top_coins:
            logger.info(
                f"  {c['symbol']}: Base={c['dca_score']:.1f} × Trend={c['trend_multiplier']:.2f} "
                f"({c['trend_direction']}) = {c['adjusted_score']:.1f} → ${target_allocations[c['symbol']]:.2f}"
            )
        logger.info(f"Total Target Allocation: ${total_allocated:.2f} | Sidelines Cash (Buffer): ${sidelines_cash:.2f}")
        
        return target_allocations

    def request_capital(self, coin: str, amount: float, pool: str = "active") -> float:
        """
        Request capital from either 'active' or 'reserve' pool.
        Returns the granted amount (up to the requested amount, limited by available cash).
        """
        if amount <= 0:
            return 0.0

        if pool.lower() == "active":
            if amount <= self.active_pool_cash:
                self.active_pool_cash -= amount
                self.active_allocations[coin] = self.active_allocations.get(coin, 0.0) + amount
                logger.info(f"Granted ${amount:.2f} to {coin} (Active Pool). Active Cash: ${self.active_pool_cash:.2f}")
                return amount
            else:
                granted = self.active_pool_cash
                self.active_allocations[coin] = self.active_allocations.get(coin, 0.0) + granted
                self.active_pool_cash = 0.0
                if granted > 0:
                    logger.warning(f"Active Pool depleted! Granted partial ${granted:.2f} to {coin}.")
                else:
                    logger.warning(f"Active Pool empty! Request for ${amount:.2f} by {coin} denied.")
                return granted
                
        elif pool.lower() == "reserve":
            # Reserve Pool is strictly for Layer 6+ / emergency
            if amount <= self.reserve_pool_cash:
                self.reserve_pool_cash -= amount
                self.reserve_allocations[coin] = self.reserve_allocations.get(coin, 0.0) + amount
                logger.info(f"Granted ${amount:.2f} to {coin} (Reserve Pool). Reserve Cash: ${self.reserve_pool_cash:.2f}")
                return amount
            else:
                granted = self.reserve_pool_cash
                self.reserve_allocations[coin] = self.reserve_allocations.get(coin, 0.0) + granted
                self.reserve_pool_cash = 0.0
                if granted > 0:
                    logger.warning(f"Reserve Pool depleted! Granted partial ${granted:.2f} to {coin}.")
                else:
                    logger.warning(f"Reserve Pool empty! Request for ${amount:.2f} by {coin} denied.")
                return granted
        else:
            logger.error(f"Unknown pool type requested: {pool}")
            return 0.0

    def return_capital(self, coin: str, amount: float):
        """
        When a deal closes, the freed capital returns entirely to the Active Pool.
        It is then available for immediate re-routing based on current allocations.
        """
        if amount <= 0:
            return

        self.active_pool_cash += amount
        
        # Reset tracking for this coin since the deal closed
        if coin in self.active_allocations:
            self.active_allocations[coin] = 0.0
        if coin in self.reserve_allocations:
            self.reserve_allocations[coin] = 0.0
            
        logger.info(f"Deal close for {coin}: Returned ${amount:.2f} to Active Pool. Active Cash: ${self.active_pool_cash:.2f}")

    def resize(self, new_equity: float):
        """Dynamically resize pools after deposit/withdrawal. Hysteresis-aware."""
        old_equity = self.total_equity
        self.total_equity = new_equity

        # Coin cap — hysteresis-aware
        prev_cap = self.tier_coin_cap
        self._cap_tier_index = self._apply_hysteresis(
            new_equity, self._cap_tier_index, EQUITY_TIER_CAPS, lambda r: r[0])
        self.tier_coin_cap = (
            EQUITY_TIER_CAPS[self._cap_tier_index][1]
            if self._cap_tier_index >= 0 else 0
        )
        if self.tier_coin_cap != prev_cap:
            direction = "DOWN" if self.tier_coin_cap < prev_cap else "UP"
            logger.warning(
                f"Tier coin cap changed {direction}: {prev_cap} -> {self.tier_coin_cap} "
                f"(equity=${new_equity:.2f})"
            )

        # Pool split — hysteresis-aware
        prev_split_index = self._split_tier_index
        self._split_tier_index = self._apply_hysteresis(
            new_equity, self._split_tier_index, EQUITY_TIER_SPLITS, lambda r: r[0])
        if self._split_tier_index >= 0:
            _, active_pct, reserve_pct = EQUITY_TIER_SPLITS[self._split_tier_index]
        else:
            active_pct, reserve_pct = 0.90, 0.10
        self.active_pool_total = new_equity * active_pct
        self.reserve_pool_total = new_equity * reserve_pct

        if self._split_tier_index != prev_split_index:
            logger.warning(
                f"Pool split changed: -> {active_pct*100:.0f}/{reserve_pct*100:.0f} "
                f"(equity=${new_equity:.2f})"
            )

        # Recalculate cash = pool total - allocated
        allocated_active = sum(self.active_allocations.values())
        self.active_pool_cash = self.active_pool_total - allocated_active
        self.reserve_pool_cash = self.reserve_pool_total

        logger.info(
            f"Resized: ${old_equity:.2f} -> ${new_equity:.2f} | "
            f"{active_pct*100:.0f}/{reserve_pct*100:.0f} split | "
            f"max {self.tier_coin_cap} coins | "
            f"active_cash=${self.active_pool_cash:.2f} reserve_cash=${self.reserve_pool_cash:.2f}"
        )


# ---------------------------------------------------------------------------
# Capital Ledger — tracks deposits, withdrawals, and seed capital
# ---------------------------------------------------------------------------

def load_capital_ledger(ledger_path: Path) -> Optional[dict]:
    """Load capital ledger from JSON file. Returns None if file doesn't exist."""
    if not ledger_path.exists():
        return None
    try:
        with open(ledger_path) as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load capital ledger: {e}")
        return None


def save_capital_ledger(ledger_path: Path, ledger: dict):
    """Atomically save capital ledger to JSON (write .tmp then rename)."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = ledger_path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(ledger, f, indent=2)
    tmp.replace(ledger_path)


def record_ledger_transaction(
    ledger_path: Path,
    tx_type: str,
    amount: float,
    note: str = "",
) -> dict:
    """Record a deposit/withdrawal/seed in the capital ledger.

    tx_type: 'seed' | 'deposit' | 'withdrawal'
    Returns the updated ledger dict.
    """
    ledger = load_capital_ledger(ledger_path) or {
        "seed_capital": amount if tx_type == "seed" else 0.0,
        "current_capital": 0.0,
        "transactions": [],
    }
    ts = datetime.now(timezone.utc).isoformat()
    ledger["transactions"].append({
        "timestamp": ts,
        "type": tx_type,
        "amount": amount,
        "note": note,
    })
    if tx_type in ("deposit", "seed"):
        ledger["current_capital"] = ledger.get("current_capital", 0.0) + amount
    elif tx_type == "withdrawal":
        ledger["current_capital"] = ledger.get("current_capital", 0.0) - amount
    save_capital_ledger(ledger_path, ledger)
    return ledger


def get_ledger_summary(ledger_path: Path) -> Optional[dict]:
    """Return a summary dict of the capital ledger, or None if no ledger."""
    ledger = load_capital_ledger(ledger_path)
    if ledger is None:
        return None
    txns = ledger.get("transactions", [])
    return {
        "seed_capital": ledger.get("seed_capital", 0.0),
        "current_capital": ledger.get("current_capital", 0.0),
        "total_deposits": sum(t["amount"] for t in txns if t["type"] == "deposit"),
        "total_withdrawals": sum(t["amount"] for t in txns if t["type"] == "withdrawal"),
        "transaction_count": len(txns),
        "last_transaction": txns[-1] if txns else None,
    }
