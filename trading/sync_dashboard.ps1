# AIT Dashboard → GitHub Pages sync script
# Runs every 10 minutes via Scheduled Task "AIT_DashboardSync"
#
# SAFETY: This script ONLY manages files under docs/ in the remote repo.
# It NEVER uses `git add -A` (which would delete non-docs files from GitHub).
# All git staging is scoped to `git add docs/` only.
$repoDir = "$env:TEMP\ait-dashboard-sync"
$spotLiveDir = "C:\Users\Never\.openclaw\workspace\trading\spot\live\aster"
$scannerDir = "C:\Users\Never\.openclaw\workspace\trading\scanner"
$docsDir = "C:\Users\Never\.openclaw\workspace\docs"
$pat = $env:AIT_GITHUB_PAT
if (-not $pat) { $pat = [Environment]::GetEnvironmentVariable("AIT_GITHUB_PAT", "User") }
if (-not $pat) { Write-Error "AIT_GITHUB_PAT env var not set"; exit 1 }
$repoUrl = "https://halo-effects:$pat@github.com/halo-effects/adaptive-intelligence-trading.git"

# Clone or pull (docs/ only — never pulls source files into this working copy)
if (Test-Path "$repoDir\.git") {
    Set-Location $repoDir
    # Fetch remote but do NOT checkout docs/ — we are the sole writer.
    # Checking out remote docs/ would overwrite fresh local data with stale remote data
    # if any previous sync caught a bad snapshot.
    git fetch --quiet 2>$null
    # Only reset to remote HEAD to keep history clean (no file checkout)
    git reset --soft origin/main 2>$null
} else {
    if (Test-Path $repoDir) { Remove-Item $repoDir -Recurse -Force }
    # Sparse clone — only checkout docs/ so git add can never stage source file deletions
    git clone --no-checkout --depth=1 $repoUrl $repoDir 2>$null
    Set-Location $repoDir
    git config user.email "geegee@haloeffects.net"
    git config user.name "Gee Gee"
    git sparse-checkout init --cone 2>$null
    git sparse-checkout set docs 2>$null
    git checkout main --quiet 2>$null
}

# Ensure docs/data subdirectories exist
foreach ($sub in @("v14-live", "v14", "v14-pm")) {
    New-Item -ItemType Directory -Path "$repoDir\docs\data\$sub" -Force | Out-Null
}

# ── V14 Live → docs/data/v14-live/ ──
$v14LiveDir = "C:\Users\Never\.openclaw\workspace\trading\spot\live\v14"
if (Test-Path "$v14LiveDir\status.json") {
    Copy-Item "$v14LiveDir\status.json" "$repoDir\docs\data\v14-live\status.json" -Force
}
if (Test-Path "$v14LiveDir\trades.csv") {
    Copy-Item "$v14LiveDir\trades.csv" "$repoDir\docs\data\v14-live\trades.csv" -Force
}

# ── V12f/V13 — REMOVED (legacy, no longer synced) ──

# ── V14 DCA paper → docs/data/v14/ ──
$v14Dir = "C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14"
if (Test-Path "$v14Dir\status.json") {
    Copy-Item "$v14Dir\status.json" "$repoDir\docs\data\v14\status.json" -Force
}
if (Test-Path "$v14Dir\trades.csv") {
    Copy-Item "$v14Dir\trades.csv" "$repoDir\docs\data\v14\trades.csv" -Force
}
# V14 scanner data
$v14ScannerFile = "C:\Users\Never\.openclaw\workspace\docs\data\v14\scanner.json"
if (Test-Path $v14ScannerFile) {
    Copy-Item $v14ScannerFile "$repoDir\docs\data\v14\scanner.json" -Force
}
$v14CycleScannerFile = "C:\Users\Never\.openclaw\workspace\docs\data\v14\cycle_scanner.json"
if (Test-Path $v14CycleScannerFile) {
    Copy-Item $v14CycleScannerFile "$repoDir\docs\data\v14\cycle_scanner.json" -Force
}


# ── V14-PM Portfolio Manager → docs/data/v14-pm/ (PAPER ONLY) ──
# FIXED 2026-03-19: Never overwrite paper data with live data.
# Live PM data goes to docs/data/v14-pm-live/ (see below).
$v14pmLiveDir = "C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm"
$v14pmPaperDir = "C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio"
if (-not (Test-Path "$repoDir\docs\data\v14-pm")) {
    New-Item -Path "$repoDir\docs\data\v14-pm" -ItemType Directory -Force | Out-Null
}
# Always use paper — no live override
if (Test-Path "$v14pmPaperDir\status.json") {
    Copy-Item "$v14pmPaperDir\status.json" "$repoDir\docs\data\v14-pm\status.json" -Force
}
if (Test-Path "$v14pmPaperDir\trades.csv") {
    Copy-Item "$v14pmPaperDir\trades.csv" "$repoDir\docs\data\v14-pm\trades.csv" -Force
}

