$dir = "C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$utf8 = [System.Text.Encoding]::UTF8

$modules = @(
    "00-welcome_V5.md","01-what-is-basis_V5.md","02-archetypes_V5.md",
    "03-token-value_V5.md","04-the-reef_V5.md","05-referral-system_V5.md",
    "06-atomic-skills_V5.md","07-mcp_V5.md","08-strategies_V5.md",
    "09-decision-trees_V5.md","10-why_V5.md","11-how_V5.md",
    "12-getting-started_V5.md","13-fees_V5.md","14-errors_V5.md",
    "15-api-reference_V5.md","16-trust-safety_V5.md","17-mistakes_V5.md",
    "18-faq_V5.md","19-contract-addresses_V5.md","20-examples_V5.md",
    "21-prediction-market-deep-dive_V5.md","22-what-to-avoid_V5.md",
    "23-production-ops_V5.md"
)

# Verify all modules exist
foreach ($mod in $modules) {
    if (-not (Test-Path "$dir\$mod")) {
        Write-Error "MISSING: $mod"
        exit 1
    }
}
Write-Output "All $($modules.Count) modules found."

# Build COMPLETE_V5.md
$header = "# Basis - Complete Agent Guide`n`n_SDK Documentation v1.0.2 | Phase 1: Founding Lobster | Last updated: 2026-03-31_`n`n_All sections concatenated. Load this single file for full platform context._`n`n---"

$parts = @($header)
foreach ($mod in $modules) {
    $content = $utf8.GetString([System.IO.File]::ReadAllBytes("$dir\$mod")).Trim()
    if ($content[0] -eq [char]0xFEFF) { $content = $content.Substring(1) }
    $parts += $content
}

$complete = $parts -join "`n`n---`n`n"
[System.IO.File]::WriteAllText("$dir\COMPLETE_V5.md", $complete, $utf8NoBom)
$completeLines = ($complete -split "`n").Count
$completeBytes = [System.IO.File]::ReadAllBytes("$dir\COMPLETE_V5.md").Length
Write-Output "Built COMPLETE_V5.md ($completeLines lines, $completeBytes bytes)"

# Build COMPLETE_INDEX_V5.md
$lines = $complete -split "`n"
$inCode = $false
$indexEntries = @()
$prevLineNum = 0
for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    if ($line.Trim() -match '^```') { $inCode = -not $inCode }
    if (-not $inCode -and $line -match '^(#{1,3}) (.+)$') {
        $level = $matches[1].Length
        $title = $matches[2].Trim()
        $lineNum = $i + 1
        # Find end of this section (next heading at same or higher level, or EOF)
        $endLine = $lines.Count
        for ($j = $i + 1; $j -lt $lines.Count; $j++) {
            $nextLine = $lines[$j]
            if ($nextLine.Trim() -match '^```') { $inCode = -not $inCode; continue }
            if (-not $inCode -and $nextLine -match '^(#{1,3}) ') {
                $nextLevel = $matches[1].Length
                if ($nextLevel -le $level) { $endLine = $j; break }
            }
        }
        $prefix = if ($level -eq 1) { "" } elseif ($level -eq 2) { "  " } else { "    " }
        $arrow = if ($level -gt 1) { [char]0x2192 + " " } else { "" }
        $indexEntries += "| $lineNum" + [char]0x2013 + "$endLine | $prefix$arrow$title |"
    }
}

$indexHeader = @"
# COMPLETE_INDEX_V5.md

_SDK Documentation v1.0.2 | Last updated: 2026-03-31_

Line-range index into [``COMPLETE_V5.md``](COMPLETE_V5.md).
Total lines: $completeLines | Total size: $("{0:N0}" -f $completeBytes) bytes

---

| Lines | Section |
|-------|---------|
"@

$indexContent = $indexHeader + "`n" + ($indexEntries -join "`n")
[System.IO.File]::WriteAllText("$dir\COMPLETE_INDEX_V5.md", $indexContent, $utf8NoBom)
Write-Output "Built COMPLETE_INDEX_V5.md ($($indexEntries.Count) entries)"

# Build INDEX_V5.md from INDEX_V4 pattern (update header refs only)
$indexV4 = $utf8.GetString([System.IO.File]::ReadAllBytes("$dir\INDEX_V4.md"))
$indexV5 = $indexV4 -replace '_V4\.md', '_V5.md' -replace 'COMPLETE_INDEX_V4', 'COMPLETE_INDEX_V5' -replace 'COMPLETE_V4', 'COMPLETE_V5' -replace 'v1\.0\.2 \| Last updated: 2026-03-27', 'v1.0.2 | Last updated: 2026-03-31'
# Update MCP entry
$indexV5 = $indexV5 -replace '141 tools across 13 modules', '172 tools across 15 modules'
$indexV5 = $indexV5 -replace '141 MCP tools, 13 modules \(Trading, Token Creation, Prediction Markets, Staking/Vault, Loans, Portfolio/Data, Agent Identity, Vesting, Order Book, Taxes, Reef, Private Markets, Extras\)', '172 MCP tools, 15 modules (Trading, Token Creation, Prediction Markets, Staking/Vault, Loans, Portfolio/Data, Agent Identity, Vesting, Order Book, Taxes, The Reef, Private Markets, Utility, Resolution Deep, Extras)'
$indexV5 = $indexV5 -replace 'Full MCP integration guide .+ 141 tools', 'Full MCP integration guide — 172 tools across 15 modules, architecture overview'
[System.IO.File]::WriteAllText("$dir\INDEX_V5.md", $indexV5, $utf8NoBom)
Write-Output "Built INDEX_V5.md"

# Build llms-full.txt (copy of COMPLETE)
[System.IO.File]::Copy("$dir\COMPLETE_V5.md", "$dir\llms-full.txt", $true)
Write-Output "Built llms-full.txt (copy of COMPLETE_V5.md)"

# Update llms.txt
$llms = $utf8.GetString([System.IO.File]::ReadAllBytes("$dir\llms.txt"))
$llms = $llms -replace 'Last updated: 2026-03-27', 'Last updated: 2026-03-31'
[System.IO.File]::WriteAllText("$dir\llms.txt", $llms, $utf8NoBom)
Write-Output "Updated llms.txt"

Write-Output "`n=== BUILD COMPLETE ==="
