import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parent / 'trading' / 'spot' / 'data' / 'candles.db'
if not db.exists():
    print(f'DB not found at {db}')
else:
    conn = sqlite3.connect(str(db))
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print('All tables:', tables)
    for t in ['scanner_results', 'phase_transitions', 'signal_snapshots', 'coin_correlations', 'trade_context']:
        try:
            row = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()
            print(f'  {t}: {row[0]} rows')
        except Exception as e:
            print(f'  {t}: MISSING - {e}')
    conn.close()
