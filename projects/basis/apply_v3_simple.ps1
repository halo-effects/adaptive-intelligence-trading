$dir = "C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# Cross-reference renumbering
$refMap = @{
    "03-atomic-skills.md" = "04-atomic-skills.md"
    "04-strategies.md" = "05-strategies.md"
    "05-decision-trees.md" = "06-decision-trees.md"
    "06-why.md" = "07-why.md"
    "07-how.md" = "08-how.md"
    "08-getting-started.md" = "09-getting-started.md"
    "09-fees.md" = "10-fees.md"
    "10-errors.md" = "11-errors.md"
    "11-api-reference.md" = "12-api-reference.md"
    "12-trust-safety.md" = "13-trust-safety.md"
    "13-mistakes.md" = "14-mistakes.md"
    "14-faq.md" = "15-faq.md"
    "15-contract-addresses.md" = "16-contract-addresses.md"
    "16-examples.md" = "17-examples.md"
    "17-prediction-market-deep-dive.md" = "18-prediction-market-deep-dive.md"
    "18-what-to-avoid.md" = "19-what-to-avoid.md"
}

$sortedKeys = $refMap.Keys | Sort-Object { [int]($_ -split '-')[0] } -Descending

Get-ChildItem $dir -Filter "*_V3.md" | Where-Object { $_.Name -notmatch "^COMPLETE" -and $_.Name -ne "INDEX_V3.md" } | ForEach-Object {
    $content = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
    $changed = $false
    foreach ($old in $sortedKeys) {
        $new = $refMap[$old]
        if ($content.Contains($old)) {
            $content = $content.Replace($old, $new)
            $changed = $true
        }
    }
    if ($changed) {
        [System.IO.File]::WriteAllText($_.FullName, $content, $utf8NoBom)
        Write-Output "Updated refs in $($_.Name)"
    }
}

# Version bump
$welcome = [System.IO.File]::ReadAllText("$dir\00-welcome_V3.md", [System.Text.Encoding]::UTF8)
$welcome = $welcome.Replace("v1.0.1", "v1.0.2").Replace("2026-03-24", "2026-03-27")
[System.IO.File]::WriteAllText("$dir\00-welcome_V3.md", $welcome, $utf8NoBom)
Write-Output "Version bumped in 00-welcome_V3.md"

# Archetype count
$arch = [System.IO.File]::ReadAllText("$dir\02-archetypes_V3.md", [System.Text.Encoding]::UTF8)
$arch = $arch.Replace("All 6 agent archetypes", "All 7 agent archetypes (including the Super Referrer meta-archetype)")
[System.IO.File]::WriteAllText("$dir\02-archetypes_V3.md", $arch, $utf8NoBom)
Write-Output "Updated archetype count"

# Strategy count
$strat = [System.IO.File]::ReadAllText("$dir\05-strategies_V3.md", [System.Text.Encoding]::UTF8)
$strat = $strat.Replace("All 5 strategy playbooks", "All 6 strategy playbooks")
[System.IO.File]::WriteAllText("$dir\05-strategies_V3.md", $strat, $utf8NoBom)
Write-Output "Updated strategy count"

# Decision tree count
$dt = [System.IO.File]::ReadAllText("$dir\06-decision-trees_V3.md", [System.Text.Encoding]::UTF8)
$dt = $dt.Replace("4 decision trees", "5 decision trees")
[System.IO.File]::WriteAllText("$dir\06-decision-trees_V3.md", $dt, $utf8NoBom)
Write-Output "Updated decision tree count"

# Fix Reef reference in token value
$tv = [System.IO.File]::ReadAllText("$dir\03-token-value_V3.md", [System.Text.Encoding]::UTF8)
$tv = $tv.Replace("The Reef (the on-platform JSON feed)", "The Reef (launchonbasis.com/reef)")
[System.IO.File]::WriteAllText("$dir\03-token-value_V3.md", $tv, $utf8NoBom)
Write-Output "Fixed Reef reference in token value"

Write-Output "`nSimple replacements done. Use edit tool for complex content insertions."
