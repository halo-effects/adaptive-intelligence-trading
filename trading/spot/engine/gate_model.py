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
EXT_PCT = 0.25      # Fallback: Close >= SMA50 * (1 + EXT_PCT) when ATR unavailable
EXT_ATR_MULT = 3.0  # G-2: Close >= SMA50 + EXT_ATR_MULT * ATR14 → extension veto
                    # Calibration: NEAR May 21 (atr%=5.4%, vs_sma50=36%) triggers;
                    # TAO at 25% in healthy conditions does NOT over-veto.
                    # 3.0 * 5.4% = 16.2% threshold for NEAR; 3.0 * 8% = 24% for high-vol coins.
DIV_AGE = 5         # Fresh 2D divergence within this many days triggers veto

# Clear conditions
CALM_DAYS = 4       # No new extreme for this many days → eligible to clear
RETRACE_PCT = 0.25  # Price must retrace >= this fraction toward SMA50
VETO_MAX_REVIEW = 21  # Days before review notice (info only, no auto-clear)

# ── Part B: Layer Gate Parameters ─────────────────────────────────────────────

STALL_N = 3         # Number of 1h candles without new extreme to confirm stall
GATE_COOLDOWN_H = 4 # Minimum hours between gated L3 and L4 fills
GATE_K_MAX = 40     # B2: StochRSI K must be below this (oversold territory only)
                    # A cross at K=75 is not exhaustion evidence


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
    has_bearish_divergence: bool = False,
    has_bullish_divergence: bool = False,
    divergence_age_days: int = 0,
    atr14: float = 0.0,
) -> VetoState:
    """Check if a coin should be vetoed from new entries.

    Args:
        side: "long" or "short" — the prospective grid direction
        daily_rsi: Daily RSI(14) value
        close: Current daily close price
        sma50: Daily SMA(50) value
        has_bearish_divergence: G-3: bearish 2D divergence (price high + RSI low)
            — only consumed for long vetoes (weakness at top)
        has_bullish_divergence: G-3: bullish 2D divergence (price low + RSI high)
            — only consumed for short vetoes (strength at bottom)
        divergence_age_days: Days since the divergence was detected
        atr14: Daily ATR(14) in price units (G-2: for ATR-normalized extension)

    Returns:
        VetoState with active=True if any veto condition fires
    """
    if side == "long":
        # Overheat veto: coin is vertical, dangerous to enter long
        if daily_rsi >= RSI_HOT:
            return VetoState(active=True, side=side, reason="A1_RSI_HOT",
                           extreme_price=close)
        # G-2: ATR-normalized extension (replaces fixed EXT_PCT)
        if sma50 > 0 and atr14 > 0:
            if close >= sma50 + EXT_ATR_MULT * atr14:
                return VetoState(active=True, side=side, reason="A2_EXTENSION",
                               extreme_price=close)
        elif sma50 > 0:
            # Fallback to fixed % if ATR not available
            if close >= sma50 * (1 + EXT_PCT):
                return VetoState(active=True, side=side, reason="A2_EXTENSION",
                               extreme_price=close)
        # G-3: only BEARISH divergence vetoes long entries
        if has_bearish_divergence and divergence_age_days <= DIV_AGE:
            return VetoState(active=True, side=side, reason="A3_DIVERGENCE",
                           extreme_price=close)
    elif side == "short":
        # Oversold veto: coin is in capitulation, dangerous to enter short
        if daily_rsi <= RSI_COLD:
            return VetoState(active=True, side=side, reason="A1_RSI_COLD",
                           extreme_price=close)
        # G-2: ATR-normalized extension (replaces fixed EXT_PCT)
        if sma50 > 0 and atr14 > 0:
            if close <= sma50 - EXT_ATR_MULT * atr14:
                return VetoState(active=True, side=side, reason="A2_EXTENSION",
                               extreme_price=close)
        elif sma50 > 0:
            if close <= sma50 * (1 - EXT_PCT):
                return VetoState(active=True, side=side, reason="A2_EXTENSION",
                               extreme_price=close)
        # G-3: only BULLISH divergence vetoes short entries
        if has_bullish_divergence and divergence_age_days <= DIV_AGE:
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
    atr14: float = 0.0,
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

    # V-4 (FA-1): Do NOT clear if any trigger condition is simultaneously true.
    # Prevents the May-30 gap: veto clears on a day the A2 extension is still active,
    # opening a 1-day re-entry window at elevated prices before A2 re-triggers.
    recheck = entry_veto(side, daily_rsi, close, sma50, atr14=atr14)
    if recheck.active:
        return False

    return True


