param(
  [string]$Version = "latest",
  [string]$Repo = "kenzot25/nexo",
  [string]$InstallDir = "$env:LOCALAPPDATA\nexo\bin",
  [string]$Checksum = "",
  [string]$SourceDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-AssetNames {
  param(
    [Parameter(Mandatory = $true)][string]$Os,
    [Parameter(Mandatory = $true)][string]$Arch
  )

  if ($Os -ne "Windows") {
    throw "install.ps1 supports Windows only. Use scripts/install.sh for macOS/Linux."
  }

  switch ($Arch.ToLowerInvariant()) {
    "x64" { return @("nexo-windows-x64.zip", "nexo-windows-x64.zip") }
    "amd64" { return @("nexo-windows-x64.zip", "nexo-windows-x64.zip") }
    "x86_64" { return @("nexo-windows-x64.zip", "nexo-windows-x64.zip") }
    "arm64" { return @("nexo-windows-arm64.zip", "nexo-windows-arm64.zip") }
    default { throw "Unsupported architecture '$Arch'. Supported: x64, arm64." }
  }
}

function Resolve-Version {
  param(
    [string]$InputVersion,
    [string]$RepoName
  )
  if ($InputVersion -and $InputVersion -ne "latest") {
    return $InputVersion
  }

  $latestUrl = "https://api.github.com/repos/$RepoName/releases/latest"
  try {
    $release = Invoke-RestMethod -Uri $latestUrl -Headers @{"User-Agent" = "nexo-installer"}
  } catch {
    throw "Failed to query latest release from $latestUrl"
  }

  if (-not $release.tag_name) {
    throw "Could not resolve latest release tag. Provide -Version explicitly."
  }

  return [string]$release.tag_name
}

function Get-ExpectedSha256 {
  param(
    [string]$RepoName,
    [string]$VersionTag,
    [string]$AssetName,
    [string]$ChecksumOverride
  )

  if ($ChecksumOverride) {
    return $ChecksumOverride.Trim().ToLowerInvariant()
  }

  $checksumsUrl = "https://github.com/$RepoName/releases/download/$VersionTag/checksums.txt"
  try {
    $checksums = Invoke-WebRequest -Uri $checksumsUrl -UseBasicParsing
  } catch {
    return ""
  }

  foreach ($line in ($checksums.Content -split "`n")) {
    $trimmed = $line.Trim()
    if (-not $trimmed) {
      continue
    }
    $parts = $trimmed -split "\s+", 2
    if ($parts.Length -lt 2) {
      continue
    }
    if ($parts[1].Trim() -eq $AssetName) {
      return $parts[0].Trim().ToLowerInvariant()
    }
  }

  return ""
}

function Get-PythonLauncher {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    return "py"
  }
  if (Get-Command python -ErrorAction SilentlyContinue) {
    return "python"
  }
  if (Get-Command python3 -ErrorAction SilentlyContinue) {
    return "python3"
  }
  return ""
}

function Bootstrap-Python {
  Write-Host "Python not found. Bootstrapping Python..."

  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "  trying: winget install Python.Python.3.12"
    winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -eq 0) {
      $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                  [System.Environment]::GetEnvironmentVariable("Path", "User")
      Write-Host "Python bootstrap: complete (winget)"
      return
    }
    Write-Host "  winget install failed (exit $LASTEXITCODE), trying next method..."
  }

  Write-Host "  note: Microsoft Store install requires user interaction."
  Write-Host "        You can open it manually: ms-windows-store://pdp/?ProductId=9NCVDN91XZQP"

  Write-Host "  trying: python.org silent installer"
  $pyInstaller = Join-Path $env:TEMP "python-3.12-installer.exe"
  # Pin to 3.12.0; update this URL when a newer patch is released
  $pyUrl = "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe"
  try {
    Invoke-WebRequest -Uri $pyUrl -OutFile $pyInstaller -UseBasicParsing
    Start-Process -FilePath $pyInstaller `
      -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" `
      -Wait -NoNewWindow
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
    Write-Host "Python bootstrap: complete (python.org installer)"
    return
  } catch {
    Write-Host "  python.org installer failed: $_"
  }

  Write-Error @"
Python could not be installed automatically.
Install Python 3.10+ manually from https://www.python.org/downloads/ and re-run this script.
"@
  exit 1
}

function Ensure-Python {
  $launcher = Get-PythonLauncher
  if (-not $launcher) {
    Bootstrap-Python
    $launcher = Get-PythonLauncher
    if (-not $launcher) {
      Write-Error "Python bootstrap completed but no launcher found. Restart your terminal and re-run."
      exit 1
    }
  }
  return $launcher
}

