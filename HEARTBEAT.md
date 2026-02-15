# HEARTBEAT.md

## Aster Trading Bot
- Check `trading/live/status.json` for bot health
- Alert if: `running` is false, `halted` is true, drawdown > 15%, or regime changes to EXTREME
- Check `trading/live/bot_service.log` tail for recent activity (stale = no logs in 5+ min)
- If bot is down, restart via: `Start-ScheduledTask -TaskName "AsterTradingBot"`
- If dashboard is down, restart via: `Start-ScheduledTask -TaskName "AsterDashboard"`
