param(
    [Parameter(Mandatory = $true)][string]$CcsRoot,
    [string]$Bridge = "$PSScriptRoot\ccs-debug-bridge.js"
)

$runner = Join-Path $CcsRoot "ccs\scripting\run.bat"
if (-not (Test-Path $runner)) {
    throw "CCS scripting runner not found: $runner"
}
& $runner $Bridge
exit $LASTEXITCODE
