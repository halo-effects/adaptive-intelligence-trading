$dir = "C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$utf8 = [System.Text.Encoding]::UTF8

$modules = @(
    "00-welcome_V3.md","01-what-is-basis_V3.md","02-archetypes_V3.md",
    "03-token-value_V3.md","04-atomic-skills_V3.md","05-strategies_V3.md",
    "06-decision-trees_V3.md","07-why_V3.md","08-how_V3.md",
    "09-getting-started_V3.md","10-fees_V3.md","11-errors_V3.md",
    "12-api-reference_V3.md","13-trust-safety_V3.md","14-mistakes_V3.md",
    "15-faq_V3.md","16-contract-addresses_V3.md","17-examples_V3.md",
    "18-prediction-market-deep-dive_V3.md","19-what-to-avoid_V3.md",
    "20-production-ops_V3.md"
)

# Build COMPLETE_V3.md
$header = "# Basis - Complete Agent Guide`n`n_SDK Documentation v1.0.2 | Phase 1: Founding Lobster | Last updated: 2026-03-27_`n`n_All sections concatenated. Load this single file for full platform context._`n`n---"

$parts = @($header)
foreach ($mod in $modules) {
    $content = $utf8.GetString([System.IO.File]::ReadAllBytes("$dir\$mod")).Trim()
    # Remove BOM if present
    if ($content[0] -eq [char]0xFEFF) { $content = $content.Substring(1) }
    $parts += $content
}

$complete = $parts -join "`n`n---`n`n"
[System.IO.File]::WriteAllText("$dir\COMPLETE_V3.md", $complete, $utf8NoBom)
$completeLines = ($complete -split "`n").Count
Write-Output "Built COMPLETE_V3.md ($completeLines lines, $([System.IO.File]::ReadAllBytes("$dir\COMPLETE_V3.md").Length) bytes)"

# Build COMPLETE_INDEX_V3.md
$lines = $complete -split "`n"
$inCode = $false
$indexEntries = @()
for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    if ($line.Trim() -match '^```') { $inCode = -not $inCode }
    if (-not $inCode -and $line -match '^(#{1,3}) (.+)$') {
        $level = $matches[1].Length
        $title = $matches[2].Trim()
        $lineNum = $i + 1
        $indent = "  " * ($level - 1)
        $indexEntries += "${indent}${lineNum}  ${title}"
    }
}

$indexContent = "# COMPLETE_INDEX_V3.md`n`n_SDK Documentation v1.0.2 | Last updated: 2026-03-27_`n`nLine number references into COMPLETE_V3.md.`n`n---`n`n" + ($indexEntries -join "`n")
[System.IO.File]::WriteAllText("$dir\COMPLETE_INDEX_V3.md", $indexContent, $utf8NoBom)
Write-Output "Built COMPLETE_INDEX_V3.md ($($indexEntries.Count) entries)"

# Build INDEX_V3.md
$moduleLinks = @()
foreach ($mod in $modules) {
    $content = $utf8.GetString([System.IO.File]::ReadAllBytes("$dir\$mod"))
    $firstH1 = ($content -split "`n") | Where-Object { $_ -match '^# ' } | Select-Object -First 1
    $title = ($firstH1 -replace '^# ', '').Trim()
    $prodName = $mod -replace '_V3\.md$', '.md'
    $moduleLinks += "### [$prodName]($prodName)"
    $moduleLinks += "**$title**"
    $moduleLinks += ""
}

$indexV3 = "# INDEX_V3.md`n`n_SDK Documentation v1.0.2 | Last updated: 2026-03-27_`n`n> This file maps to individual section files. Use COMPLETE_V3.md for single-file loading.`n`n---`n`n" + ($moduleLinks -join "`n")
[System.IO.File]::WriteAllText("$dir\INDEX_V3.md", $indexV3, $utf8NoBom)
Write-Output "Built INDEX_V3.md ($($modules.Count) modules)"

# Verify emoji in COMPLETE_V3
$checkComplete = $utf8.GetString([System.IO.File]::ReadAllBytes("$dir\COMPLETE_V3.md"))
$eggCheck = ($checkComplete -split "`n") | Where-Object { $_ -match "Egg.*Basic access" } | Select-Object -First 1
$eggCheckBytes = $utf8.GetBytes($eggCheck.Substring(0, 10))
Write-Output "`nEmoji verify - Egg bytes in COMPLETE: $($eggCheckBytes[0..7] -join ' ')"
Write-Output "Expected: 124 32 240 159 165 154 32 69"
