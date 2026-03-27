$dir = "C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs"
$outDir = "C:\Users\Never\.openclaw\workspace\projects\basis"
$zipPath = Join-Path $outDir "basis-docs-v1.0.2.zip"
$stagingDir = Join-Path $outDir "zip-staging"

# Clean staging
if (Test-Path $stagingDir) { Remove-Item $stagingDir -Recurse -Force }
New-Item -ItemType Directory -Path "$stagingDir\versioned" | Out-Null
New-Item -ItemType Directory -Path "$stagingDir\production" | Out-Null

$modules = @(
    "00-welcome", "01-what-is-basis", "02-archetypes", "03-token-value",
    "04-atomic-skills", "05-strategies", "06-decision-trees", "07-why",
    "08-how", "09-getting-started", "10-fees", "11-errors",
    "12-api-reference", "13-trust-safety", "14-mistakes", "15-faq",
    "16-contract-addresses", "17-examples", "18-prediction-market-deep-dive",
    "19-what-to-avoid", "20-production-ops"
)

# Copy individual modules
foreach ($mod in $modules) {
    $v3File = Join-Path $dir "${mod}_V3.md"
    $prodName = "${mod}.md"
    
    # versioned/
    Copy-Item $v3File (Join-Path "$stagingDir\versioned" "${mod}_V3.md")
    # production/ (same content, plain name)
    Copy-Item $v3File (Join-Path "$stagingDir\production" $prodName)
}

# Copy index files
Copy-Item (Join-Path $dir "COMPLETE_V3.md") "$stagingDir\versioned\COMPLETE_V3.md"
Copy-Item (Join-Path $dir "COMPLETE_V3.md") "$stagingDir\production\COMPLETE.md"

Copy-Item (Join-Path $dir "COMPLETE_INDEX_V3.md") "$stagingDir\versioned\COMPLETE_INDEX_V3.md"
Copy-Item (Join-Path $dir "COMPLETE_INDEX_V3.md") "$stagingDir\production\COMPLETE_INDEX.md"

Copy-Item (Join-Path $dir "INDEX_V3.md") "$stagingDir\versioned\INDEX_V3.md"
Copy-Item (Join-Path $dir "INDEX_V3.md") "$stagingDir\production\INDEX.md"

# Zip it
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path "$stagingDir\*" -DestinationPath $zipPath

# Cleanup staging
Remove-Item $stagingDir -Recurse -Force

$zipSize = [math]::Round((Get-Item $zipPath).Length / 1KB, 1)
Write-Output "Created: basis-docs-v1.0.2.zip ($zipSize KB)"
Write-Output "  versioned/  — $($modules.Count + 3) files (V3-named)"
Write-Output "  production/ — $($modules.Count + 3) files (plain names, deploy-ready)"
