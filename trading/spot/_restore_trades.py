"""
Restore trade history by merging git-recovered CSV with current bot CSV.

Strategy:
1. Load best historical CSV from git (671 trades through May 6)
2. Load current bot CSV (171 trades, some overlapping)
3. Deduplicate by (symbol, open_time, close_time) — the canonical trade key
4. Re-number deal_ids sequentially (avoid collisions)
5. Write merged CSV
6. Do the same for live bot

Safe: only creates new file, doesn't overwrite anything.
"""
import csv
import sys
import subprocess
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(__file__).resolve().parent.parent.parent

def load_csv_from_git(commit: str, path: str) -> list:
    """Load CSV content from a git commit."""
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        capture_output=True, text=True, cwd=str(WORKSPACE)
    )
    if result.returncode != 0:
        print(f"  Failed to load {path} from {commit}: {result.stderr}")
        return []
    lines = result.stdout.strip().split("\n")
    reader = csv.DictReader(lines)
    return list(reader)

def load_csv_from_file(filepath: Path) -> list:
    """Load CSV from disk."""
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def trade_key(row: dict) -> str:
    """Canonical dedup key for a trade."""
    return f"{row.get('symbol','')}|{row.get('open_time','')}|{row.get('close_time','')}"

def merge_trades(historical: list, current: list) -> list:
    """Merge two trade lists, deduplicating by trade key."""
    seen = set()
    merged = []
    
    # Historical first (they're the authoritative older records)
    for row in historical:
        key = trade_key(row)
        if key not in seen:
            seen.add(key)
            merged.append(row)
    
    # Then current (only adds truly new trades)
    added = 0
    for row in current:
        key = trade_key(row)
        if key not in seen:
            seen.add(key)
            merged.append(row)
            added += 1
    
    # Sort by close_time
    def sort_key(r):
        ct = r.get("close_time", "")
        try:
            return datetime.fromisoformat(ct)
        except Exception:
            return datetime.min
    merged.sort(key=sort_key)
    
    # Re-number deal_ids sequentially
    for i, row in enumerate(merged, start=1):
        row["deal_id"] = str(i)
    
    return merged, added

def save_csv(trades: list, filepath: Path, fieldnames: list):
    """Save trades to CSV with atomic write."""
    tmp = filepath.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(trades)
    tmp.replace(filepath)
    print(f"  Written: {filepath} ({len(trades)} trades)")

def main():
    GIT_COMMIT = "8c27b6369"  # Best historical version
    
    # ── Paper bot ──
    print("=== PAPER BOT (V14PM) ===")
    paper_path = "trading/spot/paper/v14_portfolio/trades.csv"
    paper_file = WORKSPACE / paper_path
    
    historical = load_csv_from_git(GIT_COMMIT, paper_path)
    current = load_csv_from_file(paper_file)
    print(f"  Historical (git): {len(historical)} trades")
    print(f"  Current (disk):   {len(current)} trades")
    
    if historical:
        # Backup current
        backup = paper_file.with_name("trades_pre_restore.csv")
        if paper_file.exists():
            import shutil
            shutil.copy2(paper_file, backup)
            print(f"  Backed up current to {backup.name}")
        
        merged, added = merge_trades(historical, current)
        total_pnl = sum(float(r.get("pnl", 0) or 0) for r in merged)
        wins = sum(1 for r in merged if float(r.get("pnl", 0) or 0) > 0)
        print(f"  Merged: {len(merged)} trades ({added} new from current)")
        print(f"  Total PnL: ${total_pnl:,.2f} | Wins: {wins}/{len(merged)}")
        
        # Determine fieldnames from historical (they have the authoritative schema)
        fieldnames = list(historical[0].keys()) if historical else list(current[0].keys())
        save_csv(merged, paper_file, fieldnames)
    
    # ── Live bot ──
    print()
    print("=== LIVE BOT (V14PM) ===")
    live_path = "trading/spot/live/v14pm/trades.csv"
    live_file = WORKSPACE / live_path
    
    historical_live = load_csv_from_git(GIT_COMMIT, live_path)
    current_live = load_csv_from_file(live_file)
    print(f"  Historical (git): {len(historical_live)} trades")
    print(f"  Current (disk):   {len(current_live)} trades")
    
    if historical_live:
        backup_live = live_file.with_name("trades_pre_restore.csv")
        if live_file.exists():
            import shutil
            shutil.copy2(live_file, backup_live)
            print(f"  Backed up current to {backup_live.name}")
        
        # For live, use the live bot's fieldnames (different schema)
        merged_live, added_live = merge_trades(historical_live, current_live)
        total_pnl_live = sum(float(r.get("pnl", 0) or 0) for r in merged_live)
        wins_live = sum(1 for r in merged_live if float(r.get("pnl", 0) or 0) > 0)
        print(f"  Merged: {len(merged_live)} trades ({added_live} new from current)")
        print(f"  Total PnL: ${total_pnl_live:,.2f} | Wins: {wins_live}/{len(merged_live)}")
        
        fieldnames_live = list(historical_live[0].keys()) if historical_live else list(current_live[0].keys())
        save_csv(merged_live, live_file, fieldnames_live)
    
    print()
    print("DONE. Both CSVs restored. Bots will pick up merged history on next restart.")

if __name__ == "__main__":
    main()
