[CmdletBinding()]
param(
  [string]$OpenOcd = "",
  [string]$TclRoot = "",
  [int]$AdapterSpeedKhz = 1000,
  [string]$Serial = "",
  [switch]$UseInstalledInterfaceConfig,
  [string]$LogFile = ""
)

$ErrorActionPreference = 'Stop'

function Resolve-RepoRoot {
  $here = Split-Path -Parent $PSCommandPath
  return (Resolve-Path (Join-Path $here '..\..')).Path
}

function Resolve-OpenOcd {
  param([string]$RepoRoot, [string]$Requested)
  if ($Requested) {
    return (Resolve-Path $Requested).Path
  }

  $candidate = Join-Path $RepoRoot 'dist\windows\openocd-windows-x86_64\bin\openocd.exe'
  if (Test-Path -LiteralPath $candidate) {
    return (Resolve-Path $candidate).Path
  }

  $cmd = Get-Command openocd.exe -ErrorAction SilentlyContinue
  if ($cmd) {
    return $cmd.Source
  }

  throw 'OpenOCD executable not found. Pass -OpenOcd or build/package OpenOCD first.'
}

function Get-Xds100DeviceSummary {
  try {
    $devices = Get-PnpDevice -PresentOnly |
      Where-Object { $_.InstanceId -match 'VID_0403.*PID_A6D0|XDS100|FTDI' } |
      Select-Object Status, Class, FriendlyName, InstanceId
    return $devices
  } catch {
    Write-Warning "Could not enumerate Windows PnP devices: $($_.Exception.Message)"
    return @()
  }
}

function Write-Xds100DeviceSummary {
  param($Devices)
  if (-not $Devices -or $Devices.Count -eq 0) {
    Write-Host 'No XDS100v2/FTDI USB devices were visible through Windows PnP.' -ForegroundColor Yellow
    return
  }

  Write-Host 'Detected Windows USB/PnP entries:' -ForegroundColor Cyan
  $Devices | Format-Table -AutoSize | Out-String | Write-Host

  $debugPort = $Devices | Where-Object {
    $_.InstanceId -match 'VID_0403.*PID_A6D0.*MI_00' -or
    $_.FriendlyName -match 'Debug Port'
  } | Select-Object -First 1

  if ($debugPort -and $debugPort.Class -notin @('libusbK', 'libusb-win32', 'USBDevice')) {
    Write-Host "OpenOCD/libftdi may not be able to open interface 0 while it is bound to class '$($debugPort.Class)'." -ForegroundColor Yellow
    Write-Host 'Use a WinUSB/libusb-compatible driver for only the XDS100 JTAG/debug interface when running OpenOCD.' -ForegroundColor Yellow
  }
}

function Build-OpenOcdArguments {
  param(
    [string]$RepoRoot,
    [string]$TclRoot,
    [int]$AdapterSpeedKhz,
    [string]$Serial,
    [bool]$UseInstalledInterfaceConfig
  )

  $args = @('-s', $TclRoot)

  if ($UseInstalledInterfaceConfig) {
    $args += @('-f', 'interface/ti/xds100v2.cfg')
  } else {
    $args += @(
      '-c', 'adapter driver ftdi',
      '-c', 'adapter usb vid_pid 0x0403 0xa6d0 0x0403 0x6010',
      '-c', 'ftdi channel 0',
      '-c', 'transport select jtag',
      '-c', 'ftdi layout_init 0x0038 0x597b',
      '-c', 'ftdi layout_signal nTRST -data 0x0010',
      '-c', 'ftdi layout_signal nSRST -oe 0x0100',
      '-c', 'ftdi layout_signal EMU_EN -data 0x0020',
      '-c', 'ftdi layout_signal EMU0 -oe 0x0040',
      '-c', 'ftdi layout_signal EMU1 -oe 0x1000',
      '-c', 'ftdi layout_signal PWR_RST -data 0x0800',
      '-c', 'ftdi layout_signal LOOPBACK -data 0x4000'
    )
  }

  if ($Serial) {
    $args += @('-c', "adapter serial $Serial")
  }

  $args += @(
    '-c', "adapter speed $AdapterSpeedKhz",
    '-c', 'set CHIPNAME xds100_detect',
    '-f', 'target/ti/c2000-icepick-scan.cfg',
    '-c', 'init',
    '-c', 'scan_chain',
    '-c', 'c2000_icepick_read_idcode',
    '-c', 'c2000_icepick_read_code',
    '-c', 'c2000_icepick_scan_sdtaps',
    '-c', 'shutdown'
  )

  return $args
}

$repoRoot = Resolve-RepoRoot
if (-not $TclRoot) {
  $TclRoot = Join-Path $repoRoot 'tcl'
}
$TclRoot = (Resolve-Path $TclRoot).Path
$OpenOcd = Resolve-OpenOcd -RepoRoot $repoRoot -Requested $OpenOcd

$devices = Get-Xds100DeviceSummary
Write-Xds100DeviceSummary -Devices $devices

$openOcdArgs = Build-OpenOcdArguments `
  -RepoRoot $repoRoot `
  -TclRoot $TclRoot `
  -AdapterSpeedKhz $AdapterSpeedKhz `
  -Serial $Serial `
  -UseInstalledInterfaceConfig ([bool]$UseInstalledInterfaceConfig)

Write-Host "Running OpenOCD scan: $OpenOcd $($openOcdArgs -join ' ')" -ForegroundColor Cyan

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
  $output = & $OpenOcd @openOcdArgs 2>&1
  $exitCode = $LASTEXITCODE
} finally {
  $ErrorActionPreference = $previousErrorActionPreference
}

if ($LogFile) {
  $logDirectory = Split-Path -Parent $LogFile
  if ($logDirectory) {
    New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
  }
  $output | Tee-Object -FilePath $LogFile
} else {
  $output
}

exit $exitCode
