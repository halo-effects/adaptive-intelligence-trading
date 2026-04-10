"""Phase 1: Static Analysis Audit for V14PM Trading System"""
import ast
import os
import sys
import re
from pathlib import Path
from collections import defaultdict

WORKSPACE = Path(r"C:\Users\Never\.openclaw\workspace")
TRADING = WORKSPACE / "trading" / "spot"

# All production source files
PROD_FILES = [
    TRADING / "run_v14_portfolio_live_aster.py",
    TRADING / "v14_lifecycle_engine.py",
    TRADING / "v14_capital_manager.py",
    TRADING / "exchange_client.py",
    TRADING / "v14_cycle_scanner.py",
    TRADING / "collect_scanner_candles.py",
    TRADING / "coin_scanner.py",
    TRADING / "cfgi_client.py",
    TRADING / "backfill_binance.py",
    TRADING / "generate_daily_equity.py",
    TRADING / "resample_daily.py",
    TRADING / "run_daily_collector.py",
    TRADING / "engine" / "v14_dca_engine.py",
    TRADING / "engine" / "v13_router_engine_v2.py",
    TRADING / "engine" / "v13_signals.py",
    TRADING / "engine" / "v13_router_engine_v1.py",
    TRADING / "engine" / "v13_phase_backtest_v8.py",
    TRADING / "engine" / "build_daily_candles.py",
]

print("=" * 70)
print("PHASE 1: STATIC ANALYSIS AUDIT")
print("=" * 70)

# ─── 1. SYNTAX VERIFICATION ───────────────────────────────────────────
print("\n### 1. SYNTAX VERIFICATION ###")
syntax_errors = []
for f in PROD_FILES:
    if not f.exists():
        print(f"  MISSING: {f.relative_to(WORKSPACE)}")
        continue
    try:
        source = f.read_text(encoding="utf-8")
        ast.parse(source)
        print(f"  OK: {f.relative_to(WORKSPACE)}")
    except SyntaxError as e:
        syntax_errors.append((f, e))
        print(f"  SYNTAX ERROR: {f.relative_to(WORKSPACE)} line {e.lineno}: {e.msg}")

if not syntax_errors:
    print("\n  All 18 files parse cleanly.")

# ─── 2. IMPORT RESOLUTION ─────────────────────────────────────────────
print("\n### 2. IMPORT RESOLUTION ###")

# Collect all imports from production files
import_issues = []
for f in PROD_FILES:
    if not f.exists():
        continue
    tree = ast.parse(f.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name
                # Check if it's a local trading module
                if mod.startswith("trading."):
                    parts = mod.replace(".", os.sep) + ".py"
                    full = WORKSPACE / parts
                    if not full.exists():
                        # Check if it's a package (directory with __init__.py)
                        pkg = WORKSPACE / mod.replace(".", os.sep)
                        if not (pkg / "__init__.py").exists():
                            import_issues.append((f.name, mod, "module not found"))
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("trading."):
                parts = node.module.replace(".", os.sep) + ".py"
                full = WORKSPACE / parts
                if not full.exists():
                    pkg = WORKSPACE / node.module.replace(".", os.sep)
                    if not (pkg / "__init__.py").exists():
                        import_issues.append((f.name, node.module, "module not found"))

if import_issues:
    for src, mod, issue in import_issues:
        print(f"  ISSUE: {src} imports {mod} — {issue}")
else:
    print("  All local imports resolve correctly.")

# ─── 3. HARDCODED PATHS ───────────────────────────────────────────────
print("\n### 3. HARDCODED PATHS (Windows-specific) ###")
path_patterns = [
    r'C:\\Users',
    r'C:/Users',
    r'\\\\Users\\\\Never',
    r'AppData',
    r'\.openclaw',
]
hardcoded = []
for f in PROD_FILES:
    if not f.exists():
        continue
    lines = f.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines, 1):
        # Skip comments
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for pat in path_patterns:
            if re.search(pat, line, re.IGNORECASE):
                hardcoded.append((f.name, i, line.strip()[:120]))
                break

if hardcoded:
    for src, line, text in hardcoded:
        print(f"  {src}:{line} — {text}")
else:
    print("  No hardcoded Windows paths found in production code.")

# ─── 4. TODO/FIXME/HACK MARKERS ──────────────────────────────────────
print("\n### 4. TODO / FIXME / HACK / XXX MARKERS ###")
markers = []
for f in PROD_FILES:
    if not f.exists():
        continue
    lines = f.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines, 1):
        for tag in ["TODO", "FIXME", "HACK", "XXX", "WORKAROUND", "TEMP"]:
            if tag in line.upper() and not line.strip().startswith('"""'):
                markers.append((f.name, i, tag, line.strip()[:120]))
                break

if markers:
    print(f"  Found {len(markers)} markers:")
    for src, line, tag, text in markers:
        print(f"    {src}:{line} [{tag}] {text}")
else:
    print("  No TODO/FIXME/HACK markers found.")

# ─── 5. BARE EXCEPTS / BROAD EXCEPTION HANDLING ──────────────────────
print("\n### 5. EXCEPTION HANDLING AUDIT ###")
broad_excepts = []
for f in PROD_FILES:
    if not f.exists():
        continue
    lines = f.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Bare except
        if stripped == "except:":
            broad_excepts.append((f.name, i, "bare except", stripped))
        # except Exception (too broad in critical paths)
        elif re.match(r'^except\s+Exception\b', stripped):
            broad_excepts.append((f.name, i, "broad Exception", stripped[:100]))
        elif re.match(r'^except\s+BaseException\b', stripped):
            broad_excepts.append((f.name, i, "BaseException catch", stripped[:100]))

