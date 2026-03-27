$dir = "C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# Read COMPLETE_V2.md correctly
$v2Text = [System.IO.File]::ReadAllText("$dir\COMPLETE_V2.md", [System.Text.Encoding]::UTF8)
$v2Lines = $v2Text -split "`r?`n"

Write-Output "COMPLETE_V2 total lines: $($v2Lines.Count)"

# Section boundaries (1-indexed)
$sections = @(
    @(9, 80, "00-welcome"),
    @(81, 252, "01-what-is-basis"),
    @(253, 484, "02-archetypes"),
    @(485, 633, "03-token-value"),
    @(634, 2246, "04-atomic-skills"),
    @(2247, 2423, "05-strategies"),
    @(2424, 2512, "06-decision-trees"),
    @(2513, 2609, "07-why"),
    @(2610, 2880, "08-how"),
    @(2881, 3198, "09-getting-started"),
    @(3199, 3329, "10-fees"),
    @(3330, 3421, "11-errors"),
    @(3422, 4500, "12-api-reference"),
    @(4501, 4619, "13-trust-safety"),
    @(4620, 4674, "14-mistakes"),
    @(4675, 4749, "15-faq"),
    @(4750, 4827, "16-contract-addresses"),
    @(4828, 5540, "17-examples"),
    @(5541, 5764, "18-prediction-market-deep-dive"),
    @(5765, 5849, "19-what-to-avoid"),
    @(5850, $v2Lines.Count, "20-production-ops")
)

foreach ($sec in $sections) {
    $start = $sec[0] - 1
    $end = $sec[1] - 1
    $name = $sec[2]
    $content = ($v2Lines[$start..$end] -join "`n").Trim()
    
    # Write V2
    [System.IO.File]::WriteAllText("$dir\${name}_V2.md", $content, $utf8NoBom)
    # Write V3 (will be edited later)
    [System.IO.File]::WriteAllText("$dir\${name}_V3.md", $content, $utf8NoBom)
    
    Write-Output "Wrote ${name}_V2.md and _V3.md ($($end - $start + 1) lines)"
}

# Verify emoji
$check = [System.IO.File]::ReadAllText("$dir\02-archetypes_V2.md", [System.Text.Encoding]::UTF8)
$eggLine = ($check -split "`n") | Where-Object { $_ -match "Egg.*Basic" } | Select-Object -First 1
Write-Output "`nVerification - Egg line: $eggLine"
