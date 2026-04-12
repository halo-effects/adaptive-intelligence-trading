import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv('C:/Users/Never/.openclaw/workspace/projects/basis/skill-scaffold/.env')
from basis import BasisClient

client = BasisClient.create(private_key=os.environ['BASIS_PRIVATE_KEY'], api_key=os.environ.get('BASIS_API_KEY'))
wallet = client.account.address

# Check session state
print('=== Session ===')
try:
    session = client.get_session()
    print(f'Session: {session}')
except Exception as e:
    print(f'Session error: {e}')

# Try to authenticate
print('\n=== Authenticating ===')
try:
    auth = client.authenticate()
    print(f'Auth result: {auth}')
except Exception as e:
    print(f'Auth error: {e}')

# Check session after auth
print('\n=== Session after auth ===')
try:
    session = client.get_session()
    print(f'Session: {session}')
except Exception as e:
    print(f'Session error: {e}')

# Now try API calls that need auth
print('\n=== Faucet Status ===')
try:
    fs = client.api.get_faucet_status()
    print(json.dumps(fs, indent=2, default=str))
except Exception as e:
    print(f'Error: {e}')

print('\n=== Profile ===')
try:
    p = client.api.get_my_profile()
    print(json.dumps(p, indent=2, default=str))
except Exception as e:
    print(f'Error: {e}')

print('\n=== Moltbook ===')
try:
    ms = client.api.get_moltbook_status()
    print(json.dumps(ms, indent=2, default=str))
except Exception as e:
    print(f'Error: {e}')

print('\n=== Tokens (Prediction) ===')
try:
    tokens = client.api.get_tokens(is_prediction=True, limit=5, sort='newest')
    if isinstance(tokens, dict) and 'data' in tokens:
        for t in tokens['data']:
            print(f"  {t.get('symbol','?')} | {t.get('name','?')[:50]} | status: {t.get('predictionStatus','?')}")
    else:
        print(tokens)
except Exception as e:
    print(f'Error: {e}')

print('\n=== All Tokens (newest, looking for Floor+) ===')
try:
    tokens = client.api.get_tokens(limit=30, sort='newest')
    if isinstance(tokens, dict) and 'data' in tokens:
        for t in tokens['data']:
            mult = t.get('multiplier', 100)
            if mult is not None and int(mult) < 100:
                print(f"  {t.get('symbol','?')} | mult={mult} | liq=${t.get('liquidityUSD','?')} | addr: {t.get('address','?')}")
        # Also show all tokens summary
        print(f"\n  Total tokens returned: {len(tokens['data'])}")
        for t in tokens['data'][:10]:
            print(f"  {t.get('symbol','?')} | mult={t.get('multiplier','?')} | type={'Predict+' if t.get('isPrediction') else 'Stable+' if t.get('multiplier',0)==100 else 'Floor+'}")
except Exception as e:
    print(f'Error: {e}')
