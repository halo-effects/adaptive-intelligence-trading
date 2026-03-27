$dir = "C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs"

# Module files in order
$modules = @(
    "00-welcome_V3.md",
    "01-what-is-basis_V3.md",
    "02-archetypes_V3.md",
    "03-token-value_V3.md",
    "04-atomic-skills_V3.md",
    "05-strategies_V3.md",
    "06-decision-trees_V3.md",
    "07-why_V3.md",
    "08-how_V3.md",
    "09-getting-started_V3.md",
    "10-fees_V3.md",
    "11-errors_V3.md",
    "12-api-reference_V3.md",
    "13-trust-safety_V3.md",
    "14-mistakes_V3.md",
    "15-faq_V3.md",
    "16-contract-addresses_V3.md",
    "17-examples_V3.md",
    "18-prediction-market-deep-dive_V3.md",
    "19-what-to-avoid_V3.md",
    "20-production-ops_V3.md"
)

# ---- Build COMPLETE_V3.md ----
$header = @"
# Basis - Complete Agent Guide

_SDK Documentation v1.0.2 | Phase 1: Founding Lobster | Last updated: 2026-03-27_

_All sections concatenated. Load this single file for full platform context._

---
"@

$parts = @($header)
foreach ($mod in $modules) {
    $path = Join-Path $dir $mod
    $content = Get-Content $path -Raw -Encoding UTF8
    $parts += $content.Trim()
}

$complete = $parts -join "`n`n---`n`n"
$completePath = Join-Path $dir "COMPLETE_V3.md"
Set-Content -Path $completePath -Value $complete -Encoding UTF8
Write-Output "Built COMPLETE_V3.md ($((Get-Item $completePath).Length) bytes)"

# ---- Build COMPLETE_INDEX_V3.md ----
$lines = Get-Content $completePath
$inCode = $false
$indexEntries = @()
for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    if ($line.Trim() -match '^```') { $inCode = -not $inCode }
    if (-not $inCode) {
        if ($line -match '^(#{1,3}) (.+)$') {
            $level = $matches[1].Length
            $title = $matches[2].Trim()
            $lineNum = $i + 1
            $indent = "  " * ($level - 1)
            $indexEntries += "${indent}${lineNum}  ${title}"
        }
    }
}

$indexHeader = @"
# COMPLETE_INDEX_V3.md — Line Number Index

_SDK Documentation v1.0.2 | Last updated: 2026-03-27_

Line number references into COMPLETE_V3.md. Use these to jump directly to any section.

---

"@

$indexContent = $indexHeader + ($indexEntries -join "`n")
$indexPath = Join-Path $dir "COMPLETE_INDEX_V3.md"
Set-Content -Path $indexPath -Value $indexContent -Encoding UTF8
Write-Output "Built COMPLETE_INDEX_V3.md ($($indexEntries.Count) entries)"

# ---- Build INDEX_V3.md ----
$indexV3Header = @"
# INDEX_V3.md — Module File Index

_SDK Documentation v1.0.2 | Last updated: 2026-03-27_

> This file maps to individual section files. Use COMPLETE_V3.md for single-file loading.

---

"@

$moduleLinks = @()
foreach ($mod in $modules) {
    $path = Join-Path $dir $mod
    $firstLine = (Get-Content $path | Where-Object { $_ -match '^# ' } | Select-Object -First 1)
    $title = $firstLine -replace '^# ', ''
    # Production (non-versioned) filename
    $prodName = $mod -replace '_V3\.md$', '.md'
    $moduleLinks += "### [$prodName]($prodName)"
    $moduleLinks += "**$title**"
    $moduleLinks += ""
}

$indexV3Content = $indexV3Header + ($moduleLinks -join "`n")
$indexV3Path = Join-Path $dir "INDEX_V3.md"
Set-Content -Path $indexV3Path -Value $indexV3Content -Encoding UTF8
Write-Output "Built INDEX_V3.md ($($modules.Count) modules)"

Write-Output "`nAll V3 index files built successfully."
