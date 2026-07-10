$ErrorActionPreference = "Stop"
$Root = Get-Location
$Source = Join-Path $PSScriptRoot "files"
Write-Host "Copying replacement files into $Root"
Copy-Item -Path (Join-Path $Source "*") -Destination $Root -Recurse -Force
Write-Host "Done. Now run: docker compose up --build"
