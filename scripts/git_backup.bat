@echo off
:: Workspace Git Backup - no LLM API calls required
cd /d C:\Users\Never\.openclaw\workspace
git add -A
git diff --cached --quiet && (
    echo [%DATE% %TIME%] No changes to commit >> C:\Users\Never\.openclaw\workspace\memory\git_backup.log
    exit /b 0
)
git commit -m "auto: workspace backup %DATE% %TIME:~0,5%"
git push origin main >> C:\Users\Never\.openclaw\workspace\memory\git_backup.log 2>&1
echo [%DATE% %TIME%] Git backup completed >> C:\Users\Never\.openclaw\workspace\memory\git_backup.log
