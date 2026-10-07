"""Exercise installers with the real native binary and offline release downloads."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
binary = Path(sys.argv[1]).resolve()
version = subprocess.check_output([str(binary), '--version'], text=True).strip().split()[-1]

if os.name != 'nt':
    spec = importlib.util.spec_from_file_location('installer_fixtures', ROOT/'tests/test_installers.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    case = module.InstallerTests()
    case.setUp()
    try:
        system = platform.system()
        arch = {'aarch64':'arm64', 'AMD64':'x86_64'}.get(platform.machine(), platform.machine())
        case.env.update(JIRA_INSTALL_TEST_OS=system, JIRA_INSTALL_TEST_ARCH=arch, JIRA_INSTALL_TEST_VERSION=version)
        case.prepare('macos' if system == 'Darwin' else 'linux', arch)
        target = case.assets/case.asset
        shutil.copyfile(binary, target)
        (case.assets/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in (target,case.assets/'manifest.json')))
        for args in ([], ['--version', version]):
            result = case.invoke(*args)
            assert result.returncode == 0, result.stderr
            installed = case.destination/'jira'
            assert subprocess.check_output([str(installed),'--version'],text=True).strip() == f'jira {version}'
            assert installed.read_bytes() == binary.read_bytes()
            conflict = case.invoke(*args)
            assert conflict.returncode != 0 and installed.read_bytes() == binary.read_bytes()
            shutil.rmtree(case.destination)
        with target.open('ab') as stream:
            stream.write(b'corrupt')
        result = case.invoke()
        assert result.returncode != 0 and 'Checksum mismatch' in result.stderr
        assert not case.destination.exists()
    finally:
        case.doCleanups()
else:
    shell = shutil.which('powershell.exe') or shutil.which('pwsh')
    assert shell, 'PowerShell is required for native installer CI'
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        assets = root/'assets'
        assets.mkdir()
        name = 'jira-cli-toolkit-windows-x86_64.exe'
        candidate = assets/name
        shutil.copyfile(binary, candidate)
        manifest = {'schema_version':1,'repository':'User17745/jira-cli-toolkit','channel':'stable',
                    'version':version,'tag':'v'+version,
                    'artifacts':[{'name':name,'kind':'binary','os':'windows','arch':'x86_64',
                                  'size':candidate.stat().st_size,'sha256':hashlib.sha256(candidate.read_bytes()).hexdigest()}]}
        (assets/'manifest.json').write_text(json.dumps(manifest))
        (assets/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in (candidate,assets/'manifest.json')))
        driver = root/'driver.ps1'
        driver.write_text('''
$ErrorActionPreference = 'Stop'
function Invoke-WebRequest {
    param([switch]$UseBasicParsing, [string]$Uri, [string]$OutFile)
    if ($Uri -notmatch '^https://github.com/User17745/jira-cli-toolkit/releases/(download/v[0-9.]+|latest/download)/[^/]+$') { throw "Unexpected fixture URL: $Uri" }
    Copy-Item -LiteralPath (Join-Path $env:JIRA_INSTALL_TEST_ASSETS ($Uri.Split('/')[-1])) -Destination $OutFile
}
try {
    $original = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($env:JIRA_INSTALL_TEST_LEGACY) {
        function global:jsup { 'old command' }
    }
    if ($env:JIRA_INSTALL_TEST_PINNED) {
        & $env:JIRA_INSTALL_TEST_SCRIPT -InstallDir $env:JIRA_INSTALL_TEST_DEST -Version $env:JIRA_INSTALL_TEST_PINNED -NoPath
    } else {
        & $env:JIRA_INSTALL_TEST_SCRIPT -InstallDir $env:JIRA_INSTALL_TEST_DEST -NoPath
    }
    if ([Environment]::GetEnvironmentVariable('Path', 'User') -ne $original) { throw 'NoPath altered the user PATH' }
} catch { Write-Error $_; exit 1 }
''')
        env = {**os.environ, 'PATH':str(Path(os.environ['WINDIR'])/'System32'),
               'JIRA_INSTALL_TEST_ASSETS':str(assets), 'JIRA_INSTALL_TEST_SCRIPT':str(ROOT/'scripts/install.ps1')}
        def run(destination, **changes):
            return subprocess.run([shell,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(driver)],
                                  env={**env,'JIRA_INSTALL_TEST_DEST':str(destination),**changes}, capture_output=True,text=True,timeout=90)
        for pin in ('',version):
            destination = root/('install with spaces '+(pin or 'latest'))
            result = run(destination,JIRA_INSTALL_TEST_PINNED=pin)
            assert result.returncode == 0, result.stdout+result.stderr
            installed = destination/'jira.exe'
            assert installed.read_bytes() == binary.read_bytes()
            assert subprocess.check_output([str(installed),'--version'],text=True).strip() == f'jira {version}'
            conflict = run(destination)
            assert conflict.returncode != 0 and installed.read_bytes() == binary.read_bytes()
        destination = root/'legacy conflict'
        result = run(destination,JIRA_INSTALL_TEST_LEGACY='1')
        assert result.returncode != 0 and not destination.exists()
        with candidate.open('ab') as stream:
            stream.write(b'corrupt')
        destination = root/'bad checksum'
        result = run(destination)
        assert result.returncode != 0 and 'Checksum mismatch' in result.stderr
        assert not destination.exists()
print('Native installer success, integrity and conflict checks passed.')
