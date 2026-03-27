$src = "C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs\COMPLETE_V2.md"
$outDir = "C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs"
$lines = Get-Content $src

# Define section boundaries (1-indexed line numbers from COMPLETE_V2.md)
# Format: start_line, end_line, filename
$sections = @(
    @(9, 80, "00-welcome_V2.md"),
    @(81, 252, "01-what-is-basis_V2.md"),
    @(253, 484, "02-archetypes_V2.md"),        # Archetypes WITHOUT token value section
    @(485, 633, "03-token-value_V2.md"),        # Token Value & Incentive Structure (NEW module)
    @(634, 2246, "04-atomic-skills_V2.md"),
    @(2247, 2423, "05-strategies_V2.md"),
    @(2424, 2512, "06-decision-trees_V2.md"),
    @(2513, 2609, "07-why_V2.md"),
    @(2610, 2880, "08-how_V2.md"),
    @(2881, 3198, "09-getting-started_V2.md"),
    @(3199, 3329, "10-fees_V2.md"),
    @(3330, 3421, "11-errors_V2.md"),
    @(3422, 4500, "12-api-reference_V2.md"),
    @(4501, 4619, "13-trust-safety_V2.md"),
    @(4620, 4674, "14-mistakes_V2.md"),
    @(4675, 4749, "15-faq_V2.md"),
    @(4750, 4827, "16-contract-addresses_V2.md"),
    @(4828, 5540, "17-examples_V2.md"),
    @(5541, 5764, "18-prediction-market-deep-dive_V2.md"),
    @(5765, 5849, "19-what-to-avoid_V2.md"),
    @(5850, 6206, "20-production-ops_V2.md")
)

foreach ($sec in $sections) {
    $start = $sec[0] - 1  # Convert to 0-indexed
    $end = $sec[1] - 1
    $fname = $sec[2]
    $content = $lines[$start..$end] -join "`n"
    # Trim leading/trailing blank lines
    $content = $content.Trim()
    $outPath = Join-Path $outDir $fname
    Set-Content -Path $outPath -Value $content -Encoding UTF8
    Write-Output "Wrote $fname ($($end - $start + 1) lines)"
}

Write-Output "`nDone! Extracted $($sections.Count) modules."
