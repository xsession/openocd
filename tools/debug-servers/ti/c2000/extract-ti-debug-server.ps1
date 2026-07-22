param(
    [string]$CcsRoot = "C:\ti\ccs2040\ccs",
    [string]$Destination = "",
    [ValidateSet("Full", "C2000", "None")]
    [string]$TargetDbMode = "Full",
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
    $dir = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
    return $dir
}

function Copy-Tree {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Target
    )

    if (-not (Test-Path -LiteralPath $Source)) {
        throw "Required TI debug-server path was not found: $Source"
    }

    New-Item -ItemType Directory -Force -Path $Target | Out-Null
    Copy-Item -Path (Join-Path $Source "*") -Destination $Target -Recurse -Force
}

function Copy-IfExists {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Target
    )

    if (Test-Path -LiteralPath $Source) {
        Copy-Tree -Source $Source -Target $Target
    }
}

function Copy-TargetDbC2000 {
    param(
        [Parameter(Mandatory = $true)][string]$SourceRoot,
        [Parameter(Mandatory = $true)][string]$TargetRoot
    )

    New-Item -ItemType Directory -Force -Path $TargetRoot | Out-Null

    foreach ($file in Get-ChildItem -LiteralPath $SourceRoot -File -ErrorAction SilentlyContinue) {
        Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $TargetRoot $file.Name) -Force
    }

    foreach ($dir in "Modules", "routers", "connections", "drivers", "cpus", "boarddat") {
        Copy-IfExists -Source (Join-Path $SourceRoot $dir) -Target (Join-Path $TargetRoot $dir)
    }

    $deviceTarget = Join-Path $TargetRoot "devices"
    New-Item -ItemType Directory -Force -Path $deviceTarget | Out-Null
    $patterns = @("c28*.xml", "f28*.xml", "tms320f28*.xml", "*c2000*.xml")
    foreach ($pattern in $patterns) {
        Get-ChildItem -LiteralPath (Join-Path $SourceRoot "devices") -File -Filter $pattern -ErrorAction SilentlyContinue |
            Copy-Item -Destination $deviceTarget -Force
    }

    $boardTarget = Join-Path $TargetRoot "boards"
    New-Item -ItemType Directory -Force -Path $boardTarget | Out-Null
    Get-ChildItem -LiteralPath (Join-Path $SourceRoot "boards") -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match "c2000|f28|launchxl|controlcard|xds100|xds110" } |
        Copy-Item -Destination $boardTarget -Force
}

$repoRoot = Resolve-RepoRoot
if ([string]::IsNullOrWhiteSpace($Destination)) {
    $Destination = Join-Path $repoRoot "tools\debug-servers\ti\c2000\vendor\ccs-debugserver-20.4.0"
}

$ccsRootPath = (Resolve-Path -LiteralPath $CcsRoot).Path
$ccsBase = Join-Path $ccsRootPath "ccs_base"
if (-not (Test-Path -LiteralPath $ccsBase)) {
    throw "CCS root must contain ccs_base: $ccsRootPath"
}

