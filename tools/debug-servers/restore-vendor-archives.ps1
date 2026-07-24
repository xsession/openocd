param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$archives = @(
    @{
        Path = 'microchip/mdb/vendor/mplabx-mdb-v6.25.7z'
        Sha256 = 'A47F1753630F86243FD010F644F5F1CAD79B309EC4673D009B7CCB5EABF385B9'
    },
    @{
        Path = 'ti/c2000/vendor/ccs-debugserver-20.4.0.7z'
        Sha256 = 'A673074ACC7224638521D4A462A80C7737C2A3D2C00E9749CA75A1636F415C39'
    }
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

foreach ($archive in $archives) {
    $archivePath = Join-Path $root $archive.Path
    $parts = Get-ChildItem -LiteralPath (Split-Path -Parent $archivePath) -Filter ((Split-Path -Leaf $archivePath) + '.part*') |
        Sort-Object Name

    if ($parts.Count -eq 0) {
        throw "No parts found for $archivePath"
    }

    if ((Test-Path -LiteralPath $archivePath) -and -not $Force) {
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archivePath).Hash
        if ($hash -eq $archive.Sha256) {
            Write-Host "Already restored: $archivePath"
            continue
        }

        throw "Existing archive hash mismatch: $archivePath. Use -Force to rebuild it."
    }

    $out = [System.IO.File]::Open($archivePath, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write)
    try {
        foreach ($part in $parts) {
            $in = [System.IO.File]::OpenRead($part.FullName)
            try {
                $in.CopyTo($out)
            }
            finally {
                $in.Dispose()
            }
        }
    }
    finally {
        $out.Dispose()
    }

    $newHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archivePath).Hash
    if ($newHash -ne $archive.Sha256) {
        throw "Restored archive hash mismatch: $archivePath"
    }

    Write-Host "Restored: $archivePath"
}
