"""Full two-tier coin scanner: discovery → filter → backtest → recommend.

Standalone: python trading/run_scanner.py
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from pathlib import Path

from trading.coin_scanner_t1 import run_tier1
from trading.coin_scanner_t2 import run_tier2

LIVE_DIR = Path(__file__).parent / "live"
LIVE_DIR.mkdir(exist_ok=True)

CURRENT_COIN = "HYPE/USDT"
ROTATION_THRESHOLD = 0.20  # new coin must score 20% better


def run_full_scan(top_n_t1: int = 8):
    print("╔" + "═" * 68 + "╗")
    print("║       ASTER DEX — TWO-TIER COIN SCANNER                          ║")
    print("╚" + "═" * 68 + "╝")
    print(f"  Current coin: {CURRENT_COIN}")
    print(f"  Rotation threshold: {ROTATION_THRESHOLD:.0%} improvement required")
    print()

    # ── Tier 1 ──
    t1_results = run_tier1(top_n=top_n_t1 + 5)  # get a few extra

    if not t1_results:
        print("\n❌ No coins passed Tier 1. Recommend: HOLD current.")
        return

    # Take top N for deep scan
    t2_candidates = t1_results[:top_n_t1]

    # Ensure current coin is included for comparison
    current_in_list = any(c["symbol"] == CURRENT_COIN for c in t2_candidates)
    if not current_in_list:
        # Add current coin to T2 even if it didn't make T1 top N
        current_in_t1 = [c for c in t1_results if c["symbol"] == CURRENT_COIN]
        if current_in_t1:
            t2_candidates.append(current_in_t1[0])
        else:
            # Force add with zero T1 score
            t2_candidates.append({"symbol": CURRENT_COIN, "total_score": 0})

    # ── Tier 2 ──
    print()
    t2_results = run_tier2(t2_candidates)

    if not t2_results:
        print("\n❌ No coins passed Tier 2. Recommend: HOLD current.")
        return

    # ── Recommendation ──
    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)

    best = t2_results[0]
    current_result = next((r for r in t2_results if r["symbol"] == CURRENT_COIN), None)

    if current_result is None:
        # Current coin didn't survive T2 at all
        print(f"\n  ⚠️  Current coin {CURRENT_COIN} produced 0 deals in backtest!")
        print(f"  🔄 ROTATE to {best['symbol']} (score: {best['composite_score']})")
    elif best["symbol"] == CURRENT_COIN:
        print(f"\n  ✅ HOLD {CURRENT_COIN} — it's already the best! (score: {best['composite_score']})")
    else:
        improvement = (best["composite_score"] - current_result["composite_score"]) / max(current_result["composite_score"], 0.01)
        print(f"\n  Current: {CURRENT_COIN} (score: {current_result['composite_score']})")
        print(f"  Best:    {best['symbol']} (score: {best['composite_score']})")
        print(f"  Improvement: {improvement:.1%}")

        if improvement > ROTATION_THRESHOLD:
            print(f"\n  🔄 ROTATE to {best['symbol']} (+{improvement:.1%} > {ROTATION_THRESHOLD:.0%} threshold)")
        else:
            print(f"\n  ✅ HOLD {CURRENT_COIN} — improvement below {ROTATION_THRESHOLD:.0%} threshold")

    # Save final recommendation
    rec = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "current_coin": CURRENT_COIN,
        "best_coin": best["symbol"],
        "best_score": best["composite_score"],
        "current_score": current_result["composite_score"] if current_result else None,
        "action": "ROTATE" if (current_result is None or
                               (best["symbol"] != CURRENT_COIN and
                                (best["composite_score"] - (current_result["composite_score"] if current_result else 0))
                                / max((current_result["composite_score"] if current_result else 0), 0.01) > ROTATION_THRESHOLD))
                  else "HOLD",
        "top_5": [{"symbol": r["symbol"], "score": r["composite_score"],
                    "daily_roi": r["daily_roi_pct"], "deals_per_day": r["deals_per_day"]}
                  for r in t2_results[:5]],
    }
    rec_path = LIVE_DIR / "scanner_recommendation.json"
    rec_path.write_text(json.dumps(rec, indent=2))
    print(f"\n  Recommendation saved to {rec_path}")


if __name__ == "__main__":
    run_full_scan()
