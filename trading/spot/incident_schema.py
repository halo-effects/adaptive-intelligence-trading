"""
V14 Losing Trade Incident Report Schema
========================================
Self-contained JSON incident files for post-mortem analysis of losing trades.
Each file is cloud-migration-ready and can be processed by any LLM independently.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _classify_loss(trade: dict, engine_state: dict, config: dict) -> str:
    """Auto-classify the loss type based on trade and engine context."""
    reason = trade.get("reason", "").upper()
    layers = trade.get("layers", 0)
    max_layers = config.get("DCA_MAX_LAYERS", 10)
    regime = trade.get("regime", "")

    # GRID_EXHAUSTION: All layers filled, price kept going against us
    if layers >= max_layers:
        return "GRID_EXHAUSTION"

    # PHASE_TRANSITION: Forced close on direction switch
    if any(kw in reason for kw in ("TOP_OB93", "TOP_FALLBACK", "TOP_FAILSAFE",
                                     "BOTTOM_CONVICTION", "MARKDOWN_FAIL")):
        return "PHASE_TRANSITION"

    # EARLY_EXIT: Closed before grid completion due to early warning or unwind
    if any(kw in reason for kw in ("EARLY_WARNING", "UNWIND")):
        return "EARLY_EXIT"

    # SIGNAL_FAILURE: Conviction or top signal was wrong (loss after signal-driven close)
    if "CONVICTION" in reason or "DIVERGENCE" in reason:
        return "SIGNAL_FAILURE"

    return "UNKNOWN"


def _generate_recommendation(classification: str, trade: dict) -> str:
    """Auto-generate a recommendation based on classification."""
    symbol = trade.get("symbol", "unknown")
    coin = symbol.split("/")[0] if "/" in symbol else symbol
    regime = trade.get("regime", "")
    side = "shorts" if "SHORT" in regime else "longs"

    recommendations = {
        "GRID_EXHAUSTION": f"Consider wider deviation or more layers for {coin} {side}. "
                           f"Price moved beyond grid coverage.",
        "PHASE_TRANSITION": f"Phase transition forced close on {coin}. "
                            f"Review signal timing — conviction/top detection may fire prematurely.",
        "EARLY_EXIT": f"Early exit on {coin} locked in a loss. "
                      f"Consider letting grid TPs hit before unwinding.",
        "SIGNAL_FAILURE": f"Signal-driven entry/exit on {coin} was wrong. "
                          f"Review conviction score threshold or divergence timeout.",
        "UNKNOWN": f"Unclassified loss on {coin}. Manual review recommended.",
    }
    return recommendations.get(classification, recommendations["UNKNOWN"])


def _compute_severity(pnl: float, capital: float) -> str:
    """Classify severity based on loss as % of total capital."""
    if capital <= 0:
        return "UNKNOWN"
    loss_pct = abs(pnl) / capital * 100
    if loss_pct < 1:
        return "LOW"
    elif loss_pct < 5:
        return "MEDIUM"
    else:
        return "HIGH"


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def create_incident_report(
    trade: dict,
    engine_state: dict,
    peer_states: dict,
    market_context: dict,
    config: dict,
) -> dict:
    """
    Create a self-contained incident report for a losing trade.

    Parameters
    ----------
    trade : dict
        The losing trade from TradeTracker. Keys: deal_id, symbol, open_time,
        close_time, regime, layers, invested, pnl, return_pct, duration_h.
    engine_state : dict
        Snapshot of the engine for this coin at time of loss (from get_status()).
    peer_states : dict
        {symbol: status_dict} for other coins at time of loss.
    market_context : dict
        Market-level context: cfgi, regime, trend_direction, etc.
    config : dict
        Strategy config: profile name, DCA params, capital.

    Returns
    -------
    dict
        Self-contained incident JSON ready for file write.
    """
    now = datetime.now(timezone.utc)
    capital = config.get("capital", 10000)
    classification = _classify_loss(trade, engine_state, config)

    # Extract coin status from engine_state
    coin_status = {}
    coins_dict = engine_state.get("coins", {})
    if coins_dict:
        coin_status = next(iter(coins_dict.values()), {})

    # Peer coins summary
    peer_summary = {}
    for sym, st in peer_states.items():
        peer_coins = st.get("coins", {})
        if peer_coins:
            pc = next(iter(peer_coins.values()), {})
            peer_summary[sym] = {
                "phase": pc.get("lifecycle_phase", "unknown"),
                "side": pc.get("side", "none"),
                "layers": pc.get("layers", 0),
                "unrealized_pnl": pc.get("unrealized_pnl", 0),
            }

    max_layers = config.get("DCA_MAX_LAYERS", 10)
    layers_used = trade.get("layers", 0)

    return {
        "incident_id": str(uuid.uuid4()),
        "timestamp": now.isoformat(),
        "schema_version": "1.0",
        "account_id": config.get("account_id", "paper-v14"),
        "strategy_id": f"v14-{config.get('profile', 'medium')}",

        "trade": {
            "deal_id": trade.get("deal_id"),
            "symbol": trade.get("symbol"),
            "open_time": trade.get("open_time"),
            "close_time": trade.get("close_time"),
            "regime": trade.get("regime"),
            "layers": layers_used,
            "invested": trade.get("invested", 0),
            "pnl": trade.get("pnl", 0),
            "return_pct": trade.get("return_pct", 0),
            "duration_h": trade.get("duration_h", 0),
            "close_reason": trade.get("reason", "unknown"),
        },

        "classification": classification,
        "severity": _compute_severity(trade.get("pnl", 0), capital),
        "recommendation": _generate_recommendation(classification, trade),

        "grid_utilization": {
            "layers_filled": layers_used,
            "max_layers": max_layers,
            "utilization_pct": round(layers_used / max_layers * 100, 1) if max_layers > 0 else 0,
        },

        "time_in_trade_hours": trade.get("duration_h", 0),

        "context_at_exit": {
            "phase": coin_status.get("lifecycle_phase"),
            "side": coin_status.get("side"),
            "current_price": coin_status.get("current_price"),
            "avg_entry": coin_status.get("avg_entry"),
            "cfgi": coin_status.get("cfgi"),
            "unrealized_pnl_at_close": coin_status.get("unrealized_pnl", 0),
        },

        "market_context": {
            "cfgi": market_context.get("cfgi"),
            "regime": market_context.get("regime"),
            "trend_direction": market_context.get("trend_direction"),
        },

        "peer_coins": peer_summary,

        "config_snapshot": {
            "profile": config.get("profile"),
            "leverage": config.get("leverage", 1.0),
            "capital": capital,
            "DCA_TP_PCT": config.get("DCA_TP_PCT"),
            "DCA_SO_DEVIATION": config.get("DCA_SO_DEVIATION"),
            "DCA_SO_MULTIPLIER": config.get("DCA_SO_MULTIPLIER"),
            "DCA_MAX_LAYERS": max_layers,
            "DCA_BO_PCT": config.get("DCA_BO_PCT"),
        },
    }
