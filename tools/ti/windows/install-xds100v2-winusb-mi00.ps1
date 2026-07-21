# SPDX-License-Identifier: GPL-2.0-or-later
#Requires -Version 5.1
[CmdletBinding()]
param(
  [string]$Installer = '',
  [string]$DriverDirectory = '',
  [switch]$Silent
)

$ErrorActionPreference = 'Stop'

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
  $DriverDirectory = Join-Path $PSScriptRoot 'driver\xds100v2-mi00'
}

$Installer = (Resolve-Path -LiteralPath $Installer).Path
$DriverDirectory = [System.IO.Path]::GetFullPath($DriverDirectory)
New-Item -ItemType Directory -Force -Path $DriverDirectory | Out-Null

$arguments = @(
  '--vid', '0x0403',
  '--pid', '0xa6d0',
  '--iid', '0x00',
  '--type', '0',
  '--manufacturer', 'Texas Instruments',
  '--name', 'XDS100v2 Debug Port (WinUSB)',
  '--dest', $DriverDirectory,
  '--inf', 'xds100v2-mi00-winusb.inf',
  '--timeout', '120000',
  '--log', '0'
)
if ($Silent) {
  $arguments += '--silent'
}

Write-Host 'Installing WinUSB for XDS100v2 debug interface MI_00 ...'
Write-Host "Driver staging directory: $DriverDirectory"
& $Installer @arguments
if ($LASTEXITCODE -ne 0) {
  throw "WinUSB installation failed for XDS100v2 MI_00 (exit code $LASTEXITCODE)."
}

Write-Host ''
Write-Host 'WinUSB package installed. Unplug and reconnect the LaunchPad USB cable.' -ForegroundColor Green
Write-Host 'The XDS100 Class Auxiliary Port / COM port is interface MI_01 and is not changed by this script.'
Write-Host ''
Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
  Where-Object InstanceId -Match '^USB\\VID_0403&PID_A6D0' |
  Select-Object Status, Class, FriendlyName, InstanceId |
  Format-Table -AutoSize