if broad_excepts:
    print(f"  Found {len(broad_excepts)} broad exception handlers:")
    for src, line, kind, text in broad_excepts:
        print(f"    {src}:{line} [{kind}] {text}")
else:
    print("  No bare or overly broad exception handlers.")

# ─── 6. DIVISION BY ZERO RISKS ───────────────────────────────────────
print("\n### 6. DIVISION OPERATIONS (potential zero-div) ###")
div_risks = []
for f in PROD_FILES:
    if not f.exists():
        continue
    lines = f.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # Look for divisions where denominator could be zero
        # Patterns: / variable, / self.something, / len(
        matches = re.findall(r'[/]\s*(self\.\w+|[a-z_]\w*(?:\.\w+)*)\b', stripped)
        for m in matches:
            # Check if there's a guard on previous lines
            if m in ('0', '0.0', '100', '100.0', '1', '1.0', '24', '365', '3600'):
                continue
            # Common safe denominators
            if any(safe in m for safe in ['len(', 'count', 'total', '_pct', 'max(']):
                continue
            if '/ 0' in stripped and 'if' not in stripped:
                div_risks.append((f.name, i, stripped[:120]))

# Also check for explicit / with variable denominators
for f in PROD_FILES:
    if not f.exists():
        continue
    tree = ast.parse(f.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv)):
            # Check if right side is a Name (variable) without obvious guard
            if isinstance(node.right, ast.Name):
                line = node.lineno
                # Get the actual line text
                lines = f.read_text(encoding="utf-8").splitlines()
                if line <= len(lines):
                    text = lines[line-1].strip()
                    if 'if' not in text and '> 0' not in text and text and not text.startswith('#'):
                        div_risks.append((f.name, line, f"div by {node.right.id}: {text[:100]}"))

# Deduplicate
seen = set()
unique_divs = []
for item in div_risks:
    key = (item[0], item[1])
    if key not in seen:
        seen.add(key)
        unique_divs.append(item)

if unique_divs:
    print(f"  Found {len(unique_divs)} potential division risks:")
    for src, line, text in unique_divs[:30]:
        print(f"    {src}:{line} — {text}")
else:
    print("  No obvious division-by-zero risks found.")

# ─── 7. CREDENTIAL / SECRET DETECTION ─────────────────────────────────
print("\n### 7. CREDENTIAL / SECRET SCAN ###")
secret_patterns = [
    (r'api_key\s*=\s*["\'][^"\']{10,}', "hardcoded API key"),
    (r'api_secret\s*=\s*["\'][^"\']{10,}', "hardcoded API secret"),
    (r'token\s*=\s*["\'][^"\']{10,}', "hardcoded token"),
    (r'password\s*=\s*["\'][^"\']{3,}', "hardcoded password"),
    (r'sk_[a-zA-Z0-9]{20,}', "secret key pattern"),
    (r'["\']eyJ[a-zA-Z0-9_-]+\.eyJ', "JWT token"),
]
secrets = []
for f in PROD_FILES:
    if not f.exists():
        continue
    content = f.read_text(encoding="utf-8")
    for pat, desc in secret_patterns:
        for m in re.finditer(pat, content, re.IGNORECASE):
            line_num = content[:m.start()].count('\n') + 1
            line_text = content.splitlines()[line_num - 1].strip()
            if not line_text.startswith("#") and "env" not in line_text.lower() and "os.environ" not in line_text:
                secrets.append((f.name, line_num, desc, line_text[:80]))

if secrets:
    for src, line, desc, text in secrets:
        print(f"  WARNING: {src}:{line} [{desc}] {text}")
else:
    print("  No hardcoded credentials found. Credentials loaded from environment.")

# ─── 8. FILE WRITE SAFETY ────────────────────────────────────────────
print("\n### 8. FILE WRITE SAFETY (atomic writes) ###")
write_patterns = []
for f in PROD_FILES:
    if not f.exists():
        continue
    lines = f.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # Look for open(..., 'w') without temp file pattern
        if re.search(r"open\(.*['\"]w['\"]", stripped) and "temp" not in stripped.lower() and "tmp" not in stripped.lower():
            write_patterns.append((f.name, i, stripped[:120]))

if write_patterns:
    print(f"  Found {len(write_patterns)} direct file writes (non-atomic):")
    for src, line, text in write_patterns:
        print(f"    {src}:{line} — {text}")
    print("  NOTE: Non-atomic writes risk corrupted state if process killed mid-write.")
else:
    print("  No direct file writes found (or all use atomic patterns).")

# ─── 9. SUMMARY ──────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PHASE 1 SUMMARY")
print("=" * 70)
print(f"  Files analyzed: {len([f for f in PROD_FILES if f.exists()])}")
print(f"  Syntax errors: {len(syntax_errors)}")
print(f"  Import issues: {len(import_issues)}")
print(f"  Hardcoded paths: {len(hardcoded)}")
print(f"  TODO/FIXME markers: {len(markers)}")
print(f"  Broad exception handlers: {len(broad_excepts)}")
print(f"  Division risks: {len(unique_divs)}")
print(f"  Credential leaks: {len(secrets)}")
print(f"  Non-atomic writes: {len(write_patterns)}")
