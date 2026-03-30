#!/usr/bin/env pwsh
<#
  V4 Cross-Reference Update Script
  
  Two passes:
  - Pass 1: Reef & Referral refs that changed NAME (from trust-safety subsections → own modules)
  - Pass 2: Pure number shifts for renamed modules
  
  DRY RUN by default. Pass -Apply to actually write changes.
  Usage:
    .\update_crossrefs_v4.ps1          # dry run - shows what would change
    .\update_crossrefs_v4.ps1 -Apply   # applies changes
#>
param([switch]$Apply)

$dir = "C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs"
$files = Get-ChildItem "$dir\*_V4.md"
$totalChanges = 0

foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw -Encoding UTF8
    $original = $content
    $fileChanges = 0

    # ============================================================
    # PASS 1: Reef & Referral — name+number changes
    # These were subsections of 13-trust-safety, now own modules
    # Must run BEFORE Pass 2 (which shifts 13→16)
    # ============================================================

    # 13-trust-safety — The Reef → 04-the-reef
    $content = $content -replace '\[13-trust-safety\.md\s*—\s*The Reef\]\(13-trust-safety\.md\)', '[04-the-reef.md](04-the-reef.md)'

    # 13-trust-safety — Referral System → 05-referral-system
    $content = $content -replace '\[13-trust-safety\.md\s*—\s*Referral System\]\(13-trust-safety\.md\)', '[05-referral-system.md](05-referral-system.md)'

    # 13-trust-safety — Referral Kickback → 05-referral-system — Referral Kickback
    $content = $content -replace '\[13-trust-safety\.md\s*—\s*Referral Kickback\]\(13-trust-safety\.md\)', '[05-referral-system.md — Referral Kickback](05-referral-system.md)'

    # ============================================================
    # PASS 2: Pure number shifts (old V3 numbers → new V4 numbers)
    # Order: highest old number first to avoid double-replacement
    # e.g. 20→23 before 10→13, so "20-" doesn't get caught by "0-"
    # ============================================================

    # Old 20 → New 23
    $content = $content -replace '20-production-ops\.md', '23-production-ops.md'
    $content = $content -replace '\(20-production-ops\)', '(23-production-ops)'

    # Old 19 → New 22
    $content = $content -replace '19-what-to-avoid\.md', '22-what-to-avoid.md'
    $content = $content -replace '\(19-what-to-avoid\)', '(22-what-to-avoid)'

    # Old 18 → New 21
    $content = $content -replace '18-prediction-market-deep-dive\.md', '21-prediction-market-deep-dive.md'
    $content = $content -replace '\(18-prediction-market-deep-dive\)', '(21-prediction-market-deep-dive)'

    # Old 17 → New 20
    $content = $content -replace '17-examples\.md', '20-examples.md'
    $content = $content -replace '\(17-examples\)', '(20-examples)'

    # Old 16 → New 19
    $content = $content -replace '16-contract-addresses\.md', '19-contract-addresses.md'
    $content = $content -replace '\(16-contract-addresses\)', '(19-contract-addresses)'

    # Old 15 → New 18
    $content = $content -replace '15-faq\.md', '18-faq.md'
    $content = $content -replace '\(15-faq\)', '(18-faq)'

    # Old 14 → New 17
    $content = $content -replace '14-mistakes\.md', '17-mistakes.md'
    $content = $content -replace '\(14-mistakes\)', '(17-mistakes)'

    # Old 13 → New 16 (remaining trust-safety refs after Pass 1 extracted Reef/Referral)
    $content = $content -replace '13-trust-safety\.md', '16-trust-safety.md'
    $content = $content -replace '\(13-trust-safety\)', '(16-trust-safety)'

    # Old 12 → New 15
    $content = $content -replace '12-api-reference\.md', '15-api-reference.md'
    $content = $content -replace '\(12-api-reference\)', '(15-api-reference)'

    # Old 11 → New 14
    $content = $content -replace '11-errors\.md', '14-errors.md'
    $content = $content -replace '\(11-errors\)', '(14-errors)'

    # Old 10 → New 13
    $content = $content -replace '10-fees\.md', '13-fees.md'
    $content = $content -replace '\(10-fees\)', '(13-fees)'

    # Old 09 → New 12
    $content = $content -replace '09-getting-started\.md', '12-getting-started.md'
    $content = $content -replace '\(09-getting-started\)', '(12-getting-started)'

    # Old 08 → New 11
    $content = $content -replace '08-how\.md', '11-how.md'
    $content = $content -replace '\(08-how\)', '(11-how)'

    # Old 07 → New 10
    $content = $content -replace '07-why\.md', '10-why.md'
    $content = $content -replace '\(07-why\)', '(10-why)'

    # Old 06 → New 09
    $content = $content -replace '06-decision-trees\.md', '09-decision-trees.md'
    $content = $content -replace '\(06-decision-trees\)', '(09-decision-trees)'

    # Old 05 → New 08
    $content = $content -replace '05-strategies\.md', '08-strategies.md'
    $content = $content -replace '\(05-strategies\)', '(08-strategies)'

    # Old 04 → New 06
    $content = $content -replace '04-atomic-skills\.md', '06-atomic-skills.md'
    $content = $content -replace '\(04-atomic-skills\)', '(06-atomic-skills)'

    # ============================================================
    # SKIP: 00, 01, 02, 03 — these don't change numbers
    # SKIP: New modules (04-the-reef, 05-referral-system, 07-mcp)
    #        — already have correct refs from creation
    # ============================================================

    # Count changes
    if ($content -ne $original) {
        # Count line-level diffs
        $origLines = $original -split "`n"
        $newLines = $content -split "`n"
        for ($i = 0; $i -lt [Math]::Max($origLines.Count, $newLines.Count); $i++) {
            if ($i -ge $origLines.Count -or $i -ge $newLines.Count -or $origLines[$i] -ne $newLines[$i]) {
                $fileChanges++
            }
        }
        $totalChanges += $fileChanges
        Write-Output "  $($file.Name): $fileChanges line(s) changed"
        
        if ($Apply) {
            Set-Content -Path $file.FullName -Value $content -NoNewline -Encoding UTF8
        }
    }
}

Write-Output ""
if ($Apply) {
    Write-Output "APPLIED: $totalChanges total line changes across all files."
} else {
    Write-Output "DRY RUN: $totalChanges total line changes would be made."
    Write-Output "Run with -Apply to commit changes."
}
