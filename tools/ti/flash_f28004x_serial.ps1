[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ComPort,

  [Parameter(Mandatory = $true)]
  [string]$AppFile,

  [int]$BaudRate = 9600,

  [string]$Device = 'f28004x',

  [string]$C2000WareRoot = 'C:\ti\C2000Ware_5_03_00_00',

  [string]$ProgrammerExe = 'C:\ti\C2000Ware_5_03_00_00\utilities\flash_programmers\serial_flash_programmer\serial_flash_programmer.exe',

  [string]$KernelFile = 'C:\ti\C2000Ware_5_03_00_00\utilities\flash_programmers\serial_flash_programmer\f28004x_fw_upgrade_example\flashapi_ex2_sci_kernel.txt'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $ProgrammerExe)) {
  throw "serial_flash_programmer.exe not found at: $ProgrammerExe"
}
if (-not (Test-Path -LiteralPath $KernelFile)) {
  throw "Kernel file not found at: $KernelFile"
}
if (-not (Test-Path -LiteralPath $AppFile)) {
  throw "App file not found at: $AppFile"
}

# TI tool expects COM<num> form.
if ($ComPort -notmatch '^COM\d+$') {
  throw "ComPort must look like COM7. Got: '$ComPort'"
}

Write-Host "Starting TI serial flash programmer..." -ForegroundColor Cyan
Write-Host "  Device  : $Device" -ForegroundColor Cyan
Write-Host "  Port    : $ComPort" -ForegroundColor Cyan
Write-Host "  Baud    : $BaudRate" -ForegroundColor Cyan
Write-Host "  Kernel  : $KernelFile" -ForegroundColor Cyan
Write-Host "  App     : $AppFile" -ForegroundColor Cyan
Write-Host "" 
Write-Host "NOTE: For F28004x devices, the tool may prompt for DFU/Erase/Verify interactively." -ForegroundColor Yellow

& $ProgrammerExe -d $Device -k $KernelFile -a $AppFile -b $BaudRate -p $ComPort
exit $LASTEXITCODE
