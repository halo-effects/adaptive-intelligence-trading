import sqlite3, glob, os

data_dir = r"C:\Users\Never\.openclaw\workspace\trading\spot\data"
for db_file in glob.glob(os.path.join(data_dir, "*.db")):
    name = os.path.basename(db_file)
    conn = sqlite3.connect(db_file)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"\n{name}:")
    for t in sorted(tables):
        count = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
        print(f"  {t}: {count:,} rows")
    conn.close()

# Also check for other data locations
for pattern in [r"C:\Users\Never\.openclaw\workspace\trading\**\*.db"]:
    for f in glob.glob(pattern, recursive=True):
        if "data" not in f:
            print(f"\nOther DB: {f}")
