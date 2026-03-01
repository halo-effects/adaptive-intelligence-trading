import difflib
with open('trading/spot/backtest_engine_v12.py', encoding='utf-8') as f:
    a = f.readlines()
with open('trading/spot/backtest_engine_v12f.py', encoding='utf-8') as f:
    b = f.readlines()
diff = list(difflib.unified_diff(a, b, fromfile='v12e', tofile='v12f', n=1))
keywords = ['def ', 'self.', 'return', 'if ', 'elif ', 'else:', 'class ', 'kwargs', 'import']
for line in diff:
    if line.startswith('@@'):
        print(line.strip())
    elif (line.startswith('-') or line.startswith('+')) and not line.startswith('---') and not line.startswith('+++'):
        s = line[1:].strip()
        if s and not s.startswith('#') and not s.startswith('"""') and len(s) > 5:
            if any(kw in s for kw in keywords):
                print(line.rstrip()[:120])
