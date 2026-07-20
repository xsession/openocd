param([Parameter(Mandatory = $true)][string]$OpenOcdRoot)
$root = Split-Path -Parent $PSScriptRoot
$installer = Join-Path $root 'openocd/scripts/apply_xds100_support.py'
python $installer $OpenOcdRoot
exit $LASTEXITCODE
