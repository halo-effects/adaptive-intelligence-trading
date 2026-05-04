import sqlite3, os, glob

data_dir = r"C:\Users\Never\.openclaw\workspace\trading\spot\data"
for db_file in glob.glob(os.path.join(data_dir, "*.db")):
    name = os.path.basename(db_file)
    conn = sqlite3.connect(db_file)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"{name}: {len(tables)} tables")
    # Show tables with coin names we care about
    for t in tables:
        for coin in ["TAO", "ZEC", "FET", "JTO", "HYPE"]:
            if coin in t.upper():
                count = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
                print(f"  {t}: {count} rows")
                break
    conn.close()
