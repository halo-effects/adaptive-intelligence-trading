"""Test CoinState.to_dict() includes layer_count."""
import sys
sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace')
from trading.spot.run_v14_portfolio_live_aster import CoinState

cs = CoinState("TEST/USDT", 100.0)
cs.layer_count = 4
d = cs.to_dict()
print(f"to_dict keys: {list(d.keys())}")
print(f"layer_count in dict: {'layer_count' in d}")
print(f"layer_count value: {d.get('layer_count', 'MISSING')}")
