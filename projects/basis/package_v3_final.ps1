$dir = "C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs"
$outDir = "C:\Users\Never\.openclaw\workspace\projects\basis"
$zipPath = Join-Path $outDir "basis-docs-v1.0.2.zip"
$stagingDir = Join-Path $outDir "zip-staging"

if (Test-Path $stagingDir) { Remove-Item $stagingDir -Recurse -Force }
New-Item -ItemType Directory -Path "$stagingDir\versioned" -Force | Out-Null
New-Item -ItemType Directory -Path "$stagingDir\production" -Force | Out-Null

$modules = @(
    "00-welcome","01-what-is-basis","02-archetypes","03-token-value",
    "04-atomic-skills","05-strategies","06-decision-trees","07-why",
    "08-how","09-getting-started","10-fees","11-errors",
    "12-api-reference","13-trust-safety","14-mistakes","15-faq",
    "16-contract-addresses","17-examples","18-prediction-market-deep-dive",
    "19-what-to-avoid","20-production-ops"
)

foreach ($mod in $modules) {
    Copy-Item "$dir\${mod}_V3.md" "$stagingDir\versioned\${mod}_V3.md"
    Copy-Item "$dir\${mod}_V3.md" "$stagingDir\production\${mod}.md"
}

Copy-Item "$dir\COMPLETE_V3.md" "$stagingDir\versioned\COMPLETE_V3.md"
Copy-Item "$dir\COMPLETE_V3.md" "$stagingDir\production\COMPLETE.md"
Copy-Item "$dir\COMPLETE_INDEX_V3.md" "$stagingDir\versioned\COMPLETE_INDEX_V3.md"
Copy-Item "$dir\COMPLETE_INDEX_V3.md" "$stagingDir\production\COMPLETE_INDEX.md"
Copy-Item "$dir\INDEX_V3.md" "$stagingDir\versioned\INDEX_V3.md"
Copy-Item "$dir\INDEX_V3.md" "$stagingDir\production\INDEX.md"

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path "$stagingDir\*" -DestinationPath $zipPath

Remove-Item $stagingDir -Recurse -Force

$zipSize = [math]::Round((Get-Item $zipPath).Length / 1KB, 1)
$vCount = (Add-Type -Assembly System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::OpenRead($zipPath).Entries.Count)
Write-Output "Created: basis-docs-v1.0.2.zip ($zipSize KB, $vCount files)"
