param([Parameter(Mandatory = $true)][string]$OpenOcdRoot)
$script = Join-Path $PSScriptRoot 'apply_xds100_support.py'
python $script $OpenOcdRoot
exit $LASTEXITCODE
