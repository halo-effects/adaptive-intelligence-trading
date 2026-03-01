"""Test local top vs ATH scoring."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('SANTIMENT_API_KEY', os.environ.get('SANTIMENT_API_KEY', ''))

from smart_entry import SmartEntryScorer

scorer = SmartEntryScorer(use_grok=False)

for coin in ['bitcoin', 'ethereum', 'solana']:
    print(f"\n=== {coin.upper()} ===", flush=True)
    local_top = scorer._get_local_top(coin, days=365)
    
    # Also get ATH from CoinGecko
    data = scorer._get_coingecko_data(coin)
    if data:
        current = data.get('market_data', {}).get('current_price', {}).get('usd', 0)
        ath = data.get('market_data', {}).get('ath', {}).get('usd', 0)
        print(f"  Current: ${current:,.2f}", flush=True)
        print(f"  ATH:     ${ath:,.2f} ({(ath - current) / ath * 100:.1f}% off)", flush=True)
        if local_top:
            print(f"  12m Top: ${local_top:,.2f} ({(local_top - current) / local_top * 100:.1f}% off)", flush=True)
        else:
            print(f"  12m Top: FAILED to fetch", flush=True)
    import time
    time.sleep(2)

print("\nDone!", flush=True)
