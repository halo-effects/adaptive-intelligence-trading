"""
GateModel — Signal-Aware Entry Veto + Layer Deployment Gates.
==============================================================
Version: 1.0 | Date: 2026-07-03 | Spec: signal-aware-deployment.md v1.0

Shared module consumed by:
  - v14_cycle_scanner.py (Part A veto flag + Part B sim gating)
  - v14_dca_engine.py (Part B layer gates for L3/L4)
  - run_v14_portfolio_live_aster.py (Part A veto in selector paths)

This module is a LEAF dependency — zero imports from engine, runner,
or any other trading module. All inputs are signal values passed as arguments.

Part A: Overheat/Oversold Entry Veto (selector level)
Part B: Signal-Gated L3/L4 Layer Deployment (grid level)

Both are symmetric for LONG_DCA and SHORT_DCA regimes.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

# ── Part A: Entry Veto Parameters ─────────────────────────────────────────────

RSI_HOT = 78        # Daily RSI(14) >= this → long entry veto (overheat)
RSI_COLD = 22       # Daily RSI(14) <= this → short entry veto (oversold)
EXT_PCT = 0.25      # Close >= SMA50 * (1 + EXT_PCT) → extension veto
DIV_AGE = 5         # Fresh 2D divergence within this many days triggers veto

# Clear conditions
CALM_DAYS = 4       # No new extreme for this many days → eligible to clear
RETRACE_PCT = 0.25  # Price must retrace >= this fraction toward SMA50
VETO_MAX_REVIEW = 21  # Days before review notice (info only, no auto-clear)

# ── Part B: Layer Gate Parameters ─────────────────────────────────────────────

STALL_N = 3         # Number of 1h candles without new extreme to confirm stall
GATE_COOLDOWN_H = 4 # Minimum hours between gated L3 and L4 fills


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class VetoState:
    """State of an entry veto for a coin."""
    active: bool = False
    side: str = ""           # "long" or "short"
    reason: str = ""         # Which condition triggered (A1/A2/A3)
    since: str = ""          # ISO date when veto started
    day_count: int = 0       # Days veto has been active
    extreme_price: float = 0 # Price at the extreme (for retrace calc)


# ── Part A: Entry Veto Logic ─────────────────────────────────────────────────

def entry_veto(
    side: str,
    daily_rsi: float,
    close: float,
    sma50: float,
    has_fresh_divergence: bool,
    divergence_age_days: int = 0,
) -> VetoState:
    """Check if a coin should be vetoed from new entries.

    Args:
        side: "long" or "short" — the prospective grid direction
        daily_rsi: Daily RSI(14) value
        close: Current daily close price
        sma50: Daily SMA(50) value
        has_fresh_divergence: Whether a 2D divergence was recently detected
        divergence_age_days: Days since the divergence was detected

    Returns:
        VetoState with active=True if any veto condition fires
    """
    if side == "long":
        # Overheat veto: coin is vertical, dangerous to enter long
        if daily_rsi >= RSI_HOT:
            return VetoState(active=True, side=side, reason="A1_RSI_HOT",
                           extreme_price=close)
        if sma50 > 0 and close >= sma50 * (1 + EXT_PCT):
            return VetoState(active=True, side=side, reason="A2_EXTENSION",
                           extreme_price=close)
        if has_fresh_divergence and divergence_age_days <= DIV_AGE:
            return VetoState(active=True, side=side, reason="A3_DIVERGENCE",
                           extreme_price=close)
    elif side == "short":
        # Oversold veto: coin is in capitulation, dangerous to enter short
        if daily_rsi <= RSI_COLD:
            return VetoState(active=True, side=side, reason="A1_RSI_COLD",
                           extreme_price=close)
        if sma50 > 0 and close <= sma50 * (1 - EXT_PCT):
            return VetoState(active=True, side=side, reason="A2_EXTENSION",
                           extreme_price=close)
        if has_fresh_divergence and divergence_age_days <= DIV_AGE:
            return VetoState(active=True, side=side, reason="A3_DIVERGENCE",
                           extreme_price=close)

    return VetoState(active=False, side=side)


def veto_clear(
    side: str,
    veto_state: VetoState,
    daily_rsi: float,
    close: float,
    sma50: float,
    days_no_new_extreme: int,
    extreme_price: float,
) -> bool:
    """Check if a veto should be cleared (consolidation evidence).

    All three conditions must pass:
    C1: No new extreme for CALM_DAYS
    C2: Price retraced >= RETRACE_PCT toward SMA50
    C3: RSI back in normalized band

    Args:
        side: "long" or "short"
        veto_state: Current veto state
        daily_rsi: Current daily RSI(14)
        close: Current daily close
        sma50: Current daily SMA(50)
        days_no_new_extreme: Days since last local extreme in overextended direction
        extreme_price: Price at the extreme that triggered the veto

    Returns:
        True if veto should be cleared
    """
    if not veto_state.active:
        return True  # Nothing to clear

    # C1: No new extreme
    if days_no_new_extreme < CALM_DAYS:
        return False

    # C2: Mean reversion begun
    if sma50 > 0 and extreme_price > 0:
        if side == "long":
            # Extreme was a high; retrace = price dropped toward SMA50
            total_distance = extreme_price - sma50
            if total_distance > 0:
                retrace = (extreme_price - close) / total_distance
                if retrace < RETRACE_PCT:
                    return False
        elif side == "short":
            # Extreme was a low; retrace = price bounced toward SMA50
            total_distance = sma50 - extreme_price
            if total_distance > 0:
                retrace = (close - extreme_price) / total_distance
                if retrace < RETRACE_PCT:
                    return False

    # C3: RSI normalized (hysteresis band)
    rsi_low = RSI_COLD + 8   # 30
    rsi_high = RSI_HOT - 8   # 70
    if daily_rsi < rsi_low or daily_rsi > rsi_high:
        return False

    return True


# ── Part B: Signal-Gated Layer Deployment ─────────────────────────────────────

def layer_gate_open(
    side: str,
    layer_idx: int,
    has_flush_stall: bool,
    has_structure_turn: bool,
    hours_since_last_gated_fill: float,
) -> Tuple[bool, str]:
    """Check if a gated layer (L3/L4) should be allowed to fill.

    Only applies to layer_idx >= 2 (L3+). L1/L2 are always mechanical.

    Args:
        side: "long" or "short"
        layer_idx: 0-based layer index (2=L3, 3=L4)
        has_flush_stall: B1 evidence — flush/blow-off followed by stall
        has_structure_turn: B2 evidence — structure + momentum turn
        hours_since_last_gated_fill: Hours since last gated layer filled

    Returns:
        (gate_open, reason) — True if layer should fill, reason string
    """
    # L1/L2 always mechanical
    if layer_idx < 2:
        return (True, "mechanical")

    # Cooldown between gated layers
    if layer_idx >= 3 and hours_since_last_gated_fill < GATE_COOLDOWN_H:
        return (False, f"cooldown ({hours_since_last_gated_fill:.1f}h < {GATE_COOLDOWN_H}h)")

    # At least one exhaustion evidence must be present
    if has_flush_stall:
        return (True, "B1_flush_stall")
    if has_structure_turn:
        return (True, "B2_structure_turn")

    # No evidence — gate stays closed
    return (False, "waiting_for_exhaustion")


# ── Self-Test ─────────────────────────────────────────────────────────────────

def self_test():
    """Basic validation of gate logic."""
    print("GateModel Self-Test")
    print("=" * 60)

    # Part A: Entry veto
    # Long overheat: RSI=82 should trigger
    v = entry_veto("long", daily_rsi=82, close=3.00, sma50=2.00, has_fresh_divergence=False)
    assert v.active and v.reason == "A1_RSI_HOT", f"Expected RSI_HOT veto, got {v}"
    print("  A1 long RSI_HOT veto: ✓")

    # Long extension: close 30% above SMA50
    v = entry_veto("long", daily_rsi=65, close=2.60, sma50=2.00, has_fresh_divergence=False)
    assert v.active and v.reason == "A2_EXTENSION", f"Expected EXTENSION veto, got {v}"
    print("  A2 long EXTENSION veto: ✓")

    # Long OK: RSI=55, close near SMA50
    v = entry_veto("long", daily_rsi=55, close=2.10, sma50=2.00, has_fresh_divergence=False)
    assert not v.active, f"Expected no veto, got {v}"
    print("  Long no-veto (normal): ✓")

    # Short oversold: RSI=18
    v = entry_veto("short", daily_rsi=18, close=1.50, sma50=2.00, has_fresh_divergence=False)
    assert v.active and v.reason == "A1_RSI_COLD", f"Expected RSI_COLD veto, got {v}"
    print("  A1 short RSI_COLD veto: ✓")

    # Part B: Layer gates
    # L1/L2 always open
    ok, reason = layer_gate_open("long", 0, False, False, 100)
    assert ok and reason == "mechanical", f"L1 should be mechanical: {ok}, {reason}"
    ok, reason = layer_gate_open("long", 1, False, False, 100)
    assert ok and reason == "mechanical", f"L2 should be mechanical: {ok}, {reason}"
    print("  L1/L2 mechanical: ✓")

    # L3 without evidence: blocked
    ok, reason = layer_gate_open("long", 2, False, False, 100)
    assert not ok, f"L3 without evidence should be blocked: {ok}, {reason}"
    print("  L3 blocked (no evidence): ✓")

    # L3 with flush stall: open
    ok, reason = layer_gate_open("long", 2, True, False, 100)
    assert ok and reason == "B1_flush_stall", f"L3 with flush should open: {ok}, {reason}"
    print("  L3 open (flush stall): ✓")

    # L4 cooldown: blocked
    ok, reason = layer_gate_open("long", 3, True, True, 2.0)
    assert not ok and "cooldown" in reason, f"L4 should be in cooldown: {ok}, {reason}"
    print("  L4 blocked (cooldown): ✓")

    # L4 after cooldown: open
    ok, reason = layer_gate_open("long", 3, False, True, 5.0)
    assert ok and reason == "B2_structure_turn", f"L4 should open: {ok}, {reason}"
    print("  L4 open (after cooldown): ✓")

    # Veto clear
    vs = VetoState(active=True, side="long", reason="A1_RSI_HOT", extreme_price=3.00)
    cleared = veto_clear("long", vs, daily_rsi=55, close=2.50, sma50=2.00,
                         days_no_new_extreme=5, extreme_price=3.00)
    assert cleared, "Should clear: RSI normalized, retraced, calm days passed"
    print("  Veto clear (all conditions met): ✓")

    not_cleared = veto_clear("long", vs, daily_rsi=55, close=2.90, sma50=2.00,
                             days_no_new_extreme=5, extreme_price=3.00)
    assert not not_cleared, "Should NOT clear: insufficient retrace"
    print("  Veto not cleared (insufficient retrace): ✓")

    print("-" * 60)
    print("ALL CHECKS PASSED ✓")
    return True


if __name__ == "__main__":
    self_test()
