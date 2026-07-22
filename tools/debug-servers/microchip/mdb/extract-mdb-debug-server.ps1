# SPDX-License-Identifier: GPL-2.0-or-later
#Requires -Version 5.1
[CmdletBinding()]
param(
  [string]$MplabXRoot = 'C:\Program Files\Microchip\MPLABX\v6.25',
  [string]$Destination = '',
  [switch]$IncludeUserModules,
  [switch]$IncludePacks,
  [string[]]$PackName = @(),
  [switch]$Force
)

$ErrorActionPreference = 'Stop'

function Resolve-FullPath {
  param([string]$Path)
  return [System.IO.Path]::GetFullPath($Path)
}

function Copy-Tree {
  param(
    [string]$Source,
    [string]$Destination
  )

  if (-not (Test-Path -LiteralPath $Source)) {
    Write-Warning "Skipping missing dependency: $Source"
    return
  }

  New-Item -ItemType Directory -Force -Path $Destination | Out-Null
  Copy-Item -Path (Join-Path $Source '*') -Destination $Destination -Recurse -Force
}

function Copy-File {
  param(
    [string]$Source,
    [string]$Destination
  )

  if (-not (Test-Path -LiteralPath $Source)) {
    Write-Warning "Skipping missing dependency: $Source"
    return
  }

  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
  Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

$scriptRoot = Resolve-FullPath $PSScriptRoot
$repoRoot = Resolve-FullPath (Join-Path $scriptRoot '..\..\..')

if (-not $Destination) {
  $Destination = Join-Path $scriptRoot 'vendor\mplabx-mdb-v6.25'
}
$destinationRoot = Resolve-FullPath $Destination

if ((Test-Path -LiteralPath $destinationRoot) -and -not $Force) {
  throw "Destination already exists: $destinationRoot. Pass -Force to overwrite/update it."
}

$mplabRoot = Resolve-FullPath $MplabXRoot
$platform = Join-Path $mplabRoot 'mplab_platform'
$mdbBat = Join-Path $platform 'bin\mdb.bat'
$conf = Join-Path $platform 'etc\mplab_ide.conf'

if (-not (Test-Path -LiteralPath $mdbBat)) {
  throw "Missing MDB batch file: $mdbBat"
}
if (-not (Test-Path -LiteralPath $conf)) {
  throw "Missing MPLAB X config file: $conf"
}

New-Item -ItemType Directory -Force -Path $destinationRoot | Out-Null

Copy-File $mdbBat (Join-Path $destinationRoot 'mplab_platform\bin\mdb.bat')
Copy-File $conf (Join-Path $destinationRoot 'mplab_platform\etc\mplab_ide.conf')
Copy-File (Join-Path $platform 'lib\mdb.jar') (Join-Path $destinationRoot 'mplab_platform\lib\mdb.jar')
Copy-Tree (Join-Path $platform 'mdbcore') (Join-Path $destinationRoot 'mplab_platform\mdbcore')
Copy-Tree (Join-Path $platform 'platform\core') (Join-Path $destinationRoot 'mplab_platform\platform\core')
Copy-Tree (Join-Path $platform 'platform\modules') (Join-Path $destinationRoot 'mplab_platform\platform\modules')
Copy-Tree (Join-Path $platform 'platform\lib') (Join-Path $destinationRoot 'mplab_platform\platform\lib')
Copy-Tree (Join-Path $platform 'ide\modules') (Join-Path $destinationRoot 'mplab_platform\ide\modules')
Copy-Tree (Join-Path $platform 'ide\modules\ext') (Join-Path $destinationRoot 'mplab_platform\ide\modules\ext')
Copy-Tree (Join-Path $platform 'mplablibs\modules') (Join-Path $destinationRoot 'mplab_platform\mplablibs\modules')
Copy-Tree (Join-Path $platform 'data-visualizer\modules\ext') (Join-Path $destinationRoot 'mplab_platform\data-visualizer\modules\ext')
Copy-Tree (Join-Path $platform 'thirdparty') (Join-Path $destinationRoot 'mplab_platform\thirdparty')
Copy-Tree (Join-Path $platform 'java') (Join-Path $destinationRoot 'mplab_platform\java')

if ($IncludePacks) {
  $packSource = Join-Path $mplabRoot 'packs'
  $packDestination = Join-Path $destinationRoot 'packs'
  if ($PackName.Count -gt 0) {
    foreach ($name in $PackName) {
      $matches = Get-ChildItem -LiteralPath $packSource -Directory -Recurse |
        Where-Object { $_.Name -eq $name -or $_.Name -like $name }
      if (-not $matches) {
        Write-Warning "No pack matched: $name"
      }
      foreach ($match in $matches) {
        $relative = $match.FullName.Substring($packSource.Length).TrimStart('\', '/')
        Copy-Tree $match.FullName (Join-Path $packDestination $relative)
      }
    }
  } else {
    Copy-Tree $packSource $packDestination
  }
}

if ($IncludeUserModules) {
  $userModules = Join-Path $env:APPDATA 'mplab_ipe\dev\v6.25\modules'
  if (Test-Path -LiteralPath $userModules) {
    Copy-Tree $userModules (Join-Path $destinationRoot 'user\modules')
  } else {
    Write-Warning "Requested user modules, but none were found: $userModules"
  }
}

$localCmd = Join-Path $destinationRoot 'mdb-local.cmd'
$localCmdText = @'
@echo off
set "HERE=%~dp0"
set "USER_DIR=%HERE%user"
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%run-mdb-local.ps1" %*
'@
Set-Content -LiteralPath $localCmd -Value $localCmdText -Encoding ASCII

$runner = Join-Path $destinationRoot 'run-mdb-local.ps1'
$runnerText = @'
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$platform = Join-Path $root 'mplab_platform'
$conf = Join-Path $platform 'etc\mplab_ide.conf'
$jdkhomeLine = Get-Content -LiteralPath $conf | Where-Object { $_ -match '^jdkhome=' } | Select-Object -First 1
if (-not $jdkhomeLine) {
  throw "Missing jdkhome in $conf"
}
$jdkhome = ($jdkhomeLine -replace '^jdkhome=', '').Trim('"')
if (-not [System.IO.Path]::IsPathRooted($jdkhome)) {
  $jdkhome = Join-Path $platform $jdkhome
}
$java = Join-Path $jdkhome 'bin\java.exe'
if (-not (Test-Path -LiteralPath $java)) {
  $java = Join-Path $platform 'java\bin\java.exe'
}
if (-not (Test-Path -LiteralPath $java)) {
  throw "Missing Java runtime for MDB: $java"
}
$env:MPLABX_THIRDPARTY_LIB_PATH = Join-Path $platform 'thirdparty'
$userDir = if ($env:USER_DIR) { $env:USER_DIR } else { Join-Path $root 'user' }
$mdbJar = Join-Path $platform 'lib\mdb.jar'
$classpathItems = @(
  (Join-Path $userDir 'modules\*'),
  (Join-Path $userDir 'modules\ext\*'),
  (Join-Path $platform 'mdbcore\modules\*'),
  (Join-Path $platform 'platform\core\*'),
  (Join-Path $platform 'platform\lib\*'),
  (Join-Path $platform 'mplablibs\modules\*'),
  (Join-Path $platform 'mplablibs\modules\ext\*'),
  (Join-Path $platform 'data-visualizer\modules\ext\*'),
  $mdbJar
)
$openideModules = Join-Path $platform 'platform\modules'
if (Test-Path -LiteralPath $openideModules) {
  $classpathItems += Get-ChildItem -LiteralPath $openideModules -File |
    Where-Object { $_.Name -like 'org-openide-*.jar' } |
    ForEach-Object { $_.FullName }
}
$classpath = $classpathItems -join ';'
$javaArgs = @(
  '-Dfile.encoding=UTF-8',
  '-classpath',
  $classpath,
  'com.microchip.mplab.mdb.debugcommands.Main'
)
Push-Location $platform
try {
  & $java @javaArgs @args
  exit $LASTEXITCODE
} finally {
  Pop-Location
}
'@
Set-Content -LiteralPath $runner -Value $runnerText -Encoding ASCII

$files = Get-ChildItem -LiteralPath $destinationRoot -Recurse -File
$manifest = [ordered]@{
  extracted_at = (Get-Date).ToString('o')
  source_root = $mplabRoot
  destination = $destinationRoot
  include_user_modules = [bool]$IncludeUserModules
  include_packs = [bool]$IncludePacks
  pack_name = @($PackName)
  file_count = $files.Count
  total_bytes = ($files | Measure-Object -Property Length -Sum).Sum
  entry = 'mdb-local.cmd'
  note = 'Local extraction of proprietary Microchip MPLAB X MDB runtime. Do not commit vendor/ payloads.'
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $destinationRoot 'manifest.json') -Encoding ASCII

Write-Host "Extracted MDB debug server runtime:"
Write-Host "  $destinationRoot"
Write-Host "Files: $($manifest.file_count)"
Write-Host "Bytes: $($manifest.total_bytes)"
Write-Host "Entry:"
Write-Host "  $localCmd"
