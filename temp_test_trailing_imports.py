import sys
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")
from trading.spot.run_v14_portfolio_live_aster import (
    TRAILING_STOP_ENABLED, TRAILING_CALLBACK_PCT, CoinState, AsterPerpClient
)

print(f"TRAILING_STOP_ENABLED = {TRAILING_STOP_ENABLED}")
print(f"TRAILING_CALLBACK_PCT = {TRAILING_CALLBACK_PCT}")

cs = CoinState("TAO/USDT", 3600)
print(f"CoinState.tp_type = {cs.tp_type}")
print(f"CoinState.tp_activation_price = {cs.tp_activation_price}")
print(f"CoinState.trailing_callback_pct = {cs.trailing_callback_pct}")

d = cs.to_dict()
print(f"to_dict: tp_type={d['tp_type']}, tp_activation_price={d['tp_activation_price']}, trailing_callback_pct={d['trailing_callback_pct']}")

print(f"has place_trailing_stop_sell: {hasattr(AsterPerpClient, 'place_trailing_stop_sell')}")
print(f"has place_limit_sell: {hasattr(AsterPerpClient, 'place_limit_sell')}")
print(f"has cancel_tp_order: {hasattr(AsterPerpClient, 'cancel_tp_order')}")

print("\nAll imports and fields OK ✅")
