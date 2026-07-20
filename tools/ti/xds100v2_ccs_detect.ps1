[CmdletBinding()]
param(
  [string]$CcsBase = 'C:\ti\ccs2100\ccs\ccs_base',

  [string[]]$Candidates = @(
    'f280049',
    'f280049c',
    'f28069',
    'f28035',
    'f28m35h52c1'
  ),

  [string]$OutDir = 'artifacts\xds100v2-ccs-detect',

  [string]$Serial = '',

  [string]$ReadRange = '0x0,2',

  [int]$ReadSize = 16,

  [int]$TimeoutSeconds = 10
)

$ErrorActionPreference = 'Stop'

$ccsBaseResolved = Resolve-Path -LiteralPath $CcsBase -ErrorAction Stop
$targetDb = Join-Path $ccsBaseResolved 'common\targetdb'
$dsLite = Join-Path $ccsBaseResolved 'DebugServer\bin\DSLite.exe'
$connection = Join-Path $targetDb 'connections\TIXDS100v2_Connection.xml'

if (-not (Test-Path -LiteralPath $dsLite)) {
  throw "DSLite.exe not found at: $dsLite"
}
if (-not (Test-Path -LiteralPath $connection)) {
  throw "XDS100v2 CCS connection XML not found at: $connection"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Escape-XmlAttribute {
  param([string]$Value)

  return [System.Security.SecurityElement]::Escape($Value)
}

function Get-AttributeOrDefault {
  param(
    [System.Xml.XmlElement]$Node,
    [string]$Name,
    [string]$Default
  )

  if ($Node.HasAttribute($Name)) {
    return $Node.GetAttribute($Name)
  }

  return $Default
}

function Get-MinimalDeviceBody {
  param(
    [System.Xml.XmlElement]$DeviceNode,
    [string]$DeviceInstanceId,
    [string]$PartNumber
  )

  $part = Escape-XmlAttribute $PartNumber
  $deviceId = Escape-XmlAttribute $DeviceInstanceId
  $router = $DeviceNode.SelectSingleNode('./router')
  if ($router) {
    $routerId = Escape-XmlAttribute (Get-AttributeOrDefault $router 'id' 'IcePick_C_0')
    $routerIsa = Escape-XmlAttribute (Get-AttributeOrDefault $router 'isa' 'ICEPICK_C')
    $routerDesc = Escape-XmlAttribute (Get-AttributeOrDefault $router 'description' 'ICEPick_C Router')

    $subpaths = foreach ($subpath in @($router.SelectNodes('./subpath'))) {
      $subpathId = Escape-XmlAttribute (Get-AttributeOrDefault $subpath 'id' 'Subpath_0')
      $port = $subpath.SelectSingleNode('./property[@id="Port Number"]')
      $portValue = '0x10'
      if ($port -and $port.HasAttribute('Value')) {
        $portValue = $port.GetAttribute('Value')
      }

      $cpu = $subpath.SelectSingleNode('./cpu')
      $cpuId = 'C28xx_CPU1'
      $cpuIsa = 'TMS320C28XX'
      $cpuDescription = 'C28xx CPU'
      if ($cpu) {
        $cpuId = Get-AttributeOrDefault $cpu 'id' $cpuId
        $cpuIsa = Get-AttributeOrDefault $cpu 'isa' $cpuIsa
        $cpuDescription = Get-AttributeOrDefault $cpu 'description' $cpuDescription
      }

      $cpuXml = if ($cpuIsa -match 'CORTEX|Cortex|M3') { 'cortex_m3.xml' } elseif ($cpuIsa -match 'cs_child') { 'cs_child.xml' } else { 'c28xx.xml' }
      $cpuPath = 'cpus'
      @"
                    <subpath id="$subpathId">
                        <instance XML_version="1.2" desc="$(Escape-XmlAttribute $cpuId)" href="$cpuPath/$cpuXml" id="$(Escape-XmlAttribute $cpuId)" xml="$cpuXml" xmlpath="$cpuPath"/>
                        <property Type="numericfield" Value="$(Escape-XmlAttribute $portValue)" id="Port Number"/>
                        <cpu HW_revision="1.0" XML_version="1.2" description="$(Escape-XmlAttribute $cpuDescription)" id="$(Escape-XmlAttribute $cpuId)" isa="$(Escape-XmlAttribute $cpuIsa)"/>
                    </subpath>
"@
    }

    return @"
                <device HW_revision="1" XML_version="1.2" description="" id="$deviceId" partnum="$part">
                    <router HW_revision="1.0" XML_version="1.2" description="$routerDesc" id="$routerId" isa="$routerIsa">
$($subpaths -join "`n")
                    </router>
                </device>
"@
  }

  $cpuNodes = @($DeviceNode.SelectNodes('./cpu'))
  if (-not $cpuNodes) {
    $cpuNodes = @($DeviceNode.SelectNodes('.//cpu'))
  }

  $cpus = foreach ($cpu in $cpuNodes) {
    $cpuId = Escape-XmlAttribute (Get-AttributeOrDefault $cpu 'id' 'C28xx_0')
    $cpuIsa = Escape-XmlAttribute (Get-AttributeOrDefault $cpu 'isa' 'TMS320C28XX')
    $cpuDescription = Escape-XmlAttribute (Get-AttributeOrDefault $cpu 'description' 'CPU')
    $bypass = ''
    if ($cpuIsa -match 'TMS192') {
      $bypass = '<property Type="choicelist" Value="1" id="bypass"/>'
    }

    "                    <cpu HW_revision=`"1.0`" XML_version=`"1.2`" description=`"$cpuDescription`" deviceSim=`"false`" id=`"$cpuId`" isa=`"$cpuIsa`">$bypass</cpu>"
  }

  return @"
                <device HW_revision="1" XML_version="1.2" description="" id="$deviceId" partnum="$part">
$($cpus -join "`n")
                </device>
"@
}

function New-Xds100v2Ccxml {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Device,

    [Parameter(Mandatory = $true)]
    [string]$Path,

    [string]$ProbeSerial = ''
  )

  $devicePath = Join-Path $targetDb "devices\$Device.xml"
  if (-not (Test-Path -LiteralPath $devicePath)) {
    throw "CCS device XML not found for '$Device': $devicePath"
  }

  $deviceXml = [xml](Get-Content -LiteralPath $devicePath -Raw)
  $deviceNode = $deviceXml.DocumentElement
  $partNumber = $deviceNode.partnum
  if (-not $partNumber) {
    $partNumber = $Device
  }
  $deviceInstanceId = "$($partNumber)_0"
  $deviceBody = Get-MinimalDeviceBody -DeviceNode $deviceNode -DeviceInstanceId $deviceInstanceId -PartNumber $partNumber

  $serialChoice = ''
  if ($ProbeSerial) {
    $serialChoice = @"
            <property Type="choicelist" Value="0" id="Emulator Selection">
                <choice Name="Select by serial number" value="0">
                    <property Type="stringfield" Value="$ProbeSerial" id="-- Enter the serial number"/>
                </choice>
            </property>
"@
  }

  $content = @"
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<configurations XML_version="1.2" id="configurations_0">
    <configuration XML_version="1.2" id="Texas Instruments XDS100v2 USB Emulator_0">
        <instance XML_version="1.2" desc="Texas Instruments XDS100v2 USB Emulator_0" href="connections\TIXDS100v2_Connection.xml" id="Texas Instruments XDS100v2 USB Emulator_0" xml="TIXDS100v2_Connection.xml" xmlpath="connections"/>
        <connection XML_version="1.2" id="Texas Instruments XDS100v2 USB Emulator_0">
            <instance XML_version="1.2" href="drivers\tixds100v2icepick_c.xml" id="drivers" xml="tixds100v2icepick_c.xml" xmlpath="drivers"/>
            <instance XML_version="1.2" href="drivers\tixds100v2cs_dap.xml" id="drivers" xml="tixds100v2cs_dap.xml" xmlpath="drivers"/>
            <instance XML_version="1.2" href="drivers\tixds100v2cortexM.xml" id="drivers" xml="tixds100v2cortexM.xml" xmlpath="drivers"/>
            <instance XML_version="1.2" href="drivers\tixds100v2cs_child.xml" id="drivers" xml="tixds100v2cs_child.xml" xmlpath="drivers"/>
            <instance XML_version="1.2" href="drivers\tixds100v2c28x.xml" id="drivers" xml="tixds100v2c28x.xml" xmlpath="drivers"/>
            <instance XML_version="1.2" href="drivers\tixds100v2cla.xml" id="drivers" xml="tixds100v2cla.xml" xmlpath="drivers"/>
$serialChoice            <platform XML_version="1.2" id="platform_0">
                <instance XML_version="1.2" desc="$deviceInstanceId" href="devices\$Device.xml" id="$deviceInstanceId" xml="$Device.xml" xmlpath="devices"/>
$deviceBody
            </platform>
        </connection>
    </configuration>
</configurations>
"@

  Set-Content -LiteralPath $Path -Value $content -Encoding UTF8
}

