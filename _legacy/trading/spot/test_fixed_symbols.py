"""Test the fixed symbol mappings for coins that were broken."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

from composite_scoring import _coin_id_to_symbol, score_strategy_fit, score_risk
from technical_enhanced import EnhancedTechnicalScorer

# These were broken before
test_coins = {
    'polygon-ecosystem-token': 'POL/USDT',
    'render-token': 'RENDER/USDT', 
    'injective-protocol': 'INJ/USDT',
    'sui': 'SUI/USDT',
    'aptos': 'APT/USDT',
}

print("=== Symbol Mapping Check ===", flush=True)
for cid, expected in test_coins.items():
    actual = _coin_id_to_symbol(cid)
    status = "OK" if actual == expected else f"WRONG (got {actual})"
    print(f"  {cid:30s} -> {actual:15s} {status}", flush=True)

print("\n=== Tier 1 Technical Scores ===", flush=True)
scorer = EnhancedTechnicalScorer(exchange_id='binance', timeframes=['4h'])
for cid, sym in test_coins.items():
    print(f"  Scoring {sym}...", flush=True)
    try:
        result = scorer.score(sym)
        print(f"    {sym}: tier1={result['tier1_score']:.1f}", flush=True)
    except Exception as e:
        print(f"    {sym}: ERROR {e}", flush=True)

print("\n=== Tier 2 Strategy Fit ===", flush=True)
for cid, sym in test_coins.items():
    print(f"  Scoring {sym}...", flush=True)
    try:
        result = score_strategy_fit(sym, exchange_id='binance')
        print(f"    {sym}: tier2={result['strategy_fit_score']:.1f}", flush=True)
    except Exception as e:
        print(f"    {sym}: ERROR {e}", flush=True)

print("\nDone!", flush=True)
