"""Show all signal/gate checks in the engine."""
with open('v13_phase_backtest_v8.py','r') as f:
    lines = f.readlines()
keywords = ['_hh_hl','_adx','_cfgi','_hvf','fib','sma200','stoch','ob_','price_near','price_broke','overext','lh_ll']
for i,line in enumerate(lines,1):
    s = line.strip()
    if any(k in s.lower() for k in keywords) and not s.startswith('#') and not s.startswith('"""') and 'import' not in s and 'def ' not in s:
        print(f'{i:>4}: {s}')
