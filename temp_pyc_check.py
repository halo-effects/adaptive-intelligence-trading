"""Check if .pyc _write_status has the 'cash' and 'exchange_balance' fields."""
import marshal, types

pyc = r'C:\Users\Never\.openclaw\workspace\trading\spot\__pycache__\run_v14_portfolio_live_aster.cpython-312.pyc'
with open(pyc, 'rb') as f:
    f.read(16)
    code = marshal.loads(f.read())

def find_code(co, name):
    for c in co.co_consts:
        if isinstance(c, types.CodeType):
            if c.co_name == name:
                return c
            r = find_code(c, name)
            if r:
                return r
    return None

ws = find_code(code, '_write_status')
if ws:
    print("_write_status string constants:")
    strs = [c for c in ws.co_consts if isinstance(c, str)]
    for s in strs:
        print(f"  '{s}'")
    print()
    print("Has 'cash':", 'cash' in strs)
    print("Has 'exchange_balance':", 'exchange_balance' in strs)
    print("Has 'total_realized_pnl':", 'total_realized_pnl' in strs)
    print("Has 'timeframe':", 'timeframe' in strs)
    print()
    print("co_names referencing balance:")
    for n in ws.co_names:
        if 'balance' in n.lower() or 'fetch' in n.lower():
            print(f"  {n}")
else:
    print("_write_status NOT FOUND in .pyc")
