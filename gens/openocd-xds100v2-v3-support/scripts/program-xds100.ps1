param(
    [Parameter(Mandatory = $true)][string]$OpenOcd,
    [Parameter(Mandatory = $true)][ValidateSet('v2', 'v3', 'auto')][string]$Version,
    [Parameter(Mandatory = $true)][string]$TargetConfig,
    [Parameter(Mandatory = $true)][string]$Image,
    [int]$SpeedKHz = 1000
)

$interface = switch ($Version) {
    'v2' { 'interface/ftdi/xds100v2.cfg' }
    'v3' { 'interface/ftdi/xds100v3.cfg' }
    default { 'interface/ftdi/xds100.cfg' }
}

& $OpenOcd `
    -f $interface `
    -f $TargetConfig `
    -c "adapter speed $SpeedKHz" `
    -c "program {$Image} verify reset exit"
exit $LASTEXITCODE
