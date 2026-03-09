#!/usr/bin/env bash
# AIT Candle Collector + DCA Scanner Pipeline
# Linux/cloud equivalent of run_candle_collector.ps1
#
# Run hourly via cron or systemd timer:
#   0 * * * * /opt/ait/trading/spot/run_candle_collector.sh >> /var/log/ait/collector.log 2>&1
#
# Required env vars (set in systemd service or .env):
#   AIT_CANDLES_DB   - path to candles.db (default: trading/spot/data/candles.db)
#   AIT_TG_TOKEN     - Telegram bot token
#   AIT_TG_CHAT_ID   - Telegram chat ID

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${PYTHON:-python3}"
LOG_FILE="${WORK_DIR}/trading/spot/data/collector.log"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

log() { echo "[$TIMESTAMP] $*" | tee -a "$LOG_FILE"; }

log "=== Candle Collector Pipeline Start ==="

# Step 1: Collect candles
log "Step 1: Collecting candles..."
if "$PYTHON" -u "$SCRIPT_DIR/collect_scanner_candles.py"; then
    log "Step 1 complete."
else
    log "WARNING: Candle collector exited with error"
fi

# Step 2: Run DCA Cycle Scanner
log "Step 2: Running DCA Cycle Scanner..."
if cd "$WORK_DIR" && "$PYTHON" -u -m trading.spot.v14_cycle_scanner --no-telegram; then
    log "Step 2 complete."
else
    log "WARNING: Scanner exited with error"
fi

log "=== Pipeline Complete ==="
