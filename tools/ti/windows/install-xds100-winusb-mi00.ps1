# SPDX-License-Identifier: GPL-2.0-or-later
#Requires -Version 5.1
[CmdletBinding()]
param(
  [ValidateSet('v2', 'v3')]
  [string]$ProbeVersion = 'v2',
  [string]$Installer = '',
  [string]$DriverDirectory = '',
  [switch]$Silent
)

$ErrorActionPreference = 'Stop'

$probe = @{
  v2 = @{
    Pid = '0xa6d0'
    Product = 'XDS100v2'
    Inf = 'xds100v2-mi00-winusb.inf'
    Directory = 'xds100v2-mi00'
  }
  v3 = @{
    Pid = '0xa6d1'
    Product = 'XDS100v3'
    Inf = 'xds100v3-mi00-winusb.inf'
    Directory = 'xds100v3-mi00'
  }
}[$ProbeVersion]

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  throw 'Run this script from an elevated (Administrator) PowerShell.'
}

if (-not $Installer) {
  $arch = if ([Environment]::Is64BitOperatingSystem) { 'x64' } else { 'x86' }
  $Installer = Join-Path $PSScriptRoot "bin\$arch\wdi-simple.exe"
}
if (-not (Test-Path -LiteralPath $Installer)) {
  throw "Missing libwdi installer: $Installer. Build the Windows Docker package first."
}

if (-not $DriverDirectory) {
  $DriverDirectory = Join-Path $PSScriptRoot "driver\$($probe.Directory)"
}

$Installer = (Resolve-Path -LiteralPath $Installer).Path
$DriverDirectory = [System.IO.Path]::GetFullPath($DriverDirectory)
New-Item -ItemType Directory -Force -Path $DriverDirectory | Out-Null

$arguments = @(
  '--vid', '0x0403',
  '--pid', $probe.Pid,
  '--iid', '0x00',
  '--type', '0',
  '--manufacturer', 'Texas Instruments',
  '--name', "$($probe.Product) Debug Port (WinUSB)",
  '--dest', $DriverDirectory,
  '--inf', $probe.Inf,
  '--timeout', '120000',
  '--log', '0'
)
if ($Silent) {
  $arguments += '--silent'
}

Write-Host "Installing WinUSB for $($probe.Product) debug interface MI_00 ..."
Write-Host "Driver staging directory: $DriverDirectory"
& $Installer @arguments
if ($LASTEXITCODE -ne 0) {
  throw "WinUSB installation failed for $($probe.Product) MI_00 (exit code $LASTEXITCODE)."
}

Write-Host ''
Write-Host 'WinUSB package installed. Unplug and reconnect the probe USB cable.' -ForegroundColor Green
Write-Host 'Only interface MI_00 was targeted. Do not bind the auxiliary UART interface MI_01 to WinUSB.'
Write-Host ''
Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
  Where-Object InstanceId -Match "^USB\\VID_0403&PID_$($probe.Pid.Substring(2).ToUpperInvariant())" |
  Select-Object Status, Class, FriendlyName, InstanceId |
  Format-Table -AutoSize
