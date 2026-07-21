# SPDX-License-Identifier: GPL-2.0-or-later
#Requires -Version 5.1
[CmdletBinding()]
param(
  [string]$Installer = '',
  [string]$DriverDirectory = '',
  [switch]$Silent
)

$ErrorActionPreference = 'Stop'

$script = Join-Path $PSScriptRoot 'install-xds100-winusb-mi00.ps1'
& $script -ProbeVersion v3 -Installer $Installer -DriverDirectory $DriverDirectory -Silent:$Silent
exit $LASTEXITCODE
