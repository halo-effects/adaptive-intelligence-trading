import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open(r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-sdk-python\basis\abis\AStasisVault.json') as f:
    data = json.load(f)
    abi = data.get('abi', data) if isinstance(data, dict) else data

for item in abi:
    if item.get('type') == 'function':
        inputs = ', '.join(i['name'] + ': ' + i['type'] for i in item.get('inputs', []))
        outputs = ', '.join(o.get('name', '') + ': ' + o['type'] for o in item.get('outputs', []))
        mut = item.get('stateMutability', '')
        print(f"  {item['name']}({inputs}) -> ({outputs}) [{mut}]")
    elif item.get('type') == 'event':
        inputs = ', '.join(i['name'] + ': ' + i['type'] for i in item.get('inputs', []))
        print(f"  EVENT {item['name']}({inputs})")
