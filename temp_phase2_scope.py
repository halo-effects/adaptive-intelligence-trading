"""Audit shared files: what's on disk vs what the live bot expects."""
import re

base = r"C:\Users\Never\.openclaw\workspace\trading\spot"

files = {
    "engine/v14_dca_engine.py": {
        "checks": {
            "trailing_stop_fields": ["long_trailing_active", "long_trailing_peak", "short_trailing_active"],
            "trailing_config": ["TRAILING_STOP_ENABLED", "TRAILING_CALLBACK_PCT"],
            "30pct_cap_removed": ["min(order, self.capital)"],
            "taker_fee_trailing": ["is_taker=True"],
            "live_mode_flag": ["live_mode"],
        }
    },
    "v14_lifecycle_engine.py": {
        "checks": {
            "trailing_snapshot": ["long_trailing_active", "long_trailing_peak"],
            "trailing_restore": ["short_trailing_active", "short_trailing_peak"],
        }
    },
    "v14_capital_manager.py": {
        "checks": {
            "equity_tier_splits": ["EQUITY_TIER_SPLITS"],
            "split_tier_index": ["_split_tier_index"],
            "zero_guard": ["total_score <= 0"],
        }
    },
    "v14_cycle_scanner.py": {
        "checks": {
            "bo_pct_030": ["BO_PCT = 0.30", "BO_PCT=0.30", "0.30"],
            "taker_fee_035": ["0.00035"],
            "liquidity_filter": ["TRADEABLE", "LOW_LIQUIDITY"],
            "hurdle_rate": ["hurdle", "HURDLE", "5.0"],
        }
    },
}

for fpath, spec in files.items():
    full = f"{base}\\{fpath.replace('/', chr(92))}"
    try:
        with open(full, encoding="utf-8") as f:
            content = f.read()
        print(f"\n{'='*60}")
        print(f"{fpath} ({len(content)} bytes)")
        print(f"{'='*60}")
        for check_name, patterns in spec["checks"].items():
            found = any(p in content for p in patterns)
            print(f"  {'✅' if found else '❌'} {check_name}")
            if not found:
                print(f"     Missing: {patterns}")
    except FileNotFoundError:
        print(f"\n❌ FILE MISSING: {fpath}")
