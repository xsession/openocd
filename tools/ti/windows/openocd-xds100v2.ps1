# SPDX-License-Identifier: GPL-2.0-or-later
#Requires -Version 5.1
[CmdletBinding()]
param(
  [string]$OpenOcd = '',
  [Alias('s')]
  [string]$Scripts = '',
  [string]$Serial = '',
  [switch]$NoAutoInstall,
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$OpenOcdArgs
)

$ErrorActionPreference = 'Stop'

$script = Join-Path $PSScriptRoot 'openocd-xds100.ps1'
& $script -ProbeVersion v2 -OpenOcd $OpenOcd -Scripts $Scripts -Serial $Serial -NoAutoInstall:$NoAutoInstall @OpenOcdArgs
exit $LASTEXITCODE
