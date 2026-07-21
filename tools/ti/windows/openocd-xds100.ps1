# SPDX-License-Identifier: GPL-2.0-or-later
#Requires -Version 5.1
[CmdletBinding()]
param(
  [ValidateSet('v2', 'v3')]
  [string]$ProbeVersion = 'v2',
  [string]$OpenOcd = '',
  [Alias('s')]
  [string]$Scripts = '',
  [string]$Serial = '',
  [switch]$NoAutoInstall,
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$OpenOcdArgs
)

$ErrorActionPreference = 'Stop'

function Resolve-OptionalPath {
  param([string]$Path)

  if (-not $Path) {
    return ''
  }
  return (Resolve-Path -LiteralPath $Path).Path
}

function Test-Administrator {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = [Security.Principal.WindowsPrincipal]::new($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function ConvertTo-WindowsCommandLineArgument {
  param([string]$Value)

  if ($Value -notmatch '[\s"]') {
    return $Value
  }

  $builder = '"'
  $backslashes = 0
  foreach ($char in $Value.ToCharArray()) {
    if ($char -eq '\') {
      $backslashes++
    } elseif ($char -eq '"') {
      $builder += ('\' * (($backslashes * 2) + 1))
      $builder += '"'
      $backslashes = 0
    } else {
      if ($backslashes) {
        $builder += ('\' * $backslashes)
        $backslashes = 0
      }
      $builder += $char
    }
  }
  if ($backslashes) {
    $builder += ('\' * ($backslashes * 2))
  }
  $builder += '"'
  return $builder
}

function Find-PackageRoot {
  $current = (Resolve-Path -LiteralPath $PSScriptRoot).Path
  while ($current) {
    if (Test-Path -LiteralPath (Join-Path $current 'bin\openocd.exe')) {
      return $current
    }
    $parent = Split-Path -Parent $current
    if (-not $parent -or $parent -eq $current) {
      break
    }
    $current = $parent
  }
  return ''
}

function Invoke-OpenOcdCapture {
  param(
    [string]$Exe,
    [string[]]$Arguments
  )

  $psi = [Diagnostics.ProcessStartInfo]::new()
  $psi.FileName = $Exe
  $psi.Arguments = (($Arguments | ForEach-Object { ConvertTo-WindowsCommandLineArgument $_ }) -join ' ')
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true

  $process = [Diagnostics.Process]::Start($psi)
  $stdout = $process.StandardOutput.ReadToEnd()
  $stderr = $process.StandardError.ReadToEnd()
  $process.WaitForExit()

  [pscustomobject]@{
    ExitCode = $process.ExitCode
    Text = ($stdout + $stderr)
  }
}

$probe = @{
  v2 = @{
    Product = 'XDS100v2'
    DefaultArgs = @('-f', 'board/ti/launchxl-f28069m-xds100v2.cfg')
  }
  v3 = @{
    Product = 'XDS100v3'
    DefaultArgs = @('-f', 'interface/ti/xds100v3.cfg', '-c', 'adapter speed 1000', '-c', 'init; shutdown')
  }
}[$ProbeVersion]

$packageRoot = Find-PackageRoot

if (-not $OpenOcd) {
  if (-not $packageRoot) {
    throw 'Could not find bin\openocd.exe above the wrapper. Pass -OpenOcd explicitly.'
  }
  $OpenOcd = Join-Path $packageRoot 'bin\openocd.exe'
}
$OpenOcd = Resolve-OptionalPath $OpenOcd
if (-not (Test-Path -LiteralPath $OpenOcd)) {
  throw "Missing OpenOCD executable: $OpenOcd"
}

if (-not $Scripts) {
  if (-not $packageRoot) {
    throw 'Could not find share\openocd\scripts above the wrapper. Pass -Scripts explicitly.'
  }
  $Scripts = Join-Path $packageRoot 'share\openocd\scripts'
}
$Scripts = Resolve-OptionalPath $Scripts

$args = @()
if ($Scripts) {
  $args += @('-s', $Scripts)
}

if ($OpenOcdArgs -and $OpenOcdArgs.Count -gt 0) {
  $args += $OpenOcdArgs
} else {
  $args += $probe.DefaultArgs
}

if ($Serial) {
  $args += @('-c', "adapter serial $Serial")
}

$first = Invoke-OpenOcdCapture -Exe $OpenOcd -Arguments $args
Write-Host $first.Text

if ($first.ExitCode -eq 0) {
  exit 0
}

$needsWinUsb = $first.Text -match 'LIBUSB_ERROR_NOT_FOUND|unable to open ftdi device'
if (-not $needsWinUsb -or $NoAutoInstall) {
  exit $first.ExitCode
}

$installer = Join-Path $PSScriptRoot 'install-xds100-winusb-mi00.ps1'
if (-not (Test-Path -LiteralPath $installer)) {
  Write-Warning "OpenOCD could not open the $($probe.Product) debug interface, but the WinUSB installer is missing: $installer"
  exit $first.ExitCode
}

Write-Host ''
Write-Warning "OpenOCD cannot open the $($probe.Product) debug interface. The MI_00 debug port likely needs WinUSB."

if (Test-Administrator) {
  & $installer -ProbeVersion $ProbeVersion -Silent
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
} else {
  Write-Host 'Starting the packaged libwdi installer as Administrator ...'
  $installArgs = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', "`"$installer`"",
    '-ProbeVersion', $ProbeVersion,
    '-Silent'
  )
  $process = Start-Process powershell -Verb RunAs -ArgumentList $installArgs -Wait -PassThru
  if ($process.ExitCode -ne 0) {
    Write-Warning "Driver installer failed or was canceled (exit code $($process.ExitCode))."
    exit $first.ExitCode
  }
}

Write-Host ''
Write-Host 'Unplug and reconnect the probe USB cable, then press Enter to retry OpenOCD.'
[void][Console]::ReadLine()

$second = Invoke-OpenOcdCapture -Exe $OpenOcd -Arguments $args
Write-Host $second.Text
exit $second.ExitCode
