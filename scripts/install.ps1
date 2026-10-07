# Install a verified stable native Jira CLI. Never reads Jira credentials.
[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'JiraCLI\bin'),
    [string]$Version = '',
    [switch]$NoPath
)
$ErrorActionPreference = 'Stop'
$repo = 'User17745/jira-cli-toolkit'
$work = $null
$stage = $null
try {
    $osMajor = (Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').CurrentMajorVersionNumber
    if ($osMajor -lt 10) { throw 'Native binaries require Windows 10 or later. Use the Python wheel on older supported systems.' }
    if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64') {
        throw 'Native Windows binaries support x86_64 only. Use the Python wheel on other architectures.'
    }
    $target = Join-Path $InstallDir 'jira.exe'
    if (Test-Path -LiteralPath $target) { throw "Already installed at $target. Use jira update --yes, or update through its owning package manager." }
    foreach ($commandName in @('jira', 'jsup', 'jira-cli-toolkit')) {
        $existing = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($existing) { throw "A $commandName command already exists on PATH. Update its owning installation instead of creating a conflicting command." }
    }
    if ((Test-Path -LiteralPath $InstallDir) -and ((Get-Item -LiteralPath $InstallDir).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'The installation directory must not be a symbolic link or junction.'
    }
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $work = Join-Path ([IO.Path]::GetTempPath()) ('jira-install-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $work | Out-Null
    $manifestPath = Join-Path $work 'manifest.json'
    if ($Version) {
        $tag = 'v' + $Version.TrimStart('v')
        if ($tag -notmatch '^v[0-9]+\.[0-9]+\.[0-9]+$') { throw 'Choose a stable semantic version, for example 2.1.0.' }
        $manifestUrl = "https://github.com/$repo/releases/download/$tag/manifest.json"
    } else { $manifestUrl = "https://github.com/$repo/releases/latest/download/manifest.json" }
    Invoke-WebRequest -UseBasicParsing -Uri $manifestUrl -OutFile $manifestPath
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($manifest.schema_version -ne 1 -or $manifest.repository -ne $repo -or $manifest.channel -ne 'stable' -or $manifest.version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+$' -or $manifest.tag -ne ('v' + $manifest.version)) {
        throw 'Unexpected release manifest. Nothing was installed.'
    }
    if ($Version -and $manifest.tag -ne $tag) { throw 'Requested version and manifest disagree.' }
    $tag = $manifest.tag
    $base = "https://github.com/$repo/releases/download/$tag"
    $checksumsPath = Join-Path $work 'SHA256SUMS'
    Invoke-WebRequest -UseBasicParsing -Uri "$base/SHA256SUMS" -OutFile $checksumsPath
    function Assert-Checksum([string]$File, [string]$Name) {
        $matches = @(Get-Content -LiteralPath $checksumsPath | Where-Object { $_ -match ('^[0-9a-fA-F]{64}  ' + [regex]::Escape($Name) + '$') })
        if ($matches.Count -ne 1) { throw "Missing, duplicate or malformed checksum for $Name." }
        $expected = $matches[0].Substring(0, 64)
        if ((Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash -ne $expected) { throw "Checksum mismatch for $Name. Nothing was installed." }
    }
    Assert-Checksum $manifestPath 'manifest.json'
    $assetName = 'jira-cli-toolkit-windows-x86_64.exe'
    $artifacts = @($manifest.artifacts | Where-Object { $_.name -eq $assetName -and $_.kind -eq 'binary' -and $_.os -eq 'windows' -and $_.arch -eq 'x86_64' })
    if ($artifacts.Count -ne 1) { throw 'A compatible Windows binary is missing from the manifest.' }
    $candidate = Join-Path $work $assetName
    Write-Host "Downloading Jira CLI $($manifest.version) for Windows/x86_64…"
    Invoke-WebRequest -UseBasicParsing -Uri "$base/$assetName" -OutFile $candidate
    Assert-Checksum $candidate $assetName
    if ((Get-Item -LiteralPath $candidate).Length -ne $artifacts[0].size -or (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash -ne $artifacts[0].sha256) {
        throw 'Binary size/hash does not match its manifest. Nothing was installed.'
    }
    $reported = & $candidate --version
    if ($LASTEXITCODE -ne 0 -or $reported -ne "jira $($manifest.version)") { throw 'The verified binary reports an unexpected version.' }
    & $candidate --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'The verified binary did not pass its help check.' }
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    $stage = Join-Path $InstallDir ('.jira-install-' + [Guid]::NewGuid().ToString('N') + '.exe')
    Copy-Item -LiteralPath $candidate -Destination $stage
    [IO.File]::Move($stage, $target) # Refuses to overwrite a concurrently created destination.
    $stage = $null
    if (-not $NoPath) {
        $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
        $parts = @($userPath -split ';' | Where-Object { $_ })
        if ($parts -notcontains $InstallDir) {
            [Environment]::SetEnvironmentVariable('Path', (($parts + $InstallDir) -join ';'), 'User')
        }
        if (($env:Path -split ';') -notcontains $InstallDir) { $env:Path += ';' + $InstallDir }
    }
    Write-Host "Installed $reported at $target"
    Write-Host 'Open a new terminal if needed, then run: jira auth login --profile work'
    Write-Host "Manual releases: https://github.com/$repo/releases/latest"
} finally {
    if ($stage -and (Test-Path -LiteralPath $stage)) { Remove-Item -LiteralPath $stage -Force }
    if ($work -and (Test-Path -LiteralPath $work)) { Remove-Item -LiteralPath $work -Recurse -Force }
}
