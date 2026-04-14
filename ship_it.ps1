# --- CONFIGURATION ---
$distRepoPath = "../extensions"  # This looks one folder up and into the storefront
$addonName = "cherub_suite"

Write-Host "🚀 Preparing to ship Cherub's Blender Toolset..." -ForegroundColor Cyan

# 1. CLEAN PREVIOUS BUILDS
if (Test-Path "build_temp") { Remove-Item -Recurse -Force "build_temp" }
New-Item -ItemType Directory -Path "build_temp"

# 2. SELECTIVE COPYING (The "No Junk" Rule)
# We exclude the stuff you need for dev, but users don't need for Blender.
$excludeList = @(".git*", ".vscode", "build_temp", "ship_it.ps1", "*.zip", "__pycache__", "RELEASE.md")
Get-ChildItem -Path "." -Exclude $excludeList | Copy-Item -Destination "build_temp" -Recurse

# 3. PACKAGING
Write-Host "📦 Zipping extension for distribution..." -ForegroundColor Yellow
$zipPath = "$distRepoPath/$addonName.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }
Compress-Archive -Path "build_temp/*" -DestinationPath $zipPath

# 4. SERVER GENERATE (The Blender "Boss" Command)
Write-Host "📝 Updating index.json in the extensions repo..." -ForegroundColor Yellow
Push-Location $distRepoPath
# This calculates hashes and sizes automatically
blender --command extension server-generate --repo-dir="."

# 5. SYNC TO GITHUB
Write-Host "🌐 Pushing to https://luischerub.github.io/extensions/ ..." -ForegroundColor Cyan
git add .
git commit -m "Release: Cherub Suite Update $(Get-Date -Format 'yyyy-MM-dd')"
git push origin main
Pop-Location

# 6. FINISH
Remove-Item -Recurse -Force "build_temp"
Write-Host "✨ Bacchiri! Cherub's Blender Toolset is updated." -ForegroundColor Green