# ── V14-PM Live → docs/data/v14-pm-live/ ──
if (-not (Test-Path "$repoDir\docs\data\v14-pm-live")) {
    New-Item -Path "$repoDir\docs\data\v14-pm-live" -ItemType Directory -Force | Out-Null
}
if (Test-Path "$v14pmLiveDir\status.json") {
    Copy-Item "$v14pmLiveDir\status.json" "$repoDir\docs\data\v14-pm-live\status.json" -Force
}
if (Test-Path "$v14pmLiveDir\trades.csv") {
    Copy-Item "$v14pmLiveDir\trades.csv" "$repoDir\docs\data\v14-pm-live\trades.csv" -Force
}

# ── Scanner data ──
foreach ($f in @("scanner_recommendation.json", "scanner_t1.json", "scanner_t2.json")) {
    if (Test-Path "$scannerDir\$f") {
        Copy-Item "$scannerDir\$f" "$repoDir\docs\data\$f" -Force
    }
}

# Copy dashboard files from workspace docs/
# Legacy dashboards (V12, V13, old hidden) — REMOVED from sync
if (Test-Path "$docsDir\dashboardV14.html") {
    Copy-Item "$docsDir\dashboardV14.html" "$repoDir\docs\dashboardV14.html" -Force
}
if (Test-Path "$docsDir\dashboardV14PM.html") {
    Copy-Item "$docsDir\dashboardV14PM.html" "$repoDir\docs\dashboardV14PM.html" -Force
}
# Old live dashboard — deprecated, no longer synced
# Copy-Item "$docsDir\d-474521b7c3545633.html" "$repoDir\docs\d-474521b7c3545633.html" -Force
if (Test-Path "$docsDir\d-984ae0d4ab9dc1a5.html") {
    Copy-Item "$docsDir\d-984ae0d4ab9dc1a5.html" "$repoDir\docs\d-984ae0d4ab9dc1a5.html" -Force
}
Copy-Item "$docsDir\index.html" "$repoDir\docs\index.html" -Force
Copy-Item "$docsDir\pricing.html" "$repoDir\docs\pricing.html" -Force
if (Test-Path "$docsDir\adaptive-intelligence.html") {
    Copy-Item "$docsDir\adaptive-intelligence.html" "$repoDir\docs\adaptive-intelligence.html" -Force
}
Copy-Item "$docsDir\risk-profiles.html" "$repoDir\docs\risk-profiles.html" -Force
if (Test-Path "$docsDir\qb-theme.css") {
    Copy-Item "$docsDir\qb-theme.css" "$repoDir\docs\qb-theme.css" -Force
}
# Ensure .nojekyll exists (prevents Jekyll processing on GitHub Pages)
if (-not (Test-Path "$repoDir\docs\.nojekyll")) {
    New-Item -Path "$repoDir\docs\.nojekyll" -ItemType File -Force | Out-Null
}

# ── Generate daily equity JSON for calculator ──
$equityScript = "C:\Users\Never\.openclaw\workspace\trading\spot\generate_daily_equity.py"
$pythonExe = "C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe"
if ((Test-Path $equityScript) -and (Test-Path $pythonExe)) {
    try {
        & $pythonExe $equityScript 2>$null
        # Copy generated file to sync repo
        $equityJson = "C:\Users\Never\.openclaw\workspace\docs\data\v14\daily_equity.json"
        if (Test-Path $equityJson) {
            Copy-Item $equityJson "$repoDir\docs\data\v14\daily_equity.json" -Force
        }
    } catch {
        # Non-fatal - calculator data just won't update this cycle
    }
}

# Stage docs/ ONLY — never stage deletions of source files outside docs/
git add docs/
$changes = git status --porcelain
if ($changes) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm"
    git commit -m "Data sync $ts" --quiet

    # Push with divergence recovery — if push fails (e.g. remote has new commits),
    # pull --rebase to integrate, then retry. If that fails, nuke and reclone next cycle.
    $pushResult = git push --quiet 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Push failed, attempting pull --rebase recovery..."
        $pullResult = git pull --rebase origin main 2>&1
        if ($LASTEXITCODE -eq 0) {
            git push --quiet 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Host "ERROR: Push failed after rebase. Nuking sync repo for fresh clone next cycle."
                Set-Location $env:TEMP
                Remove-Item $repoDir -Recurse -Force -ErrorAction SilentlyContinue
            }
        } else {
            Write-Host "ERROR: Rebase failed. Nuking sync repo for fresh clone next cycle."
            git rebase --abort 2>$null
            Set-Location $env:TEMP
            Remove-Item $repoDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}
