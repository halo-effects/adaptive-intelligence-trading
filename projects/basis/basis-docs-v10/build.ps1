<#
Build script for Basis SDK Docs V10
Generates: INDEX.md, COMPLETE.md, COMPLETE_INDEX.md, llms-full.txt
Run from: basis-docs-v10/
#>

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$modulesDir = Join-Path $root "modules"
$outDir = $root
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

Write-Host "=== Basis SDK Docs V10 Build ===" -ForegroundColor Cyan

# --- 1. INDEX.md ---
Write-Host "[1/4] Building INDEX.md..."

$indexDesc = [System.IO.File]::ReadAllText((Join-Path $root "INDEX_DESCRIPTIONS.md"), [System.Text.Encoding]::UTF8)
$indexContent = $indexDesc -replace "# INDEX_DESCRIPTIONS.*", "# INDEX - Basis SDK Documentation V10"
$indexContent = $indexContent -replace "(?s)_Section descriptions for compiling INDEX files\..*?_", @"
_Module index with descriptions. Use this to find the right module for your task._

> **New here?** Start with [00-guide.md](00-guide.md) for a guided orientation.
> **Want everything in one file?** See [COMPLETE.md](COMPLETE.md).
"@
[System.IO.File]::WriteAllText((Join-Path $outDir "INDEX.md"), $indexContent, $utf8NoBom)
Write-Host "  INDEX.md written." -ForegroundColor Green

# --- 2. COMPLETE.md ---
Write-Host "[2/4] Building COMPLETE.md..."

$modules = Get-ChildItem $modulesDir -Filter "*.md" |
    Where-Object { $_.Name -match "^\d{2}-" } |
    Sort-Object Name

$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine("# Basis SDK Documentation - COMPLETE")
[void]$sb.AppendLine()
$dateStr = Get-Date -Format "yyyy-MM-dd HH:mm"
[void]$sb.AppendLine("_All $($modules.Count) modules concatenated. Generated $dateStr from individual module files._")
[void]$sb.AppendLine()
[void]$sb.AppendLine("---")
[void]$sb.AppendLine()

foreach ($mod in $modules) {
    $content = [System.IO.File]::ReadAllText($mod.FullName, [System.Text.Encoding]::UTF8)
    $content = $content.TrimStart([char]0xFEFF)
    [void]$sb.AppendLine("<!-- section:$($mod.BaseName) -->")
    [void]$sb.AppendLine()
    [void]$sb.AppendLine($content.TrimEnd())
    [void]$sb.AppendLine()
    [void]$sb.AppendLine("---")
    [void]$sb.AppendLine()
}

$completeText = $sb.ToString()
[System.IO.File]::WriteAllText((Join-Path $outDir "COMPLETE.md"), $completeText, $utf8NoBom)
$totalLines = ($completeText -split "`n").Count
Write-Host ("  COMPLETE.md written ({0} lines)." -f $totalLines) -ForegroundColor Green

# --- 3. COMPLETE_INDEX.md ---
Write-Host "[3/4] Building COMPLETE_INDEX.md..."

$lines = $completeText -split "`n"
$ci = New-Object System.Text.StringBuilder
[void]$ci.AppendLine("# COMPLETE_INDEX - Line References")
[void]$ci.AppendLine()
[void]$ci.AppendLine("_Jump to any module section within [COMPLETE.md](COMPLETE.md) by line number._")
[void]$ci.AppendLine()
[void]$ci.AppendLine("| Module | Line | Description |")
[void]$ci.AppendLine("|--------|------|-------------|")

$moduleDescriptions = @{}
foreach ($mod in $modules) {
    $modContent = [System.IO.File]::ReadAllText($mod.FullName, [System.Text.Encoding]::UTF8)
    $firstHeading = ($modContent -split "`n" | Where-Object { $_ -match "^#\s" } | Select-Object -First 1)
    if ($firstHeading) {
        $moduleDescriptions[$mod.BaseName] = ($firstHeading -replace "^#+\s*", "").Trim()
    } else {
        $moduleDescriptions[$mod.BaseName] = $mod.BaseName
    }
}

for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match "^<!-- section:(.+?) -->") {
        $modName = $matches[1]
        $lineNum = $i + 1
        $desc = $moduleDescriptions[$modName]
        if (-not $desc) { $desc = $modName }
        [void]$ci.AppendLine("| ``$modName`` | $lineNum | $desc |")
    }
}

[void]$ci.AppendLine()
[void]$ci.AppendLine("_Total: $totalLines lines across $($modules.Count) modules._")

[System.IO.File]::WriteAllText((Join-Path $outDir "COMPLETE_INDEX.md"), $ci.ToString(), $utf8NoBom)
Write-Host "  COMPLETE_INDEX.md written." -ForegroundColor Green

# --- 4. llms-full.txt ---
Write-Host "[4/4] Building llms-full.txt..."

$llms = New-Object System.Text.StringBuilder
[void]$llms.AppendLine("# Basis SDK Documentation - Full Reference")
[void]$llms.AppendLine("# https://launchonbasis.com/sdk-docs")
[void]$llms.AppendLine()
[void]$llms.AppendLine("# This file contains the complete Basis SDK documentation for LLM consumption.")
[void]$llms.AppendLine("# For individual modules, see: modules/")
[void]$llms.AppendLine()
[void]$llms.AppendLine("---")
[void]$llms.AppendLine()

# Include all modules (01-29, skip 00-guide already included)
foreach ($mod in $modules) {
    $content = [System.IO.File]::ReadAllText($mod.FullName, [System.Text.Encoding]::UTF8)
    $content = $content.TrimStart([char]0xFEFF)
    [void]$llms.AppendLine($content.TrimEnd())
    [void]$llms.AppendLine()
    [void]$llms.AppendLine("---")
    [void]$llms.AppendLine()
}

$llmsFullText = $llms.ToString()
[System.IO.File]::WriteAllText((Join-Path $outDir "llms-full.txt"), $llmsFullText, $utf8NoBom)
$llmsSize = [math]::Round((Get-Item (Join-Path $outDir "llms-full.txt")).Length / 1KB)
Write-Host ("  llms-full.txt written ({0}KB)." -f $llmsSize) -ForegroundColor Green

Write-Host ""
Write-Host "=== Build complete ===" -ForegroundColor Cyan
Write-Host "  INDEX.md"
Write-Host ("  COMPLETE.md ({0} lines)" -f $totalLines)
Write-Host "  COMPLETE_INDEX.md"
Write-Host ("  llms-full.txt ({0}KB)" -f $llmsSize)
