<#
V11 Restructure: Rename, merge, reorder modules
#>

$ErrorActionPreference = "Stop"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$root = "C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs-v10"
$src = "$root\modules"
$drafts = "$root\drafts"
$staging = "$root\modules-v11"

if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item $staging -ItemType Directory | Out-Null

# === MAPPING: new number → source file ===
$map = [ordered]@{
    "01-welcome.md"                  = "$drafts\01-welcome-v11.md"
    "02-what-is-basis.md"            = "$drafts\02-what-is-basis-v11.md"
    "03-getting-started.md"          = "$src\17-getting-started.md"
    "04-token-value-incentive.md"    = "$src\05-token-value-incentive.md"
    "05-agent-archetypes.md"         = "$src\04-agent-archetypes.md"
    "06-referral-system.md"          = "$src\09-referral-system.md"
    "07-referral-multiplier.md"      = "$src\07-referral-multiplier.md"
    "08-molt-tiers.md"               = "$src\06-molt-tiers.md"
    "09-the-reef.md"                 = "$src\08-the-reef.md"
    "10-atomic-skills.md"            = "$src\10-atomic-skills.md"
    "11-why-each-action-matters.md"  = "$src\15-why-each-action-matters.md"
    "12-how-everything-works.md"     = "$src\16-how-everything-works.md"
    "13-defi-primitive-playbooks.md" = "$src\12-defi-primitive-playbooks.md"
    "14-strategy-playbooks.md"       = "$drafts\13-strategy-playbooks-merged.md"
    "15-prediction-deep-dive.md"     = "$src\26-prediction-deep-dive.md"
    "16-prediction-arb-engine.md"    = "$src\27-prediction-arb-engine.md"
    "17-fee-cost-reference.md"       = "$src\18-fee-cost-reference.md"
    "18-offchain-api-reference.md"   = "$src\20-offchain-api-reference.md"
    "19-mcp-server.md"               = "$src\11-mcp-server.md"
    "20-what-to-avoid.md"            = "$drafts\28-what-to-avoid-merged.md"
    "21-error-handling.md"           = "$src\19-error-handling.md"
    "22-trust-safety.md"             = "$src\21-trust-safety.md"
    "23-contract-addresses.md"       = "$src\24-contract-addresses.md"
    "24-code-examples.md"            = "$src\25-code-examples.md"
    "25-production-operations.md"    = "$src\29-production-operations.md"
    "26-faq.md"                      = "$src\23-faq.md"
}

# === COPY FILES ===
Write-Host "=== Copying files ===" -ForegroundColor Cyan
foreach ($newName in $map.Keys) {
    $srcFile = $map[$newName]
    $destFile = "$staging\$newName"
    $content = [System.IO.File]::ReadAllText($srcFile, [System.Text.Encoding]::UTF8)
    $content = $content.TrimStart([char]0xFEFF)
    [System.IO.File]::WriteAllText($destFile, $content, $utf8NoBom)
    Write-Host "  $newName <- $(Split-Path $srcFile -Leaf)"
}
Write-Host "$($map.Count) files copied." -ForegroundColor Green

