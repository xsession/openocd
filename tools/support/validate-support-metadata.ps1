# SPDX-License-Identifier: GPL-2.0-or-later
<#
.SYNOPSIS
Validate Zephyr-style support metadata references.

.DESCRIPTION
Checks support/**/*.yml and support/**/*.md for repository-relative references
to runtime and documentation paths, then verifies that those paths exist. Also
checks common status fields against the repository support vocabulary.

The script intentionally avoids a YAML dependency so it can run in a fresh
Windows package/development shell.
#>

[CmdletBinding()]
param(
  [string] $Root = '',
  [switch] $Quiet
)

$ErrorActionPreference = 'Stop'

if ($Root -eq '') {
  $scriptPath = $PSCommandPath
  if ($scriptPath -eq $null -or $scriptPath -eq '') {
    $scriptPath = $MyInvocation.MyCommand.Path
  }
  if ($scriptPath -eq $null -or $scriptPath -eq '') {
    throw 'Unable to determine script path; pass -Root explicitly.'
  }
  $Root = (Resolve-Path (Join-Path (Split-Path -Parent $scriptPath) '..\..')).Path
} else {
  $Root = (Resolve-Path $Root).Path
}

$supportRoot = Join-Path $Root 'support'
if (-not (Test-Path -LiteralPath $supportRoot)) {
  throw "support metadata root not found: $supportRoot"
}

$allowedStatuses = @(
  'integrated',
  'delegated',
  'experimental',
  'deferred',
  'blocked'
)

$pathPattern = '(tcl|docs|examples|tools|support)/[A-Za-z0-9_./-]+'
$statusPattern = '^\s*status:\s*([A-Za-z0-9_-]+)\s*$'
$files = Get-ChildItem -LiteralPath $supportRoot -Recurse -File -Include *.yml,*.md

function ConvertTo-RepoRelativePath {
  param(
    [string] $BasePath,
    [string] $FullPath
  )

  $base = (Resolve-Path $BasePath).Path.TrimEnd('\', '/')
  $full = (Resolve-Path $FullPath).Path
  if ($full.StartsWith($base + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    return $full.Substring($base.Length + 1)
  }
  return $full
}

$missingPaths = New-Object System.Collections.Generic.List[string]
$badStatuses = New-Object System.Collections.Generic.List[string]
$checkedPaths = New-Object System.Collections.Generic.HashSet[string]

foreach ($file in $files) {
  $relativeFile = ConvertTo-RepoRelativePath -BasePath $Root -FullPath $file.FullName
  $lines = Get-Content -LiteralPath $file.FullName
  for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]

    $statusMatch = [regex]::Match($line, $statusPattern)
    if ($statusMatch.Success) {
      $status = $statusMatch.Groups[1].Value
      if ($allowedStatuses -notcontains $status) {
        $badStatuses.Add("${relativeFile}:$($i + 1): unsupported status '$status'")
      }
    }

    foreach ($match in [regex]::Matches($line, $pathPattern)) {
      $repoPath = $match.Value.TrimEnd('.', ',', ';', ':')
      if ($checkedPaths.Add($repoPath)) {
        $localPath = Join-Path $Root ($repoPath -replace '/', [IO.Path]::DirectorySeparatorChar)
        if (-not (Test-Path -LiteralPath $localPath)) {
          $missingPaths.Add("${relativeFile}:$($i + 1): missing path '$repoPath'")
        }
      }
    }
  }
}

if ($badStatuses.Count -or $missingPaths.Count) {
  $newline = [Environment]::NewLine
  if ($badStatuses.Count) {
    Write-Error "Unsupported status values:`n$($badStatuses -join $newline)"
  }
  if ($missingPaths.Count) {
    Write-Error "Missing referenced paths:`n$($missingPaths -join $newline)"
  }
  exit 1
}

if (-not $Quiet) {
  Write-Host "support metadata files: $($files.Count)"
  Write-Host "unique referenced paths checked: $($checkedPaths.Count)"
  Write-Host "status vocabulary: $($allowedStatuses -join ', ')"
  Write-Host "support metadata validation passed"
}
