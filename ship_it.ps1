# --- CONFIGURATION ---
$DevDir      = "C:\Users\Luis Cherubini\Dropbox\Softwares\Github\cherub-suite"
$DistDir     = "C:\Users\Luis Cherubini\Dropbox\Softwares\Github\dist"
# We move the stage to a local temp folder that Dropbox doesn't watch
$StageDir    = "$env:TEMP\cherub_suite_stage" 
$BlenderExe  = "C:\Users\Luis Cherubini\Dropbox\Softwares\Blender\Blender_versions\blender_dev\blender-5.1.0-windows-x64\blender.exe"
$AddonName   = "cherub_suite"

# --- 1. CLEANUP ---
Write-Host "Cleaning up previous build files..." -ForegroundColor Cyan
if (Test-Path "$DistDir\$AddonName.zip") { Remove-Item "$DistDir\$AddonName.zip" -Force }
# Wipe old stage if it exists
if (Test-Path $StageDir) { Remove-Item -Recurse -Force $StageDir -ErrorAction SilentlyContinue }

# --- 2. PRECISE STAGING ---
Write-Host "Creating clean local stage (Outside Dropbox)..." -ForegroundColor Green
New-Item -ItemType Directory -Path $StageDir -Force | Out-Null

$ExcludeList = @(".git*", "*.zip", "__pycache__", ".vscode", ".gitignore", "tests", "ship_it.ps1")
Copy-Item -Path "$DevDir\*" -Destination $StageDir -Recurse -Exclude $ExcludeList

# --- 3. PACKAGING ---
Write-Host "Zipping extension..." -ForegroundColor Green
# We zip FROM the local temp TO the Dropbox dist folder
Compress-Archive -Path "$StageDir\*" -DestinationPath "$DistDir\$AddonName.zip" -Force

# Now it's safe to remove the local stage
Remove-Item -Recurse -Force $StageDir -ErrorAction SilentlyContinue

# --- 4. BLENDER REPOSITORY INDEX ---
Write-Host "Updating repository index..." -ForegroundColor Yellow
Set-Location $DistDir

# Clean the old one first
if (Test-Path "index.json") { Remove-Item "index.json" -Force }

# Use the full path variable to ensure Blender sees the argument
& $BlenderExe --command extension server-generate --repo-dir "$DistDir"

# --- 5. DEPLOYMENT ---
Write-Host "Pushing to GitHub..." -ForegroundColor Magenta
git add .
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "Deployment: $Timestamp"
git push origin main

Write-Host "Deployment successful! Everything is Sukkiri!" -ForegroundColor Green
Set-Location $DevDir