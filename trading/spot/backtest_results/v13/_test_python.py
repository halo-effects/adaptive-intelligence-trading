#!/usr/bin/env python3
"""Simple test script to check Python environment."""

print("Python test running...")

try:
    import sys
    print(f"Python version: {sys.version}")
    
    import pandas as pd
    print(f"Pandas version: {pd.__version__}")
    
    import numpy as np
    print(f"Numpy version: {np.__version__}")
    
    import sqlite3
    print("SQLite3 available")
    
    print("All basic imports successful!")
    
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Error: {e}")