param(
    [string]$OutputRoot = "artifacts/vendor-audit",
    [switch]$Fetch
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$outRoot = Join-Path $repoRoot $OutputRoot
$checkoutRoot = Join-Path $outRoot "checkouts"
$reportPath = Join-Path $outRoot "openocd-vendor-file-delta.csv"

$repos = @(
    @{ Ecosystem = "openocd-upstream"; Url = "https://github.com/openocd-org/openocd.git"; Branch = "master" },
    @{ Ecosystem = "arduino-openocd"; Url = "https://github.com/arduino/OpenOCD.git"; Branch = "master" },
    @{ Ecosystem = "espressif"; Url = "https://github.com/espressif/openocd-esp32.git"; Branch = "master" },
    @{ Ecosystem = "raspberrypi"; Url = "https://github.com/raspberrypi/openocd.git"; Branch = "rp2040-v0.12.0" },
    @{ Ecosystem = "riscv-collab"; Url = "https://github.com/riscv-collab/riscv-openocd.git"; Branch = "riscv" },
    @{ Ecosystem = "texas-instruments"; Url = "https://github.com/TexasInstruments/ti-openocd.git"; Branch = "ti-release" },
    @{ Ecosystem = "microchip-fpga"; Url = "https://github.com/microchip-fpga/openocd.git"; Branch = "main" },
    @{ Ecosystem = "nuvoton-legacy"; Url = "https://github.com/OpenNuvoton/OpenOCD-Nuvoton.git"; Branch = "master" },
    @{ Ecosystem = "wch-community"; Url = "https://github.com/jnk0le/openocd-wch.git"; Branch = "mrs-wch-riscv-230824-LIBERATED" },
    @{ Ecosystem = "zephyr-sdk"; Url = "https://github.com/zephyrproject-rtos/openocd.git"; Branch = "zephyr-20250213" }
)

$interestingRoots = @(
    "tcl",
    "src/jtag/drivers",
    "src/target",
    "src/flash/nor",
    "src/flash/nand",
    "configure.ac",
    "Makefile.am"
)

function Convert-ToSafeName {
    param([string]$Value)
    return ($Value -replace '[^A-Za-z0-9_.-]', '_')
}

function Get-RelativePath {
    param(
        [string]$Base,
        [string]$Path
    )

    $baseUri = [System.Uri]::new(($Base.TrimEnd('\') + '\'))
    $pathUri = [System.Uri]::new($Path)
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($pathUri).ToString()).Replace('/', '\')
}

function Get-InterestingFiles {
    param([string]$Root)

    foreach ($entry in $interestingRoots) {
        $path = Join-Path $Root ($entry -replace '/', '\')
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            Get-Item -LiteralPath $path
        } elseif (Test-Path -LiteralPath $path -PathType Container) {
            Get-ChildItem -LiteralPath $path -Recurse -File
        }
    }
}

New-Item -ItemType Directory -Force -Path $checkoutRoot | Out-Null

$rows = New-Object System.Collections.Generic.List[object]

foreach ($repo in $repos) {
    $safeName = Convert-ToSafeName $repo.Ecosystem
    $checkout = Join-Path $checkoutRoot $safeName

    if ($Fetch) {
        if (Test-Path -LiteralPath $checkout) {
            git -C $checkout fetch --depth 1 origin $repo.Branch
            git -C $checkout checkout FETCH_HEAD
        } else {
            git clone --depth 1 --branch $repo.Branch $repo.Url $checkout
        }
    }

    if (-not (Test-Path -LiteralPath $checkout)) {
        Write-Warning "Skipping $($repo.Ecosystem): checkout missing. Re-run with -Fetch to clone it."
        continue
    }

    foreach ($upstreamFile in Get-InterestingFiles $checkout) {
        $rel = Get-RelativePath -Base $checkout -Path $upstreamFile.FullName
        $localPath = Join-Path $repoRoot $rel

        if (-not (Test-Path -LiteralPath $localPath -PathType Leaf)) {
            $status = "new-upstream"
        } else {
            $upstreamHash = (Get-FileHash -LiteralPath $upstreamFile.FullName -Algorithm SHA256).Hash
            $localHash = (Get-FileHash -LiteralPath $localPath -Algorithm SHA256).Hash
            $status = if ($upstreamHash -eq $localHash) { "same" } else { "changed" }
        }

        if ($status -ne "same") {
            $rows.Add([pscustomobject]@{
                Ecosystem = $repo.Ecosystem
                Repository = $repo.Url
                Branch = $repo.Branch
                Status = $status
                RelativePath = $rel
                LocalPath = $localPath
                UpstreamPath = $upstreamFile.FullName
            })
        }
    }
}

New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
$rows | Sort-Object Ecosystem, Status, RelativePath | Export-Csv -NoTypeInformation -Path $reportPath

Write-Host "Wrote $($rows.Count) file delta rows to $reportPath"
