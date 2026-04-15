# V14PM Live Bot — Production Clone Guide
_Version: 1.0 | Date: 2026-04-09 | Status: ACTIVE_
_Reference: `V14PM_SYSTEM_ARCHITECTURE.md` (v1.7) for full system internals._

---

## Purpose

Deploy a **standalone clone** of the V14PM Live trading bot to a production server with a new,
well-funded wallet and API key. The local V14PM Live bot continues running independently — this
is a full duplicate, not a migration.

## Configuration

| Parameter | Value |
|-----------|-------|
| Initial Capital | **$20,000 USDT** |
| Exchange | **Aster DEX Perpetuals** (1x leverage, no liquidation risk) |
| Profile | **High** (unified — same as local bot) |
| Leverage | **1.0x** |
| Scanner Window | **30 days** |
| Coin Universe | **50 coins** (Aster Perps) |
| Tier at $20K | **5 coins**, 75/25 pool split |
| Candle Timeframe | **1h** |
| TP | **1.5%** above weighted avg entry |

---

## Table of Contents

1. [System Overview & Component Map](#1-system-overview--component-map)
2. [Resource Requirements](#2-resource-requirements)
3. [Prerequisites](#3-prerequisites)
4. [Component Inventory — What Gets Cloned](#4-component-inventory--what-gets-cloned)
5. [Server Setup](#5-server-setup)
6. [Code Deployment](#6-code-deployment)
7. [Database Migration](#7-database-migration)
8. [Environment Configuration](#8-environment-configuration)
9. [Systemd Services](#9-systemd-services)
10. [Dashboard & GitHub Pages Sync](#10-dashboard--github-pages-sync)
11. [Telegram Bot Setup](#11-telegram-bot-setup)
12. [Pre-Launch Checklist](#12-pre-launch-checklist)
13. [First Launch](#13-first-launch)
14. [Verification & Smoke Tests](#14-verification--smoke-tests)
15. [Ongoing Operations](#15-ongoing-operations)
16. [Troubleshooting](#16-troubleshooting)

---

## 1. System Overview & Component Map

### What the bot does

V14PM is a portfolio DCA (Dollar-Cost Averaging) trading bot that:
1. Scans 50 coins daily, ranks them by DCA cycle velocity
2. Allocates capital across the top N coins (tier-based: 5 at $20K)
3. Opens grid positions with up to 12 DCA layers per coin
4. Takes profit at 1.5% above weighted average entry
5. Recycles capital into the next opportunity

### Component Dependency Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION SERVER                             │
│                                                                 │
│  ┌──────────────────────┐    ┌──────────────────────────────┐  │
│  │   Candle Collector    │───▶│      candles.db (SQLite)     │  │
│  │  collect_scanner_     │    │  - scanner_candles_1h        │  │
│  │  candles.py (hourly)  │    │  - scanner_candles_daily     │  │
│  └──────────────────────┘    └──────────┬───────────────────┘  │
│                                         │                       │
│  ┌──────────────────────┐               │                       │
│  │   DCA Cycle Scanner   │◀─────────────┘                       │
│  │  v14_cycle_scanner.py │                                      │
│  │  (daily @ 00:05 UTC)  │                                      │
│  └──────────┬───────────┘                                       │
│             │ cycle_scanner.json                                 │
│             ▼                                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              V14PM Live Bot (main process)                │  │
│  │  run_v14_portfolio_live_aster.py                          │  │
│  │                                                           │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │  │
│  │  │ Capital      │  │ Lifecycle    │  │ DCA Engine     │  │  │
│  │  │ Router       │  │ Engine       │  │ (per coin)     │  │  │
│  │  │ (tiers,      │  │ (warmup,     │  │ (grid layers,  │  │  │
│  │  │  allocation) │  │  state mgmt) │  │  TP calc)      │  │  │
│  │  └─────────────┘  └──────────────┘  └────────────────┘  │  │
│  │                                                           │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │  │
│  │  │ Signal Stack │  │ Exchange     │  │ Telegram       │  │  │
│  │  │ ROUTER v2    │  │ Client       │  │ Commands       │  │  │
│  │  │ (phase       │  │ (CCXT/Aster) │  │ (PAUSE/RESUME/ │  │  │
│  │  │  transitions)│  │              │  │  CLOSE/DEPOSIT) │  │  │
│  │  └─────────────┘  └──────┬───────┘  └────────────────┘  │  │
│  └──────────────────────────┼────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────┐   │   ┌───────────────────────────┐  │
│  │  Dashboard Sync       │   │   │  Status/State Files       │  │
│  │  (every 10 min)       │   │   │  - status.json            │  │
│  │  → GitHub Pages       │   │   │  - state.json             │  │
│  └──────────────────────┘   │   │  - trades.csv              │  │
│                              │   │  - capital_ledger.json     │  │
└──────────────────────────────┼───┴───────────────────────────┘  │
                               │                                   │
                    ┌──────────▼──────────┐                        │
                    │   Aster DEX (Perps) │                        │
                    │   Exchange API       │                        │
                    │   Source of Truth     │                        │
                    └─────────────────────┘                        │
                                                                    │
                    ┌─────────────────────┐                        │
                    │   Telegram Bot API   │                        │
                    │   Alerts + Commands  │                        │
                    └─────────────────────┘                        │
                                                                    │
                    ┌─────────────────────┐                        │
                    │   Binance API        │                        │
                    │   Candle backfill    │                        │
                    │   (no auth needed)   │                        │
                    └─────────────────────┘                        │
```

### Data Flow Summary

| Flow | Source | Destination | Frequency | Mechanism |
|------|--------|-------------|-----------|-----------|
| Candle collection | Binance API | candles.db | Every hour | `collect_scanner_candles.py` |
| Scanner ranking | candles.db | cycle_scanner.json | Daily @ 00:05 UTC | `v14_cycle_scanner.py` |
| Coin selection | cycle_scanner.json | Bot memory | Daily @ 00:00 UTC | `_do_rebalance()` |
| Trade signals | DCA engine | Exchange client | Every candle tick | `_execute_action()` |
| Position sync | Aster API | Engine state | Every 65s cycle | `_sync_positions_from_exchange()` |
| Dashboard data | status.json + trades.csv | GitHub Pages | Every 10 min | `sync_dashboard.sh` |
| Alerts | Bot events | Telegram | Real-time | `send_telegram()` |
| Commands | Telegram | Bot | Every 15s poll | `_process_telegram_commands()` |

---

## 2. Resource Requirements

### Minimum Server Specs

| Resource | Minimum | Recommended | Notes |
|----------|---------|-------------|-------|
| **CPU** | 1 vCPU | 2 vCPU | Scanner burst uses ~1 CPU for 30s daily |
| **RAM** | 1 GB | 2 GB | Bot uses ~200MB; scanner peaks ~500MB loading candles.db |
| **Disk** | 2 GB | 5 GB | candles.db = 326MB + logs + state files |
| **Network** | Any | Low-latency to Aster | Bot polls exchange every 65s; not HFT |
| **OS** | Linux (any) | Ubuntu 22.04+ / Debian 12+ | Python 3.12 required |
| **Uptime** | 99%+ | 99.9%+ | Resting TP orders survive bot downtime |

### Estimated Costs (reference)

| Tier | Monthly | Example |
|------|---------|---------|
| Budget | $5–10 | Hetzner CX22, DigitalOcean basic |
| Recommended | $10–20 | 2 vCPU / 2GB RAM VPS |
| Premium | $20–40 | Dedicated vCPU, NVMe storage |

> **Note:** The bot is not latency-sensitive. It trades on 1h candles and polls the exchange
> every 65 seconds. A $5/mo VPS is sufficient. Resting TP limit orders on Aster mean the
> exchange handles fills even if the bot is briefly offline.

---

## 3. Prerequisites

Before starting deployment:

- [ ] **Production server** provisioned with SSH access
- [ ] **Python 3.12+** available (or will install in §5)
- [ ] **New Aster DEX wallet** created with **$20,000 USDT** deposited
- [ ] **New Aster API key + secret** generated for the wallet (trade permissions)
- [ ] **Telegram bot token** — can reuse existing `@GeeGee_Claw_bot` or create a new bot
- [ ] **Telegram chat ID** — Brett's chat ID: use existing or create dedicated command chat
- [ ] **GitHub PAT** (optional) — only needed if dashboard syncs to GitHub Pages
- [ ] **Git** installed on server (for dashboard sync and code deployment)

---

## 4. Component Inventory — What Gets Cloned

### Core Bot Code (required)

| File | Role | Size |
|------|------|------|
| `trading/spot/run_v14_portfolio_live_aster.py` | **Main bot** — portfolio manager, exchange interface, Telegram commands | 132KB |
| `trading/spot/v14_lifecycle_engine.py` | Lifecycle engine — state management, warmup, action dispatch | 41KB |
| `trading/spot/engine/v14_dca_engine.py` | DCA engine — grid layers, TP calculation, phase machine | 40KB |
| `trading/spot/v14_capital_manager.py` | Capital router — tier allocation, pool splits, hysteresis | 25KB |
| `trading/spot/exchange_client.py` | Exchange abstraction — CCXT wrapper for Aster/Hyperliquid | 10KB |
| `trading/spot/cfgi_client.py` | Fear & Greed Index client (optional, regime context) | 11KB |
| `trading/spot/coin_scanner.py` | Coin universe and metadata | 20KB |

### Signal Stack (required — loaded by DCA engine)

| File | Role | Size |
|------|------|------|
| `trading/spot/engine/v13_router_engine_v2.py` | ROUTER v2 — phase transition signals | 26KB |
| `trading/spot/engine/v13_signals.py` | Technical indicators (RSI, MACD, Bollinger, etc.) | 24KB |
| `trading/spot/engine/v13_router_engine_v1.py` | ROUTER v1 fallback | 44KB |
| `trading/spot/engine/v13_phase_backtest_v8.py` | Phase backtest engine (used by signal stack) | 45KB |

### Scanner & Data Pipeline (required)

| File | Role | Size |
|------|------|------|
| `trading/spot/v14_cycle_scanner.py` | DCA cycle velocity scanner — ranks coins daily | 34KB |
| `trading/spot/collect_scanner_candles.py` | Hourly candle collector — Binance → candles.db | 10KB |
| `trading/spot/backfill_binance.py` | Historical candle backfill (initial setup only) | 13KB |
| `trading/spot/engine/build_daily_candles.py` | 1h → daily resampling for signal stack | 7KB |
| `trading/spot/generate_daily_equity.py` | Daily equity snapshot for dashboard | 7KB |
| `trading/spot/resample_daily.py` | Daily candle resampling utility | 5KB |

### Dashboard (required for monitoring)

| File | Role | Size |
|------|------|------|
| `docs/dashboardV14PM.html` | V14PM dashboard — single HTML file, reads from data files | 80KB |
| `docs/data/v14-pm/status.json` | Dashboard data — written by bot | ~4KB |
| `docs/data/v14-pm/trades.csv` | Dashboard data — written by bot | ~10KB |
| `docs/data/v14/cycle_scanner.json` | Scanner output — written by scanner | ~50KB |

### State & Config Files (created at first launch)

| File | Role | Created By |
|------|------|------------|
| `trading/spot/live/v14pm/state.json` | Engine state — positions, coins, allocated capital | Bot (every save cycle) |
| `trading/spot/live/v14pm/status.json` | Health status — equity, PnL, coin data (for dashboard) | Bot (every cycle) |
| `trading/spot/live/v14pm/trades.csv` | Completed deal log | Bot (on TP fill) |
| `trading/spot/live/v14pm/capital_ledger.json` | Capital transaction log (deposits, withdrawals) | Bot (on capital change) |
| `trading/spot/live/v14pm/bot.log` | Runtime log | Bot |
| `trading/spot/live/v14pm/bot.lock` | PID lock file | Bot |
| `trading/spot/data/candles.db` | SQLite database — all candle data | Collector + backfill |

### Package Files

| File | Role |
|------|------|
| `trading/__init__.py` | Python package marker |
| `trading/spot/__init__.py` | Python package marker |
| `trading/spot/engine/__init__.py` | Python package marker |
| `requirements.txt` | Python dependencies (ccxt, numpy, pandas) |

### NOT Cloned (stay on local machine)

| Component | Why |
|-----------|-----|
| Paper bots (V14, V14PM Paper) | Demo accounts — continue on local machine |
| `run_v14_live_aster.py` (legacy single-coin) | Retired 2026-03-19 |
| `run_v14etf_paper.py` | Retired 2026-03-17 |
| OpenClaw agent / heartbeat / cron | Local orchestration — not part of trading system |
| Windows scheduled tasks | Replaced by systemd on Linux |

---

## 5. Server Setup

### 5.1 System Packages

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12+ and essentials
sudo apt install -y python3.12 python3.12-venv python3-pip git sqlite3 curl

# Verify
python3.12 --version   # Should be 3.12.x
git --version
sqlite3 --version
```

### 5.2 Create Application User

```bash
# Create dedicated user (no sudo, no shell login needed for service)
sudo useradd -r -m -d /opt/ait -s /bin/bash ait
sudo passwd -l ait  # Lock password (SSH key or su only)
```

### 5.3 Directory Structure

```bash
sudo mkdir -p /opt/ait
sudo chown ait:ait /opt/ait

# As ait user:
sudo -u ait mkdir -p /opt/ait/{trading/spot/{live/v14pm,data,engine},docs/data/{v14,v14-pm},logs}
```

---

## 6. Code Deployment

### 6.1 Clone from Git

```bash
# As ait user
sudo -u ait bash -c '
cd /opt/ait
git clone https://github.com/<your-repo>/ait.git .
# Or copy from local machine via scp/rsync
'
```

### 6.2 Alternative: rsync from Local Machine

```bash
# From local machine (PowerShell or bash)
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='trading/spot/live/*/bot.log' \
  --exclude='trading/spot/live/*/state.json' \
  --exclude='trading/spot/live/*/status.json' \
  --exclude='trading/spot/live/*/trades.csv' \
  --exclude='trading/spot/live/*/capital_ledger.json' \
  --exclude='trading/spot/paper' \
  --exclude='node_modules' \
  --exclude='.openclaw' \
  C:/Users/Never/.openclaw/workspace/ user@production-server:/opt/ait/
```

> **Important:** Do NOT copy state.json, trades.csv, or capital_ledger.json from the local
> bot. The production clone starts fresh with its own state.

### 6.3 Install Python Dependencies

```bash
sudo -u ait bash -c '
cd /opt/ait
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
'
```

### 6.4 Verify Import Chain

```bash
sudo -u ait bash -c '
cd /opt/ait
source venv/bin/activate
python -c "
from trading.spot.run_v14_portfolio_live_aster import V14PortfolioLiveBot
from trading.spot.v14_capital_manager import CapitalRouter
from trading.spot.v14_lifecycle_engine import V14LifecycleEngine
from trading.spot.exchange_client import SpotExchangeClient
from trading.spot.v14_cycle_scanner import V14CycleScanner
print(\"All imports OK\")
"
'
```

---

## 7. Database Migration

The candle database provides the historical data the scanner and signal stack need.

### 7.1 Copy candles.db

```bash
# From local machine
scp C:/Users/Never/.openclaw/workspace/trading/spot/data/candles.db \
  user@production-server:/opt/ait/trading/spot/data/candles.db

# Set ownership
sudo chown ait:ait /opt/ait/trading/spot/data/candles.db
```

**Current size:** ~326 MB

### 7.2 Verify Database

```bash
sudo -u ait bash -c '
cd /opt/ait
sqlite3 trading/spot/data/candles.db "
  SELECT name FROM sqlite_master WHERE type=\"table\";
  SELECT COUNT(*) as rows FROM scanner_candles_1h;
  SELECT MIN(timestamp), MAX(timestamp) FROM scanner_candles_1h;
"
'
```

Expected tables: `scanner_candles_1h`, `scanner_candles_daily`

### 7.3 Initial Scanner Run

After the database is in place, run the scanner once to generate `cycle_scanner.json`:

```bash
sudo -u ait bash -c '
cd /opt/ait
source venv/bin/activate
python -u -m trading.spot.v14_cycle_scanner
'
```

This creates `docs/data/v14/cycle_scanner.json` which the bot reads at daily rebalance.

---

## 8. Environment Configuration

### 8.1 Create .env File

```bash
sudo -u ait bash -c 'cat > /opt/ait/trading/spot/live/v14pm/.env << "EOF"
# V14PM Production Clone — Aster DEX Perpetuals
# Created: 2026-04-09

# -- Exchange: Aster DEX (Perps) -----------------------------------------------
ASTER_API_KEY=<new_wallet_api_key>
ASTER_API_SECRET=<new_wallet_api_secret>

# -- Telegram Notifications ----------------------------------------------------
AIT_TG_TOKEN=<telegram_bot_token>
AIT_TG_CHAT_ID=<telegram_chat_id>

# -- Fear & Greed Index (optional) ---------------------------------------------
# CFGI_API_KEY=<cfgi_api_key>

# -- Database -------------------------------------------------------------------
AIT_CANDLES_DB=/opt/ait/trading/spot/data/candles.db

# -- Scanner Data ---------------------------------------------------------------
AIT_SCANNER_JSON=/opt/ait/docs/data/v14/cycle_scanner.json
EOF
chmod 600 /opt/ait/trading/spot/live/v14pm/.env
'
```

### 8.2 Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `ASTER_API_KEY` | ✅ | Aster DEX wallet API key |
| `ASTER_API_SECRET` | ✅ | Aster DEX wallet API secret |
| `AIT_TG_TOKEN` | ✅ | Telegram bot token for alerts + commands |
| `AIT_TG_CHAT_ID` | ✅ | Telegram chat ID for authorized commands |
| `AIT_CANDLES_DB` | ✅ | Absolute path to candles.db |
| `AIT_SCANNER_JSON` | ✅ | Absolute path to cycle_scanner.json |
| `CFGI_API_KEY` | Optional | Fear & Greed Index API (regime context) |
| `AIT_GITHUB_PAT` | Optional | GitHub PAT for dashboard sync |

---

## 9. Systemd Services

### 9.1 V14PM Live Bot Service

```bash
sudo tee /etc/systemd/system/v14pm-live.service << 'EOF'
[Unit]
Description=V14PM Live Trading Bot (Aster Perps)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ait
Group=ait
WorkingDirectory=/opt/ait
EnvironmentFile=/opt/ait/trading/spot/live/v14pm/.env
ExecStart=/opt/ait/venv/bin/python -B -u -m trading.spot.run_v14_portfolio_live_aster \
  --capital 20000 --confirm --skip-backfill
Restart=on-failure
RestartSec=30
StandardOutput=append:/opt/ait/trading/spot/live/v14pm/bot.log
StandardError=append:/opt/ait/trading/spot/live/v14pm/bot_err.log

# Security hardening
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=/opt/ait

[Install]
WantedBy=multi-user.target
EOF
```

### 9.2 Candle Collector (Hourly)

```bash
sudo tee /etc/systemd/system/ait-candle-collector.service << 'EOF'
[Unit]
Description=AIT Candle Collector (hourly)
After=network-online.target

[Service]
Type=oneshot
User=ait
Group=ait
WorkingDirectory=/opt/ait
EnvironmentFile=/opt/ait/trading/spot/live/v14pm/.env
ExecStart=/opt/ait/venv/bin/python -u -m trading.spot.collect_scanner_candles
StandardOutput=append:/opt/ait/logs/candle_collector.log
StandardError=append:/opt/ait/logs/candle_collector_err.log
EOF

sudo tee /etc/systemd/system/ait-candle-collector.timer << 'EOF'
[Unit]
Description=Run candle collector hourly at :05

[Timer]
OnCalendar=*:05:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
```

### 9.3 DCA Cycle Scanner (Daily)

```bash
sudo tee /etc/systemd/system/ait-scanner.service << 'EOF'
[Unit]
Description=AIT DCA Cycle Scanner (daily)
After=network-online.target

[Service]
Type=oneshot
User=ait
Group=ait
WorkingDirectory=/opt/ait
EnvironmentFile=/opt/ait/trading/spot/live/v14pm/.env
ExecStart=/opt/ait/venv/bin/python -u -m trading.spot.v14_cycle_scanner
StandardOutput=append:/opt/ait/logs/scanner.log
StandardError=append:/opt/ait/logs/scanner_err.log
EOF

sudo tee /etc/systemd/system/ait-scanner.timer << 'EOF'
[Unit]
Description=Run DCA scanner daily at 00:05 UTC

[Timer]
OnCalendar=*-*-* 00:05:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
```

### 9.4 Dashboard Sync (Every 10 Minutes)

```bash
sudo tee /etc/systemd/system/ait-dashboard-sync.service << 'EOF'
[Unit]
Description=AIT Dashboard GitHub Pages Sync
After=network-online.target

[Service]
Type=oneshot
User=ait
Group=ait
WorkingDirectory=/opt/ait
Environment=AIT_GITHUB_PAT=<github_pat>
ExecStart=/opt/ait/scripts/sync_dashboard.sh
StandardOutput=append:/opt/ait/logs/dashboard_sync.log
StandardError=append:/opt/ait/logs/dashboard_sync_err.log
EOF

sudo tee /etc/systemd/system/ait-dashboard-sync.timer << 'EOF'
[Unit]
Description=Sync dashboard to GitHub Pages every 10 min

[Timer]
OnCalendar=*:00/10:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
```

### 9.5 Dashboard Sync Script (Linux)

Create `/opt/ait/scripts/sync_dashboard.sh`:

```bash
#!/bin/bash
# Dashboard sync — pushes status.json, trades.csv, cycle_scanner.json to GitHub Pages
set -euo pipefail

REPO_URL="https://${AIT_GITHUB_PAT}@github.com/<your-repo>/ait.git"
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

cd "$TEMP_DIR"
git clone --depth 1 --branch main "$REPO_URL" repo
cd repo

# Copy dashboard data files
cp /opt/ait/trading/spot/live/v14pm/status.json docs/data/v14-pm/status.json 2>/dev/null || true
cp /opt/ait/trading/spot/live/v14pm/trades.csv docs/data/v14-pm/trades.csv 2>/dev/null || true
cp /opt/ait/docs/data/v14/cycle_scanner.json docs/data/v14/cycle_scanner.json 2>/dev/null || true

# Generate daily equity snapshot
/opt/ait/venv/bin/python /opt/ait/trading/spot/generate_daily_equity.py 2>/dev/null || true

# Ensure .nojekyll exists
touch docs/.nojekyll

# Commit and push if changed
git add docs/
if git diff --cached --quiet; then
  echo "No changes"
else
  git -c user.name="AIT Bot" -c user.email="bot@ait" commit -m "dashboard sync $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git push
  echo "Pushed"
fi
```

```bash
chmod +x /opt/ait/scripts/sync_dashboard.sh
```

### 9.6 Enable All Services

```bash
sudo systemctl daemon-reload

# Enable timers (start on boot)
sudo systemctl enable --now ait-candle-collector.timer
sudo systemctl enable --now ait-scanner.timer
sudo systemctl enable --now ait-dashboard-sync.timer

# DO NOT enable the bot yet — see §13 First Launch
```

---

## 10. Dashboard & GitHub Pages

The dashboard is a single HTML file that reads JSON/CSV data from GitHub Pages.

### Option A: Shared GitHub Pages (same repo as local bot)

Both local and production bots write to different data paths:
- Local: `docs/data/v14-pm/` (existing)
- Production: `docs/data/v14-pm-prod/` (new path)

Modify the production bot's status.json output path or create a separate dashboard HTML
pointing to the production data directory.

### Option B: Separate GitHub Repo

Create a new GitHub repo for the production dashboard. Simpler isolation.

### Dashboard File

Copy `docs/dashboardV14PM.html` to the production server. The HTML loads data via fetch()
from relative paths — update the data path if using Option A.

---

## 11. Telegram Bot Setup

### Option A: Reuse Existing Bot (@GeeGee_Claw_bot)

Both local and production bots can share the same Telegram bot if they use **different
`TG_PREFIX` values** (local uses `[V14-PM]`, production could use `[V14-PM-PROD]`).

However, both bots poll the same chat — **commands sent by Brett would be processed by
BOTH bots**. This is dangerous (a CLOSE ALL would close on both).

### Option B: Separate Telegram Bot (recommended)

1. Create a new bot via @BotFather on Telegram
2. Get the token
3. Start a chat with the new bot, send `/start`
4. Use the new token and chat ID in the production `.env`

This isolates commands completely — PAUSE on one bot doesn't affect the other.

> **Recommendation: Option B.** Two trading bots sharing one Telegram command interface is a
> foot-gun. Create a separate bot for production.

---

## 12. Pre-Launch Checklist

### Exchange Verification

- [ ] New wallet has $20,000 USDT on Aster Perps
- [ ] API key has trade permissions
- [ ] Test API connectivity:
  ```bash
  sudo -u ait bash -c '
  cd /opt/ait && source venv/bin/activate
  python -c "
  from trading.spot.exchange_client import SpotExchangeClient
  c = SpotExchangeClient()
  c.connect(\"aster\")
  bal = c.fetch_balance()
  print(f\"Balance: {bal} USDT\")
  pos = c.fetch_open_positions()
  print(f\"Open positions: {len(pos)}\")
  "
  '
  ```

### Database Verification

- [ ] candles.db exists at `/opt/ait/trading/spot/data/candles.db`
- [ ] `scanner_candles_1h` table has recent data (within 24h)
- [ ] `cycle_scanner.json` exists and was generated after DB copy

### Telegram Verification

- [ ] Bot token is valid (test with curl)
- [ ] Chat ID is correct
- [ ] Test send:
  ```bash
  curl -s "https://api.telegram.org/bot<TOKEN>/sendMessage" \
    -d chat_id=<CHAT_ID> -d text="V14PM Production Clone - test message"
  ```

### Code Verification

- [ ] All imports pass (§6.4)
- [ ] Python 3.12+ confirmed
- [ ] requirements.txt installed (ccxt, numpy, pandas)
- [ ] `__init__.py` files exist in trading/, trading/spot/, trading/spot/engine/

### Service Verification

- [ ] Candle collector timer active: `systemctl status ait-candle-collector.timer`
- [ ] Scanner timer active: `systemctl status ait-scanner.timer`
- [ ] Dashboard sync timer active: `systemctl status ait-dashboard-sync.timer`

---

## 13. First Launch

### 13.1 Dry Run (Recommended)

First, start the bot manually to watch the output:

```bash
sudo -u ait bash -c '
cd /opt/ait
source venv/bin/activate
source trading/spot/live/v14pm/.env
python -B -u -m trading.spot.run_v14_portfolio_live_aster \
  --capital 20000 --confirm --skip-backfill
'
```

Watch for:
- `Restored state: bot_state=RUNNING` — should NOT appear (fresh start)
- `CapitalRouter: $20,000.00 equity` — confirms capital recognition
- `Tier coin cap: 5 coins` — confirms $20K tier
- `Pool split: 75.0% active / 25.0% reserve` — confirms $20K split
- Exchange balance fetched successfully
- Scanner data loaded
- First candle tick processes without errors

Press Ctrl+C after confirming startup is clean.

### 13.2 Production Start

```bash
sudo systemctl enable --now v14pm-live.service

# Verify
sudo systemctl status v14pm-live.service
journalctl -u v14pm-live.service -f  # Follow logs
```

### 13.3 What Happens at First Launch

1. Bot starts with `--capital 20000` and `--skip-backfill`
2. No state.json exists → fresh start, no position restore
3. Candle collector has been running hourly → candles.db is current
4. Scanner has run → `cycle_scanner.json` has ranked coins
5. At the first midnight UTC rebalance, the bot:
   - Reads scanner rankings
   - Selects top 5 coins (at $20K tier)
   - Allocates $3,000 per coin (75% of $20K / 5)
   - Creates engines and begins trading
6. Before midnight, the bot is "warm but idle" — processing candles, building signal context

> **Expect no trades until the first midnight UTC rebalance.** The bot needs the daily
> rebalance cycle to select and allocate coins.

---

## 14. Verification & Smoke Tests

### After First Midnight Rebalance

- [ ] `state.json` has coins with `allocated_capital > 0`
- [ ] `status.json` shows `running=true`, correct equity, coin data
- [ ] Telegram received rebalance notification
- [ ] Dashboard shows active coins (if sync is running)

### After First Trade

- [ ] `trades.csv` has at least one entry
- [ ] Exchange shows open position(s) with TP limit orders
- [ ] `capital_ledger.json` shows seed capital entry
- [ ] PnL in status.json matches exchange positions

### Ongoing Health Checks

```bash
# Bot running?
systemctl is-active v14pm-live.service

# Status file fresh? (should be < 2 min old)
stat /opt/ait/trading/spot/live/v14pm/status.json

# Exchange positions match status?
sudo -u ait bash -c '
cd /opt/ait && source venv/bin/activate
python -c "
import json
with open(\"trading/spot/live/v14pm/status.json\") as f:
    s = json.load(f)
print(f\"Equity: {s[\"equity\"]}, Running: {s[\"running\"]}\")
for sym, c in s.get(\"coins\", {}).items():
    if c.get(\"invested\", 0) > 0:
        print(f\"  {sym}: inv={c[\"invested\"]:.2f} upnl={c[\"unrealized_pnl\"]:.2f}\")
"
'
```

---

## 15. Ongoing Operations

### Log Rotation

```bash
sudo tee /etc/logrotate.d/ait << 'EOF'
/opt/ait/trading/spot/live/v14pm/bot.log
/opt/ait/trading/spot/live/v14pm/bot_err.log
/opt/ait/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF
```

### Updating Code

```bash
# Stop bot
sudo systemctl stop v14pm-live.service

# Update code (git pull or rsync)
sudo -u ait bash -c 'cd /opt/ait && git pull'

# Restart
sudo systemctl start v14pm-live.service

# Verify
sudo systemctl status v14pm-live.service
tail -20 /opt/ait/trading/spot/live/v14pm/bot.log
```

> **State survives restarts.** The bot saves state.json every cycle. On restart it restores
> positions, TP orders, and allocated capital. No trades are lost.

### Capital Changes (via Telegram)

Send commands to the production bot's Telegram chat:
- `DEPOSIT` — bot auto-detects new USDT deposited to exchange
- `WITHDRAW <amount>` — records a withdrawal in the capital ledger
- `CAPITAL` — shows current capital, equity, and tier

### Emergency Commands (via Telegram)

- `PAUSE` — stops all new trades, existing TP orders stay active on exchange
- `PAUSE <COIN>` — pauses a specific coin
- `RESUME` / `RESUME <COIN>` — resume trading
- `CLOSE <COIN>` — market-sell a position immediately
- `CLOSE ALL` — close everything and enter wind-down

---

## 16. Troubleshooting

### Bot won't start

```bash
# Check logs
journalctl -u v14pm-live.service -n 50
cat /opt/ait/trading/spot/live/v14pm/bot_err.log

# Common causes:
# - Missing .env file or env vars not loaded
# - candles.db not found (check AIT_CANDLES_DB path)
# - Import error (missing dependency — run pip install -r requirements.txt)
# - bot.lock exists from crashed process (delete it)
```

### "Insufficient USDT" alerts

The bot has insufficient free USDT to open new positions. Causes:
- All capital is allocated to open positions
- Drawdown has eaten into available capital
- Need to deposit more USDT or wait for TP fills

Alert is throttled to once per coin per hour. Not an error — informational.

### "ReduceOnly Order is rejected"

The bot tried to sell a coin with no open position on the exchange. Fixed in v1.7 with
sell guard (GAP-14). If you see this on the production clone, you're running old code.

### Exchange API errors

```bash
# Test connectivity
sudo -u ait bash -c '
cd /opt/ait && source venv/bin/activate
python -c "
from trading.spot.exchange_client import SpotExchangeClient
c = SpotExchangeClient()
c.connect(\"aster\")
print(\"Balance:\", c.fetch_balance())
"
'
```

### Scanner data stale

```bash
# Check when scanner last ran
ls -la /opt/ait/docs/data/v14/cycle_scanner.json
systemctl status ait-scanner.timer
systemctl status ait-candle-collector.timer

# Run manually
sudo -u ait bash -c 'cd /opt/ait && source venv/bin/activate && python -u -m trading.spot.v14_cycle_scanner'
```

---

## Appendix A: At-a-Glance — $20K Tier Configuration

| Parameter | Value at $20K |
|-----------|---------------|
| Max coins | 5 |
| Active pool | 75% ($15,000) |
| Reserve pool | 25% ($5,000) |
| Per-coin allocation | ~$3,000 |
| Grid layers | Up to 12 |
| Base order | 40% of allocation ($1,200) |
| TP target | 1.5% above weighted avg entry |
| Hysteresis | 5% (won't downgrade to 4-coin tier until equity drops below $19,000) |

## Appendix B: Tier Table Reference

| Equity | Max Coins | Active Pool | Reserve Pool |
|--------|-----------|-------------|--------------|
| $100K+ | 10 | 75% | 25% |
| $20K–$100K | 5 | 75% | 25% |
| $10K–$20K | 5 | 80% | 20% |
| $5K–$10K | 5 | 90% | 10% |
| $3K–$5K | 4 | 90% | 10% |
| $100–$3K | 3 | 90% | 10% |

## Appendix C: Files Checklist

```
/opt/ait/
├── requirements.txt
├── venv/                          # Python virtual environment
├── scripts/
│   └── sync_dashboard.sh         # Dashboard sync script
├── trading/
│   ├── __init__.py
│   └── spot/
│       ├── __init__.py
│       ├── run_v14_portfolio_live_aster.py    # Main bot
│       ├── v14_lifecycle_engine.py            # Lifecycle engine
│       ├── v14_capital_manager.py             # Capital router
│       ├── exchange_client.py                 # Exchange abstraction
│       ├── cfgi_client.py                     # Fear & Greed
│       ├── coin_scanner.py                    # Coin universe
│       ├── v14_cycle_scanner.py               # DCA scanner
│       ├── collect_scanner_candles.py         # Candle collector
│       ├── backfill_binance.py                # Historical backfill
│       ├── generate_daily_equity.py           # Equity snapshots
│       ├── resample_daily.py                  # Daily resampling
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── v14_dca_engine.py              # DCA engine
│       │   ├── v13_router_engine_v2.py        # ROUTER v2
│       │   ├── v13_signals.py                 # Technical indicators
│       │   ├── v13_router_engine_v1.py        # ROUTER v1 fallback
│       │   ├── v13_phase_backtest_v8.py       # Phase backtest
│       │   └── build_daily_candles.py         # 1h→daily resampling
│       ├── data/
│       │   └── candles.db                     # 326MB SQLite database
│       └── live/
│           └── v14pm/
│               ├── .env                       # Credentials (600 perms)
│               ├── state.json                 # Engine state (auto-created)
│               ├── status.json                # Health status (auto-created)
│               ├── trades.csv                 # Deal log (auto-created)
│               ├── capital_ledger.json         # Capital log (auto-created)
│               ├── bot.log                    # Runtime log
│               └── bot.lock                   # PID lock
└── docs/
    ├── dashboardV14PM.html                    # Dashboard HTML
    ├── .nojekyll                               # GitHub Pages marker
    └── data/
        ├── v14/
        │   └── cycle_scanner.json             # Scanner output
        └── v14-pm/
            ├── status.json                    # Dashboard data
            └── trades.csv                     # Dashboard data
```

---

_Document: V14PM_PRODUCTION_CLONE_GUIDE.md_
_Version: 1.0 | Created: 2026-04-09_
_Author: Gee Gee_
_Reference: V14PM_SYSTEM_ARCHITECTURE.md v1.7_
