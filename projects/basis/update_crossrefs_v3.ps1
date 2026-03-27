$dir = "C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs"

# Old name -> New name mapping (version-agnostic, as they'll appear in cross-refs)
$map = @{
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
# Note: 00-welcome.md, 01-what-is-basis.md, 02-archetypes.md stay the same

# Process all V3 files (but NOT COMPLETE_V3.md or COMPLETE_INDEX_V3.md - those get regenerated)
Get-ChildItem $dir -Filter "*_V3.md" | Where-Object { $_.Name -notmatch "^COMPLETE" } | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    $changed = $false
    
    # Sort by key length descending to avoid partial replacements (e.g., 03- before 13-)
    # Actually, since we're matching exact filenames in brackets, we need to be careful
    # Process replacements from highest old number to lowest to avoid double-replacement
    $sortedKeys = $map.Keys | Sort-Object { [int]($_ -split '-')[0] } -Descending
    
    foreach ($old in $sortedKeys) {
        $new = $map[$old]
        if ($content.Contains($old)) {
            $content = $content.Replace($old, $new)
            $changed = $true
        }
    }
    
    if ($changed) {
        Set-Content -Path $_.FullName -Value $content -NoNewline -Encoding UTF8
        Write-Output "Updated cross-refs in $($_.Name)"
    } else {
        Write-Output "No changes needed in $($_.Name)"
    }
}
