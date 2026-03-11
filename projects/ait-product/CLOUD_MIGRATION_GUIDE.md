# Adaptive Intelligence Trading — Cloud Migration Guide
_V14PM Live Trading Deployment_
_Version: 1.2 | Date: 2026-03-10 | Status: Draft — Pending Decisions_

**Reference:** See `V14PM_SYSTEM_ARCHITECTURE.md` for full system internals.

---

## Decisions Required Before Execution

The following must be decided before a systems engineer can complete this guide.
Everything else is fully specified.

| # | Decision | Status | Notes |
|---|----------|--------|-------|
| D1 | Cloud provider | ⚠️ PENDING | Recommendations in Section 2 |
| D2 | Instance size / budget | ⚠️ PENDING | Recommendations in Section 2 |
| D3 | Initial live capital (USD) | ⚠️ PENDING | Affects equity tier and coin cap |
| D4 | Hyperliquid mainnet API key | ⚠️ PENDING | Must be created — see Section 4.2 |
| D5 | Server region | ⚠️ PENDING | Closest to Hyperliquid infra = lowest latency |
| D6 | Paper bots migrate or stay on Windows? | ⚠️ PENDING | Recommendation: stay on Windows (demo continuity) |

---

## Table of Contents

1. [Scope & What Moves Where](#1-scope--what-moves-where)
2. [Cloud Provider & Sizing Recommendations](#2-cloud-provider--sizing-recommendations)
3. [Server Provisioning](#3-server-provisioning)
4. [Hyperliquid API Key Setup](#4-hyperliquid-api-key-setup)
5. [Application Deployment](#5-application-deployment)
6. [Database Migration](#6-database-migration)
7. [Environment Configuration](#7-environment-configuration)
8. [Systemd Services & Timers](#8-systemd-services--timers)
9. [GitHub Pages Sync (Linux)](#9-github-pages-sync-linux)
10. [Pre-Launch Checklist](#10-pre-launch-checklist)
11. [Live Trading Cutover](#11-live-trading-cutover)
12. [Ongoing Operations](#12-ongoing-operations)
13. [Rollback Plan](#13-rollback-plan)

---

## 1. Scope & What Moves Where

### What migrates to cloud

| Component | Cloud Role |
|-----------|-----------|
| V14PM live bot (`run_v14_portfolio_live.py`) | Primary: 24/7 live trading process |
| Candle collector (`run_candle_collector.sh`) | Hourly: keeps candles.db fresh |
| DCA Cycle Scanner (`v14_cycle_scanner.py`) | Daily: refreshes capital rotation rankings |
| Dashboard sync | Every 10 min: pushes data to GitHub Pages |
| candles.db | Migrated from Windows; primary data store on cloud |

### What stays on Windows

| Component | Reason |
|-----------|--------|
| V14 Paper Bot | Customer demo — continuous runtime, familiar environment |
| V14-ETF Paper Bot | Customer demo — same |
| V14PM Paper Bot | Customer demo benchmark — compare against live |
| V14 Live (Aster) | Aster DEX is a different exchange; no cloud benefit |

The Windows paper bots continue pulling candle data from their local candles.db
(updated by their own AIT_CandleCollector task). The cloud server maintains a
**separate independent candles.db** for the live bot.

---

## 2. Cloud Provider & Sizing Recommendations

### 2.1 System Requirements

Based on measured production resource usage:

| Resource | Measured | Recommended Minimum | Comfortable |
|----------|----------|-------------------|-------------|
| RAM | 4 × ~20 MB per process | 1 GB | **2 GB** |
| CPU | Low (signal calc on daily candles) | 1 vCPU | **2 vCPU** |
| Disk | candles.db 214 MB, grows ~30 MB/year | 10 GB | **20 GB SSD** |
| Network | Low (REST polling + order placement) | 100 Mbps | Any |

The system is **not** computationally intensive. It is I/O-bound (SQLite reads,
HTTP to Hyperliquid). An entry-level cloud instance is sufficient.

### 2.2 Provider Comparison

> **Decision D1 & D2** — Choose provider and instance tier from this table.

| Provider | Instance | Specs | Price/mo | Notes |
|----------|----------|-------|----------|-------|
| **Hetzner** | CX22 | 2 vCPU, 4 GB RAM, 40 GB NVMe | ~$5 | Best value; EU datacenters |
| **Hetzner** | CX32 | 4 vCPU, 8 GB RAM, 80 GB NVMe | ~$9 | Headroom for future growth |
| DigitalOcean | Basic $12 | 2 vCPU, 2 GB RAM, 50 GB SSD | $12 | Good UX, US/EU regions |
| Vultr | High Freq $12 | 2 vCPU, 4 GB RAM, 80 GB NVMe | $12 | Strong US/EU options |
| AWS | t3.small | 2 vCPU, 2 GB RAM | ~$17 | Overkill complexity; skip |

**Recommendation:** Hetzner CX22 for cost, or DigitalOcean/Vultr if US region is
preferred. All run Ubuntu 22.04 LTS identically.

### 2.3 Region Selection

Hyperliquid validators are geographically distributed. For live trading, latency
matters more for order placement than for candle collection. US East or EU West
are both fine for a DCA system with ~1-hour decision cycles (not HFT).

**Recommendation:** US East (New York / Virginia) or EU West (Frankfurt / Amsterdam)
based on your preference.

---

## 3. Server Provisioning

> Replace `[PROVIDER]`, `[INSTANCE_TYPE]`, `[REGION]` with your chosen values (D1, D2, D5).

### 3.1 Create Instance

```bash
# Via provider web console or CLI:
# - OS: Ubuntu 22.04 LTS
# - Instance: [INSTANCE_TYPE]
# - Region: [REGION]
# - SSH Key: add your public key at creation time
# - Firewall: allow SSH (22) inbound only — no inbound ports needed for the bot
```

### 3.2 Initial Server Setup

```bash
# Connect
ssh root@[SERVER_IP]

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y git python3.12 python3.12-venv python3-pip sqlite3 htop tmux

# Verify Python version
python3.12 --version    # Should show 3.12.x

# Create app user (never run the bot as root)
useradd -m -s /bin/bash ait
# Add your SSH key to ait user too
mkdir -p /home/ait/.ssh
cp ~/.ssh/authorized_keys /home/ait/.ssh/
chown -R ait:ait /home/ait/.ssh
chmod 700 /home/ait/.ssh && chmod 600 /home/ait/.ssh/authorized_keys
```

### 3.3 Configure Firewall

```bash
# UFW — allow SSH only; all outbound permitted (bot connects out to Hyperliquid + GitHub)
ufw allow OpenSSH
ufw enable
ufw status
```

---

## 4. Hyperliquid API Key Setup

> **Decision D4** — Complete before any deployment steps.

### 4.1 How Hyperliquid API Keys Work

Hyperliquid uses **API Wallets** — a separate keypair authorized to trade on behalf
of your main account. Your real funds stay in your main wallet; the API wallet can
place/cancel orders but cannot withdraw.

**Never put your main wallet private key on a server.**

### 4.2 Creating an API Wallet

1. Go to: https://app.hyperliquid.xyz/settings/api
2. Click **"Generate API Wallet"**
3. Save the output — you will see:
   - **API Wallet Address** → this is your `HYPERLIQUID_API_KEY`
   - **API Wallet Private Key** → this is your `HYPERLIQUID_API_SECRET`
4. Authorize the API wallet to trade on your account (confirm in the UI)
5. **Store these securely** — the private key is shown only once

### 4.3 Security Notes

- The API wallet private key is what an attacker needs to place trades
- It **cannot withdraw funds** from your account — this limits exposure
- Do not commit `.env` to git (`.gitignore` already excludes it)
- Rotate the key if you suspect compromise — just generate a new API wallet

---

## 5. Application Deployment

### 5.1 Clone Repository

```bash
su - ait
cd /home/ait

# Clone the repo
git clone git@github.com:halo-effects/adaptive-intelligence-trading.git ait
cd ait

# Or via HTTPS if no deploy key:
git clone https://github.com/halo-effects/adaptive-intelligence-trading.git ait
```

### 5.2 Python Virtual Environment

```bash
cd /home/ait/ait

# Create venv
python3.12 -m venv .venv
source .venv/bin/activate

# Install production dependencies (only 3 packages)
pip install -r trading/requirements.txt

# Verify
python -c "import ccxt, numpy, pandas; print('Dependencies OK')"
```

### 5.3 Verify All Imports

```bash
cd /home/ait/ait
source .venv/bin/activate

python -c "
from trading.spot.v14_lifecycle_engine import V14LifecycleEngine, V14_PROFILES
from trading.spot.v14_capital_manager import CapitalRouter
from trading.spot.exchange_client import SpotExchangeClient
from trading.spot.cfgi_client import CFGIClient
from trading.spot.incident_schema import create_incident_report
from trading.spot.coin_scanner import ALL_TOKENS
from trading.spot.daily_collector import run_collector
from trading.spot.v14_cycle_scanner import *
print('ALL IMPORTS OK')
"
```

All 8 imports must pass before proceeding.

### 5.4 Create Live Bot Runner

> `run_v14_portfolio_live.py` must be created. It is the live-trading equivalent
> of `run_v14_portfolio_paper.py` with real order execution enabled.

**To create it:** Copy `run_v14_portfolio_paper.py` as the starting point and:
1. Remove paper-mode simulation logic (TradeTracker is replaced by exchange fills)
2. Enable `SpotExchangeClient` with `paper=False`
3. Add `--confirm` flag requirement (safety gate — refuses to trade without it)
4. Add extra logging for real order fills (price, amount, exchange order ID)
5. Write a `--dry-run` mode that validates connectivity without placing orders
6. **Keep state persistence** (`_save_state` / `_load_state` / `engine_state.json`) —
   this is critical for restart recovery on the cloud server
7. Add exchange balance reconciliation on startup — compare engine positions
   vs real Hyperliquid positions, log drift, abort if mismatch > threshold
8. PID lock is **not needed** — systemd guarantees single instance.
   Remove the `_acquire_pid_lock()` / `_release_pid_lock()` code.
9. **Equity from exchange API:** For live trading, compute equity as
   `USDT balance + (position value at current price)` from exchange API,
   not from engine internals. See `run_v14_live_aster.py` for reference
   implementation (§6.3.1 of Architecture doc).
10. **CSV-as-truth for realized PnL:** The `_write_status()` method must always
    read `trades.csv` and use its PnL sum as `total_realized_pnl`. Engine counters
    drift on restart. This is already implemented in all four current runners.
11. **`--fresh` must call `tracker.load_existing()`** to prevent `save_csv()` from
    overwriting trade history with an empty file.

This step is a development task — flag for completion before cutover.

---

## 6. Database Migration

### 6.1 Copy candles.db from Windows

The candles.db on the Windows machine has 7+ years of historical data (1.56M rows).
Copying it saves approximately **2-4 weeks** of backfill time to rebuild from scratch.

```bash
# From your local machine (or Windows machine via scp):
scp C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db \
    ait@[SERVER_IP]:/home/ait/ait/trading/spot/data/candles.db
```

**Via rsync (preferred for large file, restartable):**
```bash
rsync -avz --progress \
  /mnt/c/Users/Never/.openclaw/workspace/trading/spot/data/candles.db \
  ait@[SERVER_IP]:/home/ait/ait/trading/spot/data/candles.db
```

### 6.2 Verify Database Integrity

```bash
ssh ait@[SERVER_IP]
cd /home/ait/ait
source .venv/bin/activate

python -c "
import sqlite3
conn = sqlite3.connect('trading/spot/data/candles.db')
hourly = conn.execute('SELECT COUNT(*) FROM candles').fetchone()[0]
daily = conn.execute('SELECT COUNT(*) FROM candles_daily').fetchone()[0]
hourly_coins = conn.execute(\"SELECT COUNT(DISTINCT symbol) FROM candles WHERE timeframe='1h'\").fetchone()[0]
daily_coins = conn.execute('SELECT COUNT(DISTINCT symbol) FROM candles_daily').fetchone()[0]
print(f'candles (1h): {hourly:,} rows, {hourly_coins} symbols')
print(f'candles_daily: {daily:,} rows, {daily_coins} symbols')
# Check for coins with 1h data but no daily data
hourly_bases = set(r[0].split('/')[0] for r in conn.execute(\"SELECT DISTINCT symbol FROM candles WHERE timeframe='1h'\").fetchall())
daily_bases = set(r[0].split('/')[0] for r in conn.execute('SELECT DISTINCT symbol FROM candles_daily').fetchall())
missing = hourly_bases - daily_bases
if missing:
    print(f'WARNING: {len(missing)} coins have 1h but NO daily: {sorted(missing)}')
    print('Run: python trading/spot/resample_daily.py')
else:
    print('All hourly coins have daily data ✓')
conn.close()
"
```

Expected: 1,500,000+ candle rows, 90,000+ daily rows, zero missing coins.
If any coins are missing daily data, run `resample_daily.py` (see §6.3).

### 6.3 Ensure Daily Candles Are Complete

After copying `candles.db`, run the daily resampler to ensure all coins have daily data:

```bash
cd /home/ait/ait && source .venv/bin/activate
python trading/spot/resample_daily.py
```

This aggregates 1h candles → daily OHLCV for any coins that are missing daily data.
The V13SignalPack (which computes all indicators for phase detection) requires daily
candles. Without this step, engines for coins only available on Hyperliquid would run
without signal packs — no phase transitions, no top/bottom detection.

### 6.4 Set DB Environment Variable

The bot resolves candles.db via `AIT_CANDLES_DB` (see Section 7). Set this to the
absolute path on the cloud server.

---

## 7. Environment Configuration

### 7.1 Create .env File

```bash
ssh ait@[SERVER_IP]
mkdir -p /home/ait/ait/trading/spot/live/v14pm
cp /home/ait/ait/trading/spot/live/v14pm/.env.template \
   /home/ait/ait/trading/spot/live/v14pm/.env
nano /home/ait/ait/trading/spot/live/v14pm/.env
```

Fill in all values:

```bash
# /home/ait/ait/trading/spot/live/v14pm/.env

# Hyperliquid API Wallet (see Section 4)
HYPERLIQUID_API_KEY=<your_api_wallet_address>
HYPERLIQUID_API_SECRET=<your_api_wallet_private_key>

# Telegram (same bot token and chat ID as Windows bots)
AIT_TG_TOKEN=<your_telegram_bot_token>
AIT_TG_CHAT_ID=<your_telegram_chat_id>

# Paths (absolute on Linux)
AIT_CANDLES_DB=/home/ait/ait/trading/spot/data/candles.db
AIT_SCANNER_JSON=/home/ait/ait/docs/data/v14/cycle_scanner.json

# Optional
# CFGI_API_KEY=<your_cfgi_key>
```

### 7.2 Protect the .env File

```bash
chmod 600 /home/ait/ait/trading/spot/live/v14pm/.env
```

### 7.3 System-Wide Environment (for systemd)

Systemd services do not inherit the user environment. Create a shared env file:

```bash
sudo mkdir -p /etc/ait
sudo nano /etc/ait/environment

# Contents:
PYTHONPATH=/home/ait/ait
AIT_CANDLES_DB=/home/ait/ait/trading/spot/data/candles.db
AIT_SCANNER_JSON=/home/ait/ait/docs/data/v14/cycle_scanner.json
AIT_TG_TOKEN=<your_telegram_bot_token>
AIT_TG_CHAT_ID=<your_telegram_chat_id>
HYPERLIQUID_API_KEY=<your_api_wallet_address>
HYPERLIQUID_API_SECRET=<your_api_wallet_private_key>

sudo chmod 600 /etc/ait/environment
sudo chown root:root /etc/ait/environment
```

---

## 8. Systemd Services & Timers

Systemd replaces the Windows Scheduled Tasks. One service file per component.

### 8.1 V14PM Live Bot

```bash
sudo nano /etc/systemd/system/ait-v14pm.service
```

```ini
[Unit]
Description=AIT V14PM Live Trading Bot (Hyperliquid)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ait
WorkingDirectory=/home/ait/ait
EnvironmentFile=/etc/ait/environment
ExecStart=/home/ait/ait/.venv/bin/python -u -m trading.spot.run_v14_portfolio_live \
    --capital [INITIAL_CAPITAL] \
    --profile high \
    --leverage 1.0 \
    --exchange hyperliquid \
    --confirm
# State persistence: on restart, the bot loads engine_state.json automatically.
# --fresh is NOT included here — it's only for the very first launch.
# For first launch: manually run with --fresh (see Section 11.3).
Restart=on-failure
RestartSec=30s
StandardOutput=append:/var/log/ait/v14pm.log
StandardError=append:/var/log/ait/v14pm.log

[Install]
WantedBy=multi-user.target
```

> Replace `[INITIAL_CAPITAL]` with Decision D3 (initial live capital in USD).

### 8.2 Candle Collector (Hourly)

```bash
sudo nano /etc/systemd/system/ait-candle-collector.service
```

```ini
[Unit]
Description=AIT Candle Collector (one-shot)
After=network-online.target

[Service]
Type=oneshot
User=ait
WorkingDirectory=/home/ait/ait
EnvironmentFile=/etc/ait/environment
ExecStart=/bin/bash /home/ait/ait/trading/spot/run_candle_collector.sh
StandardOutput=append:/var/log/ait/collector.log
StandardError=append:/var/log/ait/collector.log
```

> **Important:** `run_candle_collector.sh` must include the daily resample step.
> The pipeline is: (1) collect 1h candles, (1.5) resample to daily, (2) run scanner.
> See the Windows version (`run_candle_collector.ps1`) for the exact 3-step sequence.
> The Linux script should call `python trading/spot/resample_daily.py` between steps 1 and 2.

```bash
sudo nano /etc/systemd/system/ait-candle-collector.timer
```

```ini
[Unit]
Description=Run AIT Candle Collector every hour

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

### 8.3 DCA Cycle Scanner (Daily)

```bash
sudo nano /etc/systemd/system/ait-scanner.service
```

```ini
[Unit]
Description=AIT DCA Cycle Scanner (one-shot)

[Service]
Type=oneshot
User=ait
WorkingDirectory=/home/ait/ait
EnvironmentFile=/etc/ait/environment
ExecStart=/home/ait/ait/.venv/bin/python -u -m trading.spot.v14_cycle_scanner \
    --no-telegram
StandardOutput=append:/var/log/ait/scanner.log
StandardError=append:/var/log/ait/scanner.log
```

```bash
sudo nano /etc/systemd/system/ait-scanner.timer
```

```ini
[Unit]
Description=Run AIT DCA Cycle Scanner daily

[Timer]
OnCalendar=daily
RandomizedDelaySec=5min
Persistent=true

[Install]
WantedBy=timers.target
```

### 8.4 Create Log Directory & Enable Services

```bash
sudo mkdir -p /var/log/ait
sudo chown ait:ait /var/log/ait

sudo systemctl daemon-reload

# Enable all services to start on boot
sudo systemctl enable ait-v14pm.service
sudo systemctl enable ait-candle-collector.timer
sudo systemctl enable ait-scanner.timer

# Start timers now (bot starts after cutover — see Section 11)
sudo systemctl start ait-candle-collector.timer
sudo systemctl start ait-scanner.timer

# Verify
sudo systemctl list-timers --all | grep ait
```

### 8.5 Log Rotation

```bash
sudo nano /etc/logrotate.d/ait
```

```
/var/log/ait/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    copytruncate
}
```

---

## 9. GitHub Pages Sync (Linux)

The dashboard sync script (`sync_dashboard.ps1`) is Windows-specific.
A Linux equivalent must be created for the cloud server.

### 9.1 Create Linux Sync Script

```bash
nano /home/ait/ait/sync_dashboard.sh
chmod +x /home/ait/ait/sync_dashboard.sh
```

```bash
#!/usr/bin/env bash
# AIT Dashboard Sync — Linux version
# Pushes docs/ data to GitHub Pages (same logic as sync_dashboard.ps1)

set -euo pipefail

REPO_DIR="/home/ait/ait"
TMP_DIR="/tmp/ait-dashboard-sync"

# Clean and clone with sparse checkout (docs/ only)
rm -rf "$TMP_DIR"
git clone --no-checkout --depth=1 \
  git@github.com:halo-effects/adaptive-intelligence-trading.git \
  "$TMP_DIR"

cd "$TMP_DIR"
git sparse-checkout init --cone
git sparse-checkout set docs
git checkout

# Copy updated data files
cp -r "$REPO_DIR/docs/" "$TMP_DIR/"

# Commit and push
git config user.email "ait-bot@haloeffects.net"
git config user.name "AIT Bot"
git add docs/
git diff --staged --quiet && echo "Nothing to sync" && exit 0
git commit -m "Data sync $(date '+%Y-%m-%d %H:%M')"
git push origin main

echo "Dashboard sync complete"
```

**Requires:** SSH deploy key with push access to the GitHub repo.
See your GitHub repo Settings → Deploy Keys → Add key (check "Allow write access").

### 9.2 Dashboard Sync Timer

```bash
sudo nano /etc/systemd/system/ait-dashboard-sync.service
```

```ini
[Unit]
Description=AIT Dashboard Sync (one-shot)

[Service]
Type=oneshot
User=ait
WorkingDirectory=/home/ait/ait
ExecStart=/bin/bash /home/ait/ait/sync_dashboard.sh
StandardOutput=append:/var/log/ait/sync.log
StandardError=append:/var/log/ait/sync.log
```

```bash
sudo nano /etc/systemd/system/ait-dashboard-sync.timer
```

```ini
[Unit]
Description=AIT Dashboard Sync every 10 minutes

[Timer]
OnCalendar=*:0/10
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ait-dashboard-sync.timer
sudo systemctl start ait-dashboard-sync.timer
```

---

## 10. Pre-Launch Checklist

Complete every item in order. Do not proceed to Section 11 until all pass.

### 10.1 Infrastructure
- [ ] Server provisioned and accessible via SSH as `ait` user
- [ ] UFW firewall enabled (SSH only inbound)
- [ ] Python 3.12 installed and venv activated
- [ ] `trading/requirements.txt` installed
- [ ] All 8 imports pass (Section 5.3)

### 10.2 Data
- [ ] `candles.db` transferred and verified (1.5M+ rows)
- [ ] `candles_daily` has rows for ALL scanner coins (run `resample_daily.py` after transfer)
- [ ] Zero coins have 1h data but missing daily data (verify with §6.2 check script)
- [ ] Candle collector runs successfully: `bash trading/spot/run_candle_collector.sh`
- [ ] `docs/data/v14/cycle_scanner.json` exists and has rankings
- [ ] Score history backfilled (`--backfill-history 7`) — trend multipliers require ≥3 snapshots

### 10.3 Configuration
- [ ] `/home/ait/ait/trading/spot/live/v14pm/.env` filled in and `chmod 600`
- [ ] `/etc/ait/environment` filled in and `chmod 600`
- [ ] `HYPERLIQUID_API_KEY` is an API wallet address (not main wallet)
- [ ] `HYPERLIQUID_API_SECRET` is the API wallet private key

### 10.4 Exchange Connectivity
```bash
# Test exchange connection (read-only, no orders placed)
cd /home/ait/ait && source .venv/bin/activate
python -c "
import os
from trading.spot.exchange_client import SpotExchangeClient
client = SpotExchangeClient('hyperliquid')
balance = client.fetch_balance()
print('Connection OK')
print('USDC balance:', balance.get('USDC', {}).get('total', 0))
"
```
- [ ] Exchange connects without error
- [ ] USDC balance matches expected initial capital (within $1)
- [ ] Telegram alert received: "Exchange connection test OK"

### 10.5 Live Bot Runner
- [ ] `run_v14_portfolio_live.py` created (Section 5.4)
- [ ] Dry-run passes: `python -m trading.spot.run_v14_portfolio_live --dry-run`
- [ ] Dry-run Telegram message received

### 10.6 Systemd Services
- [ ] `ait-candle-collector.timer` active and running
- [ ] `ait-scanner.timer` active and running
- [ ] `ait-dashboard-sync.timer` active and running
- [ ] First dashboard sync successful (GitHub Pages updated)
- [ ] `journalctl -u ait-candle-collector -n 50` shows no errors

---

## 11. Live Trading Cutover

### 11.1 Timing

Choose a time when:
- No active DCA positions are open in the paper bot (simpler capital reconciliation)
- Market conditions are not extreme (avoid launching into heavy volatility)
- You are available to monitor for the first 2 hours

### 11.2 Capital Deposit

> **Decision D3** — Initial live capital.

1. Deposit USDC to your Hyperliquid main account
2. Verify balance via Hyperliquid UI
3. Authorize the API wallet to trade (if not done in Section 4)

**Equity tier at launch:**

| Capital | Max Coins Active |
|---------|-----------------|
| $1,000 | 1 |
| $10,000 | 2 |
| $20,000 | 3 |
| $30,000 | 4 |
| $50,000 | 5 |
| $100,000 | 10 |

### 11.3 Start the Bot

**First launch (one time only):**
```bash
# Manual first launch with --fresh to avoid processing historical candles:
cd /home/ait/ait && source .venv/bin/activate
python -u -m trading.spot.run_v14_portfolio_live \
  --capital [INITIAL_CAPITAL] --profile high --leverage 1.0 \
  --exchange hyperliquid --confirm --fresh

# Wait for first status cycle (~60 seconds) to confirm engine_state.json is written:
ls -la trading/spot/live/v14pm/engine_state.json

# Once confirmed working, stop the manual run (Ctrl+C) and enable systemd:
sudo systemctl start ait-v14pm.service
```

**Subsequent restarts (systemd handles automatically):**
```bash
# Systemd service does NOT use --fresh. On restart, the bot loads engine_state.json
# and resumes from where it left off — no candle replay, no phantom trades.
sudo systemctl start ait-v14pm.service

# Follow logs live
sudo journalctl -u ait-v14pm -f
```

### 11.4 First Startup Verification

Within 5 minutes of start, verify:
- [ ] Telegram alert received: bot started
- [ ] `trading/spot/live/v14pm/status.json` written and `running: true`
- [ ] Log shows: "Exchange connection OK"
- [ ] Log shows: "CapitalRouter initialized with $[CAPITAL]"
- [ ] Log shows: "DCA Scanner loaded, [N] coins qualify"
- [ ] First tier is correct for your capital level
- [ ] No Python exceptions in log

### 11.5 First Hour Monitoring

- Monitor `journalctl -u ait-v14pm -f` for the first cycle
- Verify first candle is fetched at the top of the next hour
- Verify first position evaluation runs (may or may not enter — depends on signal state)
- Confirm status.json updates each cycle

### 11.6 Enable Auto-Start on Reboot

```bash
sudo systemctl enable ait-v14pm.service
```

---

## 12. Ongoing Operations

### 12.1 Common Commands

```bash
# Service status
sudo systemctl status ait-v14pm

# Live log
sudo journalctl -u ait-v14pm -f

# Restart bot
sudo systemctl restart ait-v14pm

# View last 100 log lines
sudo journalctl -u ait-v14pm -n 100

# Check all AIT timers
sudo systemctl list-timers | grep ait

# Manual candle collection
cd /home/ait/ait && source .venv/bin/activate
bash trading/spot/run_candle_collector.sh

# Manual scanner run
python -u -m trading.spot.v14_cycle_scanner

# Backfill score history for trend data (run once after fresh deployment)
# The PM needs ≥3 daily snapshots for trend multipliers to compute.
# This generates genuine historical snapshots from candle DB data:
python -u -m trading.spot.v14_cycle_scanner --backfill-history 7 --no-telegram
```

### 12.2 Updating the Bot

```bash
# Pull latest code
cd /home/ait/ait
git pull origin main

# Restart if needed
sudo systemctl restart ait-v14pm
```

**Safety:** The bot gracefully handles restarts — `engine_state.json` preserves all
engine positions, phases, signal state, and router allocations. On restart, the bot
loads this file and resumes from the last processed candle. No `--fresh` or
`--skip-backfill` flags needed.

### 12.3 Database Maintenance

candles.db grows ~30 MB/year at the current 66-coin coverage. No maintenance required
for at least 5 years at current growth rate.

**Periodic backup (add to cron):**
```bash
# Weekly backup to a separate file
0 2 * * 0 cp /home/ait/ait/trading/spot/data/candles.db \
           /home/ait/backups/candles-$(date +\%Y\%m\%d).db
```

### 12.4 Heartbeat Monitoring from Gee Gee

The Windows-based heartbeat monitor (Gee Gee / OpenClaw) checks `status.json` files.
For the cloud bot, `status.json` is at:

```
trading/spot/live/v14pm/status.json
```

This file is pushed to GitHub Pages via the dashboard sync, so Gee Gee can monitor
it remotely without SSH access to the server.

**Heartbeat thresholds:**
- `running: false` → immediate alert
- `last_update` stale > 65 minutes → immediate alert
- `max_drawdown_pct` > 15% → alert (capital at risk)

### 12.5 Adding Coins to the Live Bot

Capital rotation is fully automatic via the DCA Cycle Scanner. To add new coins to
the scanned universe, edit `COINS` in `v14_cycle_scanner.py` and `collect_scanner_candles.py`,
then run a backfill:

```bash
python -u trading/spot/backfill_scanner_coins.py --coins NEW/USDT
```

---

## 13. Rollback Plan

### If the live bot fails to start

1. Check logs: `journalctl -u ait-v14pm -n 200`
2. Common causes:
   - Missing env var → fix `/etc/ait/environment`, restart
   - Exchange auth failure → verify API wallet credentials
   - DB path wrong → verify `AIT_CANDLES_DB` path exists
3. Paper bot on Windows remains running — no customer impact

### If the live bot crashes mid-trading

1. Bot auto-restarts via systemd (`Restart=on-failure`)
2. On restart, it reads `state.json` and reconciles with exchange
3. Any open positions are recovered — the bot does not place duplicate orders
4. Monitor Telegram for "Bot restarted" message

### If capital is at risk (drawdown > threshold)

1. Emergency stop: `sudo systemctl stop ait-v14pm`
2. Open positions remain on exchange (are not closed by stopping the bot)
3. Evaluate manually on Hyperliquid UI
4. Decide: wait for DCA grid to recover, or close manually
5. Do NOT re-enable until root cause is understood

### Full rollback

1. Stop cloud bot: `sudo systemctl stop ait-v14pm && sudo systemctl disable ait-v14pm`
2. Close any open positions manually on Hyperliquid
3. Withdraw USDC back to main wallet
4. Paper bots on Windows are unaffected throughout

---

## Appendix A: File Layout on Cloud Server

```
/home/ait/ait/                          ← Cloned repo (workspace root)
├── .venv/                              ← Python venv
├── trading/
│   ├── spot/
│   │   ├── data/candles.db             ← Migrated from Windows
│   │   └── live/v14pm/
│   │       ├── .env                    ← Credentials (NOT in git)
│   │       ├── engine_state.json       ← Full engine state (saved every 60s, restored on restart)
│   │       ├── status.json             ← Health metrics (dashboard + heartbeat)
│   │       └── trades.csv              ← Closed trade history (source of truth for PnL)
│   └── requirements.txt
├── docs/                               ← Dashboard data (synced to GitHub Pages)
└── sync_dashboard.sh                   ← Linux dashboard sync

/etc/ait/environment                    ← systemd environment file (root-owned)
/var/log/ait/                           ← Logs (v14pm.log, collector.log, etc.)
/etc/systemd/system/ait-*.service       ← Service units
/etc/systemd/system/ait-*.timer         ← Timer units
```

## Appendix B: Open Items (must complete before cutover)

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Create `run_v14_portfolio_live.py` | Engineering | PENDING | Copy paper runner, enable real orders, add `--confirm`/`--dry-run`, keep state persistence, add exchange reconciliation, remove PID lock, equity from exchange API, CSV-as-truth for realized PnL, `--fresh` loads existing trades |
| Create `run_candle_collector.sh` (Linux) | Engineering | PENDING | Must include 3-step pipeline: collect → resample_daily → scanner. Template the Windows `.ps1` version. |
| Create `sync_dashboard.sh` as git-committed file | Engineering | PENDING | Template in Section 9.1 above |
| Centralize `DB_PATH` into `trading/spot/config.py` | Engineering | RECOMMENDED | 6 files independently define DB_PATH. Two had wrong paths. Single import eliminates this bug class. |
| Set up GitHub deploy key on cloud server | Ops | PENDING | For dashboard sync push access |
| Decide initial live capital | Brett | PENDING | D3 — determines coin cap tier at launch |
| Create Hyperliquid API wallet | Brett | PENDING | D4 — must be done before deployment |
| Choose cloud provider + region | Brett | PENDING | D1, D2, D5 |

---

_Document generated by Gee Gee — 2026-03-09_
_Updated: 2026-03-10 (v1.2 — CSV-as-truth for all bots, exchange API equity for live, --fresh loads existing trades)_
_Architecture reference: `V14PM_SYSTEM_ARCHITECTURE.md` (v1.1)_
_Audit trail: `V14PM_FULL_AUDIT.md`, `PM_AUDIT_2026-03-10.md`_