$results = foreach ($candidate in $Candidates) {
  $safeName = $candidate -replace '[^A-Za-z0-9_.-]', '_'
  $ccxml = Join-Path $OutDir "$safeName.ccxml"
  $log = Join-Path $OutDir "$safeName.log"
  $memoryDump = Join-Path $OutDir "$safeName.bin"

  Write-Host "Testing $candidate through TI DSLite memory read..." -ForegroundColor Cyan
  New-Xds100v2Ccxml -Device $candidate -Path $ccxml -ProbeSerial $Serial

  $env:TI_APPDATA_DIR = (Resolve-Path -LiteralPath $OutDir).Path
  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    $output = & $dsLite memory --config $ccxml --range $ReadRange --size $ReadSize --output $memoryDump --timeout $TimeoutSeconds --log $log --verbose 2>&1
    $exitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }

  $output | Set-Content -LiteralPath $log -Encoding UTF8

  $passed = ($exitCode -eq 0) -and -not (($output -join "`n") -match '(?i)\b(error|failed|cannot|unable)\b')
  [pscustomobject]@{
    Candidate = $candidate
    Passed = $passed
    ExitCode = $exitCode
    Ccxml = $ccxml
    Log = $log
    MemoryDump = $memoryDump
  }
}

$results | Format-Table -AutoSize

$match = $results | Where-Object { $_.Passed } | Select-Object -First 1
if ($match) {
  Write-Host ""
  Write-Host "Likely reachable target configuration: $($match.Candidate)" -ForegroundColor Green
  exit 0
}

Write-Host ""
Write-Host "No candidate passed the XDS100v2 DSLite target-read checks." -ForegroundColor Yellow
Write-Host "Inspect the per-candidate logs in: $OutDir" -ForegroundColor Yellow
exit 1
