$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    python -m unittest discover -s tests -v
    Push-Location (Join-Path $root 'extension')
    try { npm test } finally { Pop-Location }
    python -m unittest discover -s (Join-Path $root 'openocd/tests') -p 'test_*.py' -v
    tclsh (Join-Path $root 'openocd/tests/test_xds100_configs.tcl')
    python (Join-Path $root 'openocd/scripts/validate_bundle.py') (Join-Path $root 'openocd')
} finally {
    Pop-Location
}