function Invoke-Python {
  param(
    [Parameter(Mandatory = $true)][string]$Launcher,
    [Parameter(Mandatory = $true)][string[]]$Args
  )

  if ($Launcher -eq "py") {
    & py -3 @Args
  } elseif ($Launcher -eq "python") {
    & python @Args
  } else {
    & python3 @Args
  }
}

function Install-FromSource {
  param(
    [Parameter(Mandatory = $true)][string]$InstallPath,
    [Parameter(Mandatory = $true)][string]$SourcePath
  )

  $launcher = Ensure-Python

  Write-Host "  fallback:  local source install"
  Write-Host "  source:    $SourcePath"

  Invoke-Python -Launcher $launcher -Args @("-m", "pip", "install", "--user", "--upgrade", $SourcePath) | Out-Host
  if ($LASTEXITCODE -ne 0) {
    throw "Local source install failed. Check Python/pip setup and project metadata."
  }

  $pythonExe = (Invoke-Python -Launcher $launcher -Args @("-c", "import sys; print(sys.executable)") | Select-Object -Last 1).Trim()
  if (-not $pythonExe) {
    throw "Could not determine Python executable after install."
  }

  New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
  $legacyExe = Join-Path $InstallPath "nexo.exe"
  if (Test-Path $legacyExe) {
    Remove-Item -Path $legacyExe -Force
  }

  $target = Join-Path $InstallPath "nexo.cmd"
  $shim = @(
    "@echo off",
    ('"{0}" -m nexo %*' -f $pythonExe)
  )
  Set-Content -Path $target -Value $shim -Encoding ascii
  return $target
}

function Install-FromWheelAsset {
  param(
    [Parameter(Mandatory = $true)][string]$InstallPath,
    [Parameter(Mandatory = $true)][string]$RepoName,
    [Parameter(Mandatory = $true)][string]$VersionTag,
    [Parameter(Mandatory = $true)][string]$ChecksumOverride,
    [Parameter(Mandatory = $true)][string]$TempRoot
  )

  $launcher = Ensure-Python

  $normalized = $VersionTag
  if ($normalized.StartsWith("v")) {
    $normalized = $normalized.Substring(1)
  }
  $wheelAsset = "nexo-$normalized-py3-none-any.whl"
  $wheelUrl = "https://github.com/$RepoName/releases/download/$VersionTag/$wheelAsset"
  $wheelPath = Join-Path $TempRoot $wheelAsset

  Write-Host "  fallback:  wheel"
  Write-Host "  asset:     $wheelAsset"
  Write-Host "  download:  $wheelUrl"

  Invoke-WebRequest -Uri $wheelUrl -OutFile $wheelPath -UseBasicParsing

  $expectedSha = Get-ExpectedSha256 -RepoName $RepoName -VersionTag $VersionTag -AssetName $wheelAsset -ChecksumOverride $ChecksumOverride
  if ($expectedSha) {
    $actualSha = (Get-FileHash -Path $wheelPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualSha -ne $expectedSha) {
      throw "Checksum mismatch for $wheelAsset. Expected $expectedSha, got $actualSha"
    }
    Write-Host "  checksum:  verified"
  } else {
    Write-Host "  checksum:  skipped (no checksums.txt or -Checksum provided)"
  }

  Invoke-Python -Launcher $launcher -Args @("-m", "pip", "install", "--user", "--upgrade", $wheelPath) | Out-Host
  if ($LASTEXITCODE -ne 0) {
    throw "Wheel install failed. Check Python/pip setup and release assets."
  }

  $pythonExe = (Invoke-Python -Launcher $launcher -Args @("-c", "import sys; print(sys.executable)") | Select-Object -Last 1).Trim()
  if (-not $pythonExe) {
    throw "Could not determine Python executable after wheel install."
  }

  New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
  $legacyExe = Join-Path $InstallPath "nexo.exe"
  if (Test-Path $legacyExe) {
    Remove-Item -Path $legacyExe -Force
  }

  $target = Join-Path $InstallPath "nexo.cmd"
  $shim = @(
    "@echo off",
    ('"{0}" -m nexo %*' -f $pythonExe)
  )
  Set-Content -Path $target -Value $shim -Encoding ascii
  return $target
}

