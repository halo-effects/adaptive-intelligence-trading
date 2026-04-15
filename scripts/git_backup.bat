@echo off
:: Workspace Git Backup - no LLM API calls required
:: NOTE: Uses 'git add -A' which respects .gitignore.
:: Bot runtime data (state.json, status.json, trades.csv, logs, etc)
:: is excluded via .gitignore to prevent accidental code regression.
:: See incident 2026-04-14 for context.
cd /d C:\Users\Never\.openclaw\workspace
git add -A
git diff --cached --quiet && (
    echo [%DATE% %TIME%] No changes to commit >> C:\Users\Never\.openclaw\workspace\memory\git_backup.log
    exit /b 0
)
git commit -m "auto-backup %DATE:~-4%-%DATE:~4,2%-%DATE:~7,2% %TIME:~0,5%"
git push origin main >> C:\Users\Never\.openclaw\workspace\memory\git_backup.log 2>&1
echo [%DATE% %TIME%] Git backup completed >> C:\Users\Never\.openclaw\workspace\memory\git_backup.log