# ── Part B: Signal-Gated Layer Deployment ─────────────────────────────────────

def layer_gate_open(
    side: str,
    layer_idx: int,
    has_flush_stall: bool,
    has_structure_turn: bool,
    has_higher_low: bool,
    hours_since_last_gated_fill: float,
) -> Tuple[bool, str]:
    """Check if a gated layer (L3/L4) should be allowed to fill.

    Only applies to layer_idx >= 2 (L3+). L1/L2 are always mechanical.

    B2 requires BOTH a StochRSI K↑D cross (K < GATE_K_MAX) AND a higher-low
    on the 1h chart. The higher-low is the anti-noise anchor that prevents
    B2 from triggering on dead-cat bounces within waterfall legs (G-6 finding).

    Args:
        side: "long" or "short"
        layer_idx: 0-based layer index (2=L3, 3=L4)
        has_flush_stall: B1 evidence — stall (STALL_N candles, no new low)
        has_structure_turn: B2 evidence — StochRSI K↑D cross with K < GATE_K_MAX
        has_higher_low: B2 anchor — most recent 1h low > prior swing low
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

    # At least one exhaustion evidence must be present.
    # BOTH B1 and B2 require higher-low anchor (G-6 finding: stall/cross
    # alone fires on brief pauses within waterfall legs).
    if has_flush_stall and has_higher_low:
        return (True, "B1_flush_stall+HL")
    if has_flush_stall and not has_higher_low:
        return (False, "B1_no_higher_low")
    if has_structure_turn and has_higher_low:
        return (True, "B2_structure_turn+HL")
    if has_structure_turn and not has_higher_low:
        return (False, "B2_no_higher_low")

    # No evidence — gate stays closed
    return (False, "waiting_for_exhaustion")


# ── Self-Test ─────────────────────────────────────────────────────────────────

def self_test():
    """Basic validation of gate logic."""
    print("GateModel Self-Test")
    print("=" * 60)

    # Part A: Entry veto
    # A1: Long overheat: RSI=82 should trigger
    v = entry_veto("long", daily_rsi=82, close=3.00, sma50=2.00)
    assert v.active and v.reason == "A1_RSI_HOT", f"Expected RSI_HOT veto, got {v}"
    print("  A1 long RSI_HOT veto: ✓")

    # A2 with ATR (G-2): NEAR-like scenario — atr=0.08, sma50=1.42, close=1.93
    # Threshold = sma50 + 3.0 * atr = 1.42 + 0.24 = 1.66. Close 1.93 > 1.66 → veto
    v = entry_veto("long", daily_rsi=65, close=1.93, sma50=1.42, atr14=0.08)
    assert v.active and v.reason == "A2_EXTENSION", f"Expected ATR EXTENSION veto, got {v}"
    print("  A2 long ATR EXTENSION veto (NEAR-like): ✓")

    # A2 with ATR: high-vol coin at normal distance — atr=0.40, sma50=5.00, close=6.00
    # Threshold = 5.00 + 3.0 * 0.40 = 6.20. Close 6.00 < 6.20 → NO veto
    v = entry_veto("long", daily_rsi=65, close=6.00, sma50=5.00, atr14=0.40)
    assert not v.active, f"High-vol coin at 20% above SMA50 should NOT veto, got {v}"
    print("  A2 long no-veto (high-vol coin, normal range): ✓")

    # A2 fallback (no ATR): close 30% above SMA50
    v = entry_veto("long", daily_rsi=65, close=2.60, sma50=2.00)
    assert v.active and v.reason == "A2_EXTENSION", f"Expected EXTENSION veto, got {v}"
    print("  A2 long EXTENSION fallback (no ATR): ✓")

    # Long OK: RSI=55, close near SMA50
    v = entry_veto("long", daily_rsi=55, close=2.10, sma50=2.00)
    assert not v.active, f"Expected no veto, got {v}"
    print("  Long no-veto (normal): ✓")

    # A1: Short oversold: RSI=18
    v = entry_veto("short", daily_rsi=18, close=1.50, sma50=2.00)
    assert v.active and v.reason == "A1_RSI_COLD", f"Expected RSI_COLD veto, got {v}"
    print("  A1 short RSI_COLD veto: ✓")

    # G-3: Bearish divergence vetoes LONG, NOT short
    v = entry_veto("long", daily_rsi=65, close=2.10, sma50=2.00,
                   has_bearish_divergence=True, divergence_age_days=3)
    assert v.active and v.reason == "A3_DIVERGENCE", f"Bearish div should veto long: {v}"
    v = entry_veto("short", daily_rsi=35, close=1.90, sma50=2.00,
                   has_bearish_divergence=True, divergence_age_days=3)
    assert not v.active, f"Bearish div must NOT veto short: {v}"
    print("  G-3 bearish divergence: vetoes long ✓, ignores short ✓")

    # G-3: Bullish divergence vetoes SHORT, NOT long
    v = entry_veto("short", daily_rsi=35, close=1.90, sma50=2.00,
                   has_bullish_divergence=True, divergence_age_days=3)
    assert v.active and v.reason == "A3_DIVERGENCE", f"Bullish div should veto short: {v}"
    v = entry_veto("long", daily_rsi=65, close=2.10, sma50=2.00,
                   has_bullish_divergence=True, divergence_age_days=3)
    assert not v.active, f"Bullish div must NOT veto long: {v}"
    print("  G-3 bullish divergence: vetoes short ✓, ignores long ✓")

    # Part B: Layer gates
    # L1/L2 always open
    ok, reason = layer_gate_open("long", 0, False, False, False, 100)
    assert ok and reason == "mechanical", f"L1 should be mechanical: {ok}, {reason}"
    ok, reason = layer_gate_open("long", 1, False, False, False, 100)
    assert ok and reason == "mechanical", f"L2 should be mechanical: {ok}, {reason}"
    print("  L1/L2 mechanical: ✓")

    # L3 without evidence: blocked
    ok, reason = layer_gate_open("long", 2, False, False, False, 100)
    assert not ok, f"L3 without evidence should be blocked: {ok}, {reason}"
    print("  L3 blocked (no evidence): ✓")

    # L3 with flush stall + higher-low: open
    ok, reason = layer_gate_open("long", 2, True, False, True, 100)
    assert ok and "B1_flush_stall" in reason, f"B1+HL should open: {ok}, {reason}"
    print("  L3 open (B1 stall + higher-low): ✓")

    # L3 with flush stall, NO higher-low: BLOCKED (G-6 fix)
    ok, reason = layer_gate_open("long", 2, True, False, False, 100)
    assert not ok and "B1_no_higher_low" in reason, f"B1 without HL should block: {ok}, {reason}"
    print("  L3 blocked (B1 stall, no higher-low): ✓")

    # L3 with structure turn BUT no higher-low: BLOCKED
    ok, reason = layer_gate_open("long", 2, False, True, False, 100)
    assert not ok and "no_higher_low" in reason, f"B2 without HL should block: {ok}, {reason}"
    print("  L3 blocked (B2 cross, no higher-low): ✓")

    # L3 with structure turn AND higher-low: OPEN
    ok, reason = layer_gate_open("long", 2, False, True, True, 100)
    assert ok and "B2_structure_turn" in reason, f"B2+HL should open: {ok}, {reason}"
    print("  L3 open (B2 cross + higher-low): ✓")

    # L4 cooldown: blocked
    ok, reason = layer_gate_open("long", 3, True, True, True, 2.0)
    assert not ok and "cooldown" in reason, f"L4 should be in cooldown: {ok}, {reason}"
    print("  L4 blocked (cooldown): ✓")

    # L4 after cooldown with B2 + HL: open
    ok, reason = layer_gate_open("long", 3, False, True, True, 5.0)
    assert ok and "B2_structure_turn" in reason, f"L4 should open: {ok}, {reason}"
    print("  L4 open (after cooldown, B2 + HL): ✓")

    # Veto clear — close=2.50, sma50=2.00, atr14=0.20 → threshold=2.60, close below → no re-trigger
    vs = VetoState(active=True, side="long", reason="A1_RSI_HOT", extreme_price=3.00)
    cleared = veto_clear("long", vs, daily_rsi=55, close=2.50, sma50=2.00,
                         days_no_new_extreme=5, extreme_price=3.00, atr14=0.20)
    assert cleared, "Should clear: RSI normalized, retraced, no trigger active"
    print("  Veto clear (all conditions met, no re-trigger): ✓")

    not_cleared = veto_clear("long", vs, daily_rsi=55, close=2.90, sma50=2.00,
                             days_no_new_extreme=5, extreme_price=3.00, atr14=0.20)
    assert not not_cleared, "Should NOT clear: insufficient retrace"
    print("  Veto not cleared (insufficient retrace): ✓")

    # V-4 (FA-1): veto must NOT clear when trigger condition is simultaneously true
    # Scenario: C1/C2/C3 all pass, BUT close is still extended above ATR threshold
    # close=2.80, sma50=2.00, atr14=0.20 → threshold=2.60 → close > threshold → A2 re-triggers
    v4_vs = VetoState(active=True, side="long", reason="A1_RSI_HOT", extreme_price=3.00)
    v4_cleared = veto_clear("long", v4_vs, daily_rsi=55, close=2.80, sma50=2.00,
                            days_no_new_extreme=5, extreme_price=3.00, atr14=0.20)
    assert not v4_cleared, "V-4: must NOT clear when A2 extension still true (close 2.80 > threshold 2.60)"
    print("  V-4: veto blocked from clearing while trigger active: ✓")

    # ── G-1: NEAR fixture (spec §6, audit L-2) ───────────────────────────
    # Real NEAR/USDT daily data from candles_daily, May-July 2026.
    # Validates the full veto lifecycle against a known blow-off → crash → basing cycle.
    print("\n  G-1 NEAR Fixture (real data):")

    # NEAR timeline:
    # May 21: RSI 78.6, close $1.93, sma50 $1.42, atr14 ~$0.077 → blow-off begins
    # May 25: RSI 90.0, close $2.78, peak
    # Jun 4-6: crash to $1.86-$2.20
    # Jun 7-8: dead-cat bounce to $2.06-$2.13, RSI 48-50
    # Late Jun: basing at $1.78-$1.87, RSI 39-42
    # Jul 2-3: recovery begins, RSI 47-52

    # 1. Veto TRIGGERS on May 21 (RSI crosses 78)
    v = entry_veto("long", daily_rsi=78.6, close=1.9266, sma50=1.4161, atr14=0.077)
    assert v.active and v.reason == "A1_RSI_HOT", (
        f"NEAR May 21: RSI 78.6 must trigger A1 veto, got {v}")
    extreme = v.extreme_price
    print("    May 21 veto triggers (RSI 78.6): ✓")

    # 2. Veto does NOT clear at ~$2.40 first-RSI-cooldown (May 28-29)
    #    RSI dropped to 69.8 but only 3 days since peak (May 25). C1 fails.
    vs = VetoState(active=True, side="long", reason="A1_RSI_HOT",
                   extreme_price=2.7826)  # May 25 peak
    cleared = veto_clear("long", vs, daily_rsi=69.8, close=2.4340, sma50=1.5864,
                         days_no_new_extreme=3, extreme_price=2.7826)
    assert not cleared, (
        "NEAR May 28: veto must NOT clear at $2.43 — only 3 calm days (need 4)")
    print("    May 28 veto holds at $2.43 (3 calm days < 4): ✓")

    # 2b. V-4 assertion: May 30, C1/C2/C3 all pass BUT A2 extension still true.
    #     close=$2.25, sma50=$1.62, atr14=$0.146 → threshold=$1.62+3*0.146=$2.06
    #     Close $2.25 > threshold $2.06 → A2 would re-trigger.
    #     V-4 guard prevents clear. The May-30 gap is now CLOSED.
    vs_may30 = VetoState(active=True, side="long", reason="A1_RSI_HOT",
                         extreme_price=2.7826)
    cleared_may30 = veto_clear("long", vs_may30, daily_rsi=60.9, close=2.2500,
                               sma50=1.6245, days_no_new_extreme=4,
                               extreme_price=2.7826, atr14=0.146)
    assert not cleared_may30, (
        "V-4 NEAR May 30: must NOT clear — A2 extension still true "
        "(close $2.25 > threshold $2.06)")
    print("    V-4 May 30 gap CLOSED (no clear while A2 active): ✓")

    # 3. Verify A2 re-triggers at the bounce (Jun 1-3: close $2.64-$2.82)
    v = entry_veto("long", daily_rsi=70.3, close=2.6380, sma50=1.6687, atr14=0.137)
    # Threshold = 1.6687 + 3.0 * 0.137 = 2.08. Close 2.64 > 2.08 → A2 triggers.
    # But A1 is checked first and RSI 70.3 < 78, so A2 is the expected trigger.
    assert v.active and v.reason == "A2_EXTENSION", (
        f"NEAR Jun 1: close $2.64, sma50 $1.67, atr $0.14 must trigger A2, got {v}")
    print("    Jun 1 re-veto via A2 extension ($2.64 vs threshold $2.08): ✓")

    # 4. Veto CLEARS during late-June basing (~$1.80)
    vs = VetoState(active=True, side="long", reason="A2_EXTENSION",
                   extreme_price=2.7826)
    cleared = veto_clear("long", vs, daily_rsi=41.8, close=1.8680, sma50=2.0605,
                         days_no_new_extreme=10, extreme_price=2.7826, atr14=0.218)
    # C1: 10 days no new extreme > 4 ✓
    # C2: retrace = (2.78 - 1.87) / (2.78 - 2.06) = 0.91/0.72 = 1.26 > 0.25 ✓
    # C3: RSI 41.8 is in [30, 70] ✓
    # V-4: close $1.87 < sma50+3*atr = $2.06+0.65 = $2.71 → no re-trigger ✓
    assert cleared, (
        "NEAR Jun 27: veto must clear at $1.87 basing — all conditions met, no trigger active")
    print("    Jun 27 veto clears at $1.87 basing (V-4 safe, below threshold): ✓")

    # 5. No veto at $2.05 recovery (Jul 3: RSI 52, normal)
    v = entry_veto("long", daily_rsi=52.0, close=2.0450, sma50=2.0973, atr14=0.185)
    assert not v.active, (
        f"NEAR Jul 3: RSI 52, close near SMA50 — no veto expected, got {v}")
    print("    Jul 3 no veto at recovery ($2.05, RSI 52): ✓")

    print("-" * 60)
    print("ALL CHECKS PASSED ✓")
    return True


if __name__ == "__main__":
    self_test()
