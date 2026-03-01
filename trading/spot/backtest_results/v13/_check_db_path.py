"""Check if default DB path differs between contexts."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_signals import DB_PATH
print(f"v13_signals.DB_PATH = {DB_PATH}")
print(f"Exists: {DB_PATH.exists()}")

# Check what the wrapper would use
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# Wrapper imports V13SignalPack which uses the same DB_PATH
print(f"\nExplicit DB = C:\\Users\\Never\\.openclaw\\workspace\\trading\\spot\\data\\candles.db")
print(f"Same? {str(DB_PATH) == r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'}")
