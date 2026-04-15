# --- CONFIGURATION ---
$DevDir      = "C:\Users\Luis Cherubini\Dropbox\Softwares\Github\cherub-suite"
$DistDir     = "C:\Users\Luis Cherubini\Dropbox\Softwares\Github\dist"
$StageDir    = "$DistDir\temp_stage" # Temporary clean room
$BlenderExe  = "C:\Users\Luis Cherubini\Dropbox\Softwares\Blender\Blender_versions\blender_dev\blender-5.1.0-windows-x64\blender.exe"
$AddonName   = "cherub_suite"

# --- 1. CLEANUP ---
Write-Host "Cleaning up previous distribution files..." -ForegroundColor Cyan
if (Test-Path "$DistDir\$AddonName.zip") { Remove-Item "$DistDir\$AddonName.zip" }
if (Test-Path $StageDir) { Remove-Item -Recurse -Force $StageDir }

# --- 2. PRECISE STAGING ---
Write-Host "Creating clean folder structure..." -ForegroundColor Green
New-Item -ItemType Directory -Path $StageDir | Out-Null

# Copy everything EXCEPT the junk
$ExcludeList = @(".git*", "*.zip", "__pycache__", ".vscode", ".gitignore", "tests", "ship_it.ps1")
Copy-Item -Path "$DevDir\*" -Destination $StageDir -Recurse -Exclude $ExcludeList

# --- 3. PACKAGING ---
Write-Host "Zipping extension..." -ForegroundColor Green
# Zipping the contents of the stage folder ensures the manifest is at the root
Compress-Archive -Path "$StageDir\*" -DestinationPath "$DistDir\$AddonName.zip" -Force

# Cleanup the stage
Remove-Item -Recurse -Force $StageDir

# --- 4. BLENDER REPOSITORY INDEX ---
Write-Host "Updating local repository index..." -ForegroundColor Yellow
Set-Location $DistDir
& $BlenderExe --command extension build-repository .

# --- 5. DEPLOYMENT ---
Write-Host "Pushing to GitHub distribution repo..." -ForegroundColor Magenta
git add .
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "Deployment: $Timestamp"
git push origin main

Write-Host "Deployment successful! Folder structure preserved." -ForegroundColor Green
Set-Location $DevDir