$destinationFull = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Destination)
$vendorRoot = Join-Path $repoRoot "tools\debug-servers\ti\c2000\vendor"
if (-not $destinationFull.StartsWith($vendorRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Destination must stay under the ignored TI vendor folder: $vendorRoot"
}

if ((Test-Path -LiteralPath $destinationFull) -and -not $Force) {
    throw "Destination already exists. Pass -Force to replace it: $destinationFull"
}

if (Test-Path -LiteralPath $destinationFull) {
    Remove-Item -LiteralPath $destinationFull -Recurse -Force
}

$localCcsBase = Join-Path $destinationFull "ccs_base"
New-Item -ItemType Directory -Force -Path $localCcsBase | Out-Null

Copy-Tree -Source (Join-Path $ccsBase "DebugServer") -Target (Join-Path $localCcsBase "DebugServer")
Copy-Tree -Source (Join-Path $ccsBase "emulation") -Target (Join-Path $localCcsBase "emulation")
Copy-Tree -Source (Join-Path $ccsBase "common\bin") -Target (Join-Path $localCcsBase "common\bin")
Copy-Tree -Source (Join-Path $ccsBase "common\uscif") -Target (Join-Path $localCcsBase "common\uscif")

if ($TargetDbMode -eq "Full") {
    Copy-Tree -Source (Join-Path $ccsBase "common\targetdb") -Target (Join-Path $localCcsBase "common\targetdb")
} elseif ($TargetDbMode -eq "C2000") {
    Copy-TargetDbC2000 -SourceRoot (Join-Path $ccsBase "common\targetdb") -TargetRoot (Join-Path $localCcsBase "common\targetdb")
}

$appData = Join-Path $destinationFull "ti-appdata"
New-Item -ItemType Directory -Force -Path $appData | Out-Null

@'
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-dslite-local.ps1" %*
'@ | Set-Content -LiteralPath (Join-Path $destinationFull "dslite-local.cmd") -Encoding ASCII

@'
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-dbgjtag-local.ps1" %*
'@ | Set-Content -LiteralPath (Join-Path $destinationFull "dbgjtag-local.cmd") -Encoding ASCII

@'
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ccsBase = Join-Path $root "ccs_base"
$env:TI_APPDATA_DIR = Join-Path $root "ti-appdata"
$env:PATH = @(
    (Join-Path $ccsBase "DebugServer\bin"),
    (Join-Path $ccsBase "common\bin"),
    (Join-Path $ccsBase "common\uscif"),
    (Join-Path $ccsBase "emulation\drivers"),
    (Join-Path $ccsBase "emulation\windows"),
    $env:PATH
) -join [IO.Path]::PathSeparator

Push-Location $ccsBase
try {
    & (Join-Path $ccsBase "DebugServer\bin\DSLite.exe") @Args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
'@ | Set-Content -LiteralPath (Join-Path $destinationFull "run-dslite-local.ps1") -Encoding ASCII

@'
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ccsBase = Join-Path $root "ccs_base"
$env:TI_APPDATA_DIR = Join-Path $root "ti-appdata"
$env:PATH = @(
    (Join-Path $ccsBase "DebugServer\bin"),
    (Join-Path $ccsBase "common\bin"),
    (Join-Path $ccsBase "common\uscif"),
    (Join-Path $ccsBase "emulation\drivers"),
    (Join-Path $ccsBase "emulation\windows"),
    $env:PATH
) -join [IO.Path]::PathSeparator

Push-Location $ccsBase
try {
    & (Join-Path $ccsBase "common\uscif\dbgjtag.exe") @Args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
'@ | Set-Content -LiteralPath (Join-Path $destinationFull "run-dbgjtag-local.ps1") -Encoding ASCII

$files = Get-ChildItem -LiteralPath $destinationFull -Recurse -File
$manifest = [ordered]@{
    extracted_at = (Get-Date).ToString("o")
    source_root = $ccsRootPath
    destination = $destinationFull
    targetdb_mode = $TargetDbMode
    file_count = @($files).Count
    total_bytes = ($files | Measure-Object Length -Sum).Sum
    dslite_entry = "dslite-local.cmd"
    dbgjtag_entry = "dbgjtag-local.cmd"
    appdata = "ti-appdata"
    note = "Local extraction of proprietary TI CCS DebugServer runtime. Do not commit vendor/ payloads."
}

$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $destinationFull "manifest.json") -Encoding ASCII

Write-Host "Extracted TI DebugServer runtime:"
Write-Host "  Source:      $ccsRootPath"
Write-Host "  Destination: $destinationFull"
Write-Host "  Target DB:   $TargetDbMode"
Write-Host "  Files:       $(@($files).Count)"
Write-Host "  Bytes:       $(($files | Measure-Object Length -Sum).Sum)"
Write-Host "  DSLite:      $(Join-Path $destinationFull 'dslite-local.cmd')"
Write-Host "  dbgjtag:     $(Join-Path $destinationFull 'dbgjtag-local.cmd')"