function Ensure-InstallDirOnPath {
  param([Parameter(Mandatory = $true)][string]$InstallPath)

  $userUpdated = $false
  $sessionUpdated = $false
  $userHasEntry = $false

  $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $userParts = @()
  if (-not [string]::IsNullOrWhiteSpace($userPath)) {
    $userParts = $userPath -split ";"
  }

  if ($userParts -contains $InstallPath) {
    $userHasEntry = $true
  } else {
    try {
      $newUserPath = if ([string]::IsNullOrWhiteSpace($userPath)) {
        $InstallPath
      } else {
        $userPath.TrimEnd(';') + ";" + $InstallPath
      }
      [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
      $userUpdated = $true
      $userHasEntry = $true
    } catch {
      $userHasEntry = $false
    }
  }

  if (-not (($env:Path -split ";") -contains $InstallPath)) {
    $env:Path = "$InstallPath;$env:Path"
    $sessionUpdated = $true
  }

  return [PSCustomObject]@{
    UserUpdated    = $userUpdated
    SessionUpdated = $sessionUpdated
    UserHasEntry   = $userHasEntry
  }
}

function Resolve-Architecture {
  # PowerShell 5.1 can expose RuntimeInformation without OSArchitecture; use fallback env vars.
  try {
    $runtimeInfoType = [System.Runtime.InteropServices.RuntimeInformation]
    $archProp = $runtimeInfoType.GetProperty("OSArchitecture")
    if ($archProp) {
      $resolved = [string]$archProp.GetValue($null)
      if (-not [string]::IsNullOrWhiteSpace($resolved)) {
        return $resolved
      }
    }
  } catch {
    # Continue to fallback detection.
  }

  $candidates = @($env:PROCESSOR_ARCHITEW6432, $env:PROCESSOR_ARCHITECTURE)
  foreach ($candidate in $candidates) {
    if ([string]::IsNullOrWhiteSpace($candidate)) {
      continue
    }

    switch ($candidate.ToUpperInvariant()) {
      "AMD64" { return "x64" }
      "X86_64" { return "x64" }
      "X64" { return "x64" }
      "ARM64" { return "arm64" }
      "AARCH64" { return "arm64" }
      "X86" { return "x86" }
    }
  }

  if ([Environment]::Is64BitOperatingSystem) {
    return "x64"
  }

  return "x86"
}

function Resolve-TempRoot {
  $tempPath = $env:TEMP
  if ([string]::IsNullOrWhiteSpace($tempPath)) {
    $tempPath = [System.IO.Path]::GetTempPath()
  }
  if ([string]::IsNullOrWhiteSpace($tempPath)) {
    throw "Could not determine a temporary directory. Set TEMP or TMP and retry."
  }
  return (Join-Path $tempPath "nexo-install")
}

$arch = Resolve-Architecture
$assetNames = Get-AssetNames -Os "Windows" -Arch $arch
$legacyRepo = "kenzot25/nexo"
$repoCandidates = @($Repo)
if ($Repo -ne $legacyRepo) {
  $repoCandidates += $legacyRepo
}

$localSourceCandidate = ""
if ($SourceDir) {
  $localSourceCandidate = (Resolve-Path $SourceDir).Path
} else {
  $repoRootCandidate = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  if (Test-Path (Join-Path $repoRootCandidate "pyproject.toml")) {
    $localSourceCandidate = $repoRootCandidate
  }
}

$resolvedRepo = $null
$resolvedVersion = $null
foreach ($repoCandidate in $repoCandidates) {
  try {
    $resolvedVersion = Resolve-Version -InputVersion $Version -RepoName $repoCandidate
    $resolvedRepo = $repoCandidate
    break
  } catch {
    continue
  }
}

if (-not $resolvedRepo -or -not $resolvedVersion) {
  if ($localSourceCandidate) {
    Write-Host "Installing nexo"
    Write-Host "  fallback:  local source install"
    Write-Host "  source:    $localSourceCandidate"
    $target = Install-FromSource -InstallPath $InstallDir -SourcePath $localSourceCandidate
    $pathStatus = Ensure-InstallDirOnPath -InstallPath $InstallDir

    Write-Host ""
    Write-Host "Installed: $target"
    if ($pathStatus.UserUpdated) {
      Write-Host "PATH (User): updated"
    } elseif ($pathStatus.UserHasEntry) {
      Write-Host "PATH (User): already configured"
    } else {
      Write-Host "PATH (User): update failed, add manually:"
      Write-Host "  $InstallDir"
    }
    if ($pathStatus.SessionUpdated) {
      Write-Host "PATH (Session): updated for current process"
    }
    Write-Host "Run: nexo --help"

    Write-Host ""
    Write-Host "Next step: nexo install"
    exit 0
  }
  throw "Failed to query latest release. Provide -Version explicitly or pass -Repo owner/name."
}

$tmpRoot = Resolve-TempRoot
$tmpZip = $null
$tmpExtract = Join-Path $tmpRoot "extract"

$downloadUrl = $null
$assetName = $null

Write-Host "Installing nexo"
Write-Host "  repo:      $resolvedRepo"
Write-Host "  version:   $resolvedVersion"

New-Item -ItemType Directory -Path $tmpRoot -Force | Out-Null
if (Test-Path $tmpExtract) {
  Remove-Item -Path $tmpExtract -Recurse -Force
}

foreach ($candidateAsset in $assetNames) {
  $candidateUrl = "https://github.com/$resolvedRepo/releases/download/$resolvedVersion/$candidateAsset"
  $candidateZip = Join-Path $tmpRoot $candidateAsset
  try {
    Invoke-WebRequest -Uri $candidateUrl -OutFile $candidateZip -UseBasicParsing
    $assetName = $candidateAsset
    $downloadUrl = $candidateUrl
    $tmpZip = $candidateZip
    break
  } catch {
    continue
  }
}

if (-not $tmpZip -or -not (Test-Path $tmpZip)) {
  try {
    $target = Install-FromWheelAsset -InstallPath $InstallDir -RepoName $resolvedRepo -VersionTag $resolvedVersion -ChecksumOverride $Checksum -TempRoot $tmpRoot
    $pathStatus = Ensure-InstallDirOnPath -InstallPath $InstallDir

    Write-Host ""
    Write-Host "Installed: $target"
    if ($pathStatus.UserUpdated) {
      Write-Host "PATH (User): updated"
    } elseif ($pathStatus.UserHasEntry) {
      Write-Host "PATH (User): already configured"
    } else {
      Write-Host "PATH (User): update failed, add manually:"
      Write-Host "  $InstallDir"
    }
    if ($pathStatus.SessionUpdated) {
      Write-Host "PATH (Session): updated for current process"
    }
    Write-Host "Run: nexo --help"

    Write-Host ""
    Write-Host "Next step: nexo install"
    exit 0
  } catch {
    if (-not $localSourceCandidate) {
      throw
    }
  }

  if ($localSourceCandidate) {
    $target = Install-FromSource -InstallPath $InstallDir -SourcePath $localSourceCandidate
    $pathStatus = Ensure-InstallDirOnPath -InstallPath $InstallDir

    Write-Host ""
    Write-Host "Installed: $target"
    if ($pathStatus.UserUpdated) {
      Write-Host "PATH (User): updated"
    } elseif ($pathStatus.UserHasEntry) {
      Write-Host "PATH (User): already configured"
    } else {
      Write-Host "PATH (User): update failed, add manually:"
      Write-Host "  $InstallDir"
    }
    if ($pathStatus.SessionUpdated) {
      Write-Host "PATH (Session): updated for current process"
    }
    Write-Host "Run: nexo --help"

    Write-Host ""
    Write-Host "Next step: nexo install"
    exit 0
  }
  throw "Download failed. Check network/proxy access or verify release assets exist under $resolvedRepo/$resolvedVersion. If unreleased, rerun with -SourceDir <local-repo-path>."
}

Write-Host "  asset:     $assetName"
Write-Host "  download:  $downloadUrl"

$expectedSha = Get-ExpectedSha256 -RepoName $resolvedRepo -VersionTag $resolvedVersion -AssetName $assetName -ChecksumOverride $Checksum
if ($expectedSha) {
  $actualSha = (Get-FileHash -Path $tmpZip -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($actualSha -ne $expectedSha) {
    throw "Checksum mismatch for $assetName. Expected $expectedSha, got $actualSha"
  }
  Write-Host "  checksum:  verified"
} else {
  Write-Host "  checksum:  skipped (no checksums.txt or -Checksum provided)"
}

Expand-Archive -Path $tmpZip -DestinationPath $tmpExtract -Force

$exe = Get-ChildItem -Path $tmpExtract -Recurse -File | Where-Object {
  $_.Name -ieq "nexo.exe"
} | Select-Object -First 1

if (-not $exe) {
  $exe = Get-ChildItem -Path $tmpExtract -Recurse -File | Where-Object {
    $_.Name -ieq "nexo.exe"
  } | Select-Object -First 1
}

if (-not $exe) {
  throw "Archive does not contain nexo.exe"
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
$target = Join-Path $InstallDir "nexo.exe"
Copy-Item -Path $exe.FullName -Destination $target -Force
$pathStatus = Ensure-InstallDirOnPath -InstallPath $InstallDir

Write-Host ""
Write-Host "Installed: $target"
if ($pathStatus.UserUpdated) {
  Write-Host "PATH (User): updated"
} elseif ($pathStatus.UserHasEntry) {
  Write-Host "PATH (User): already configured"
} else {
  Write-Host "PATH (User): update failed, add manually:"
  Write-Host "  $InstallDir"
}
if ($pathStatus.SessionUpdated) {
  Write-Host "PATH (Session): updated for current process"
}
Write-Host "Run: nexo --help"

Write-Host ""
Write-Host "Next step: nexo install"