# === BUILD RENAME MAP for cross-references ===
# old filename → new filename
$renameMap = @{
    # Deleted files - point to their new homes
    "00-guide.md" = "01-welcome.md"
    "02-start-here.md" = "01-welcome.md"
    "14-decision-trees.md" = "14-strategy-playbooks.md"
    "22-mistakes-to-avoid.md" = "20-what-to-avoid.md"
    "28-what-to-avoid.md" = "20-what-to-avoid.md"
    
    # Renamed/renumbered files
    "01-welcome.md" = "01-welcome.md"
    "03-what-is-basis.md" = "02-what-is-basis.md"
    "17-getting-started.md" = "03-getting-started.md"
    "05-token-value-incentive.md" = "04-token-value-incentive.md"
    "04-agent-archetypes.md" = "05-agent-archetypes.md"
    "09-referral-system.md" = "06-referral-system.md"
    "07-referral-multiplier.md" = "07-referral-multiplier.md"
    "06-molt-tiers.md" = "08-molt-tiers.md"
    "08-the-reef.md" = "09-the-reef.md"
    "10-atomic-skills.md" = "10-atomic-skills.md"
    "15-why-each-action-matters.md" = "11-why-each-action-matters.md"
    "16-how-everything-works.md" = "12-how-everything-works.md"
    "12-defi-primitive-playbooks.md" = "13-defi-primitive-playbooks.md"
    "13-strategy-playbooks.md" = "14-strategy-playbooks.md"
    "26-prediction-deep-dive.md" = "15-prediction-deep-dive.md"
    "27-prediction-arb-engine.md" = "16-prediction-arb-engine.md"
    "18-fee-cost-reference.md" = "17-fee-cost-reference.md"
    "20-offchain-api-reference.md" = "18-offchain-api-reference.md"
    "11-mcp-server.md" = "19-mcp-server.md"
    "19-error-handling.md" = "21-error-handling.md"
    "21-trust-safety.md" = "22-trust-safety.md"
    "24-contract-addresses.md" = "23-contract-addresses.md"
    "25-code-examples.md" = "24-code-examples.md"
    "29-production-operations.md" = "25-production-operations.md"
    "23-faq.md" = "26-faq.md"
    
    # Also handle references without .md (in link text)
    "21-prediction-market-deep-dive.md" = "15-prediction-deep-dive.md"
    "16-trust-safety.md" = "22-trust-safety.md"
}

# === UPDATE CROSS-REFERENCES ===
Write-Host ""
Write-Host "=== Updating cross-references ===" -ForegroundColor Cyan
$totalReplacements = 0
$filesModified = 0

foreach ($file in (Get-ChildItem $staging -Filter "*.md")) {
    $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
    $original = $content
    
    # Sort by longest key first to avoid partial replacements
    $sortedKeys = $renameMap.Keys | Sort-Object { $_.Length } -Descending
    
    foreach ($old in $sortedKeys) {
        if ($content.Contains($old)) {
            $content = $content.Replace($old, $renameMap[$old])
        }
    }
    
    if ($content -ne $original) {
        [System.IO.File]::WriteAllText($file.FullName, $content, $utf8NoBom)
        $changes = 0
        foreach ($old in $sortedKeys) {
            $oldCount = ([regex]::Matches($original, [regex]::Escape($old))).Count
            $newCount = ([regex]::Matches($content, [regex]::Escape($old))).Count
            $changes += ($oldCount - $newCount)
        }
        $totalReplacements += $changes
        $filesModified++
        Write-Host "  $($file.Name): ~$changes replacements"
    }
}
Write-Host "$filesModified files modified, ~$totalReplacements total replacements." -ForegroundColor Green

# === VERIFY ===
Write-Host ""
Write-Host "=== Verification ===" -ForegroundColor Cyan
$allFiles = Get-ChildItem $staging -Filter "*.md" | Sort-Object Name
Write-Host "Total files: $($allFiles.Count)"

# Check for any remaining old references
$oldPatterns = @("00-guide", "02-start-here", "14-decision-trees", "22-mistakes-to-avoid", "28-what-to-avoid")
foreach ($file in $allFiles) {
    $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
    foreach ($pat in $oldPatterns) {
        if ($content.Contains($pat)) {
            Write-Host "  WARNING: $($file.Name) still references '$pat'" -ForegroundColor Yellow
        }
    }
}

# Check encoding
$corrupted = 0
foreach ($file in $allFiles) {
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    $emDash = 0
    for ($i = 0; $i -lt $bytes.Count - 2; $i++) {
        if ($bytes[$i] -eq 0xE2 -and $bytes[$i+1] -eq 0x80 -and $bytes[$i+2] -eq 0x94) { $emDash++ }
    }
    $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
    $suspicious = ([regex]::Matches($content, '\? (?:See|[A-Z])|\? \?')).Count
    if ($emDash -eq 0 -and $suspicious -gt 2) {
        $corrupted++
        Write-Host "  ENCODING: $($file.Name) may have garbled characters" -ForegroundColor Red
    }
}

if ($corrupted -eq 0) {
    Write-Host "Encoding: all clean" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
Write-Host "Staging at: $staging"
Write-Host "Review, then replace modules/ with modules-v11/"
