"""Explicit updates from verified GitHub Release assets; ordinary commands never update."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit, quote

import requests
from packaging.version import Version, InvalidVersion

from . import __version__

REPO = 'User17745/jira-cli-toolkit'
API = 'https://api.github.com/repos/'+REPO
MAX_BINARY = 250 * 1024 * 1024


class UpdateError(ValueError):
    pass


DISTRIBUTION='jira-cli-toolkit'
WINGET_ID='User17745.JiraCliToolkit'


def _distribution():
    """Package name the running code was installed under; jsup before 2.5.1."""
    from importlib.metadata import PackageNotFoundError, distribution
    for name in (DISTRIBUTION,'jsup'):
        try:
            distribution(name)
            return name
        except PackageNotFoundError:
            continue
    return None


def _winget_owns(executable) -> bool:
    """True when a winget portable install registered this executable (covers custom package roots)."""
    if os.name != 'nt':
        return False
    try:
        import winreg
    except ImportError:
        return False
    target=os.path.normcase(os.path.realpath(executable))
    path=r'Software\Microsoft\Windows\CurrentVersion\Uninstall'
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            root=winreg.OpenKey(hive,path)
        except OSError:
            continue
        with root:
            for index in range(winreg.QueryInfoKey(root)[0]):
                try:
                    with winreg.OpenKey(root,winreg.EnumKey(root,index)) as entry:
                        if winreg.QueryValueEx(entry,'WinGetPackageIdentifier')[0]!=WINGET_ID: continue
                        for name in ('TargetFullPath','InstallLocation'):
                            try: value=os.path.normcase(os.path.realpath(winreg.QueryValueEx(entry,name)[0]))
                            except OSError: continue
                            if target==value or target.startswith(value.rstrip('\\')+os.sep):
                                return True
                except OSError:
                    continue
    return False


def installation():
    if getattr(sys,'frozen',False):
        # Homebrew owns files under its Cellar; replacing them would break `brew upgrade`.
        location=str(Path(sys.executable).resolve()).replace('\\','/')
        # Package managers own these files; replacing them would break their own upgrades.
        method=('homebrew' if '/Cellar/' in location else
                'winget' if '/winget/packages/' in location.lower() or _winget_owns(sys.executable) else 'standalone')
    else:
        prefix=Path(sys.prefix)
        executable=str(Path(sys.executable).absolute()).replace('\\','/')
        if (prefix/'pipx_metadata.json').is_file() or '/pipx/venvs/' in executable:
            method='pipx'
        elif (prefix/'uv-receipt.toml').is_file() or '/uv/tools/' in executable:
            method='uv'
        else:
            method='python'
    arch={'amd64':'x86_64','x86_64':'x86_64','aarch64':'arm64','arm64':'arm64'}.get(platform.machine().lower(),platform.machine().lower())
    return dict(version=__version__,method=method,distribution=None if method in ('standalone','homebrew','winget') else _distribution(),os={'Darwin':'macos','Linux':'linux','Windows':'windows'}.get(platform.system(),'unsupported'),
                arch=arch,executable=str(Path(sys.executable).resolve()),python=sys.version.split()[0])


def github_token():
    token=os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
    if not token and shutil.which('gh'):
        try:
            result=subprocess.run(['gh','auth','token','--hostname','github.com'],capture_output=True,text=True,timeout=10)
            if result.returncode==0: token=result.stdout.strip()
        except (OSError,subprocess.TimeoutExpired):
            pass
    return token


class Releases:
    def __init__(self):
        self.session=requests.Session()
        self.session.headers.update({'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
        token=github_token()
        if token: self.session.headers['Authorization']='Bearer '+token

    def close(self): self.session.close()

    def get(self,path):
        response=self.session.get(API+path,timeout=(10,30))
        if response.status_code==404:
            raise UpdateError('Release not found or private repository access unavailable. Set GH_TOKEN with repository read access, or authenticate gh for the owning account.')
        if response.status_code in (403,429):
            raise UpdateError('GitHub access denied or rate limited. Check repository access and retry after the rate-limit window.')
        if response.status_code!=200:
            raise UpdateError(f'GitHub returned HTTP {response.status_code}.')
        try: data=response.json()
        except ValueError: raise UpdateError('GitHub returned malformed JSON.') from None
        if not isinstance(data,dict): raise UpdateError('Unexpected GitHub release response.')
        return data

    def release(self,version=None):
        tag='v'+version.removeprefix('v') if version else None
        return self.get('/releases/tags/'+quote(tag,safe='') if tag else '/releases/latest')

    def download(self,asset,destination,max_size):
        aid=asset.get('id')
        if not isinstance(aid,int) or aid<1 or not isinstance(asset.get('size'),int) or not 0<asset['size']<=max_size:
            raise UpdateError('Release asset has invalid ID or size.')
        # Construct the canonical URL rather than trusting a manifest-provided URL.
        response=self.session.get(API+'/releases/assets/'+str(aid),headers={'Accept':'application/octet-stream'},
                                  stream=True,timeout=(10,60),allow_redirects=False)
        if response.status_code in (301,302,303,307,308):
            location=response.headers.get('Location','')
            parsed=urlsplit(location)
            if parsed.scheme!='https' or parsed.hostname not in {'release-assets.githubusercontent.com','objects.githubusercontent.com','github.com'} or parsed.username:
                response.close(); raise UpdateError('Unexpected release download host.')
            response.close()
            # Never forward the GitHub token to object storage.
            response=requests.get(location,stream=True,timeout=(10,60),allow_redirects=False)
        try:
            if response.status_code!=200: raise UpdateError(f'Asset download failed (HTTP {response.status_code}).')
            size=0; digest=hashlib.sha256()
            with open(destination,'wb') as stream:
                for chunk in response.iter_content(1024*1024):
                    if not chunk: continue
                    size+=len(chunk)
                    if size>max_size or size>asset['size']: raise UpdateError('Release download exceeds its declared size.')
                    digest.update(chunk); stream.write(chunk)
                stream.flush(); os.fsync(stream.fileno())
            if size!=asset['size']: raise UpdateError('Interrupted or truncated release download.')
            return size,digest.hexdigest()
        finally:
            response.close()


def verify_manifest(manifest,release):
    if not isinstance(manifest,dict) or manifest.get('schema_version')!=1:
        raise UpdateError('Unsupported release manifest schema.')
    try:
        version=Version(manifest['version'])
        tag_version=Version(release['tag_name'].removeprefix('v'))
    except (KeyError,InvalidVersion): raise UpdateError('Invalid release version metadata.') from None
    if version!=tag_version or manifest.get('tag')!=release['tag_name']:
        raise UpdateError('Release tag and manifest version do not agree.')
    if manifest.get('repository')!=REPO or not isinstance(manifest.get('artifacts'),list):
        raise UpdateError('Invalid release repository or artifacts.')
    names=set()
    for item in manifest['artifacts']:
        name=item.get('name','')
        if not name or Path(name).name!=name or name in names or not isinstance(item.get('size'),int) or item['size']<=0 or len(item.get('sha256',''))!=64:
            raise UpdateError('Invalid or duplicate release artifact metadata.')
        names.add(name)
    return version


def probe(path,version):
    env=os.environ.copy(); env['PYINSTALLER_RESET_ENVIRONMENT']='1'
    try:
        result=subprocess.run([str(path),'--version'],capture_output=True,text=True,timeout=45,env=env,check=True)
        if Version(result.stdout.strip().split()[-1])!=Version(version):
            raise UpdateError('Candidate binary reports the wrong version.')
        subprocess.run([str(path),'--help'],capture_output=True,text=True,timeout=45,env=env,check=True)
    except (OSError,subprocess.SubprocessError,InvalidVersion,IndexError):
        raise UpdateError('Candidate executable failed its version/help checks.') from None


def _preload_output():
    """Load everything that reports the result while the original executable is still in place.

    A frozen build imports modules lazily from its own file. Once that file is replaced,
    a first import fails to decompress, as 2.1.0 does after a successful update.
    """
    from . import ui
    for console in (ui.console, ui.err_console):
        with console.capture():
            console.print({'updated': True, 'version': '0.0.0'}, markup=False)
            console.print('Update failed after replacement.', markup=False)
    import json, traceback  # noqa: F401  (error reporting paths)



def replace_binary(candidate,target,version):
    target=Path(target)
    if target.is_symlink(): raise UpdateError('Refusing to overwrite a symbolic-link installation. Update its owning manager.')
    backup=target.with_name(target.name+'.previous')
    lock=target.with_name(target.name+'.update-lock')
    deferred = False
    try:
        lock.mkdir()
    except FileExistsError: raise UpdateError('Another update is running (or left an update lock); inspect it before retrying.') from None
    try:
        if backup.exists(): raise UpdateError('A previous backup exists; preserve or remove it before another update.')
        candidate.chmod(target.stat().st_mode & 0o777)
        probe(candidate,version)
        if os.name=='nt':
            # Run a separate copy so the source candidate remains replaceable.
            staging=Path(tempfile.mkdtemp(prefix='.jira-update-',dir=target.parent))
            source=staging/'candidate.exe'; helper=staging/'helper.exe'
            shutil.copy2(candidate,source); shutil.copy2(candidate,helper)
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            env=os.environ.copy(); env['PYINSTALLER_RESET_ENVIRONMENT']='1'
            with open(staging/'helper.log','w') as log:
                subprocess.Popen([str(helper),'--_apply-update',str(source),str(target),str(os.getpid()),version,digest],
                                 stdout=log,stderr=log,env=env,creationflags=0x00000008)
            deferred=True
            return {'pending':True,'log':str(staging/'helper.log')}
        _preload_output()
        os.replace(target,backup)
        try:
            os.replace(candidate,target)
            probe(target,version)
        except Exception:
            os.replace(backup,target)
            raise UpdateError('Update failed after replacement; the previous executable was restored.') from None
        # Preserve the backup for explicit executable rollback; config is untouched.
    finally:
        if not deferred:
            lock.rmdir()


def apply_windows_update(values):
    """Private helper entry point: wait for the parent, replace, validate, rollback."""
    if os.name!='nt' or not getattr(sys,'frozen',False) or len(values)!=5:
        raise UpdateError('The update helper is supported only in a standalone Windows binary.')
    source,target,pid,version,digest=values
    source,target=Path(source).absolute(),Path(target).absolute()
    lock=target.with_name(target.name+'.update-lock'); backup=target.with_name(target.name+'.previous')
    if source.parent.parent!=target.parent or not source.parent.name.startswith('.jira-update-') or not lock.is_dir() or target.is_symlink():
        raise UpdateError('Invalid staged update paths.')
    if Version(version)!=Version(__version__) or hashlib.sha256(source.read_bytes()).hexdigest()!=digest:
        raise UpdateError('Staged update checksum/version mismatch.')
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.windll.kernel32
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x00100000,False,int(pid))
    if handle:
        try:
            if kernel.WaitForSingleObject(handle,120000)!=0:
                raise UpdateError('The old executable did not exit; installation is unchanged.')
        finally:
            kernel.CloseHandle(handle)
    moved=False
    try:
        for attempt in range(20):
            try:
                os.replace(target,backup)
                moved=True
                break
            except PermissionError:
                if attempt==19: raise
                time.sleep(0.5)
        os.replace(source,target)
        probe(target,version)
        print('Update completed; previous executable retained at '+str(backup))
    except Exception:
        if moved:
            os.replace(backup,target)
        raise UpdateError('Windows update failed; the previous executable was retained/restored. See helper.log.') from None
    finally:
        lock.rmdir()


def handle(args):
    installed=installation()
    if args.info: return installed
    if args.version and installed['method']=='homebrew':
        # The tap only offers its latest stable release; brew can't install another one.
        raise UpdateError(f'Homebrew installs follow the tap\'s latest stable release; run brew upgrade {DISTRIBUTION}. '
                          f'For a specific version, use that release\'s binary or pipx install \'{DISTRIBUTION}==VERSION\'.')
    try: requested=Version(args.version.removeprefix('v')) if args.version else None
    except InvalidVersion: raise UpdateError('Use a valid release version.') from None
    if requested and requested.is_prerelease and not args.prerelease:
        raise UpdateError('Prerelease versions require --prerelease.')
    if requested and requested<Version(__version__) and not args.allow_downgrade:
        raise UpdateError('Downgrades require --allow-downgrade.')
    if installed['method']=='winget':
        # winget can install a specific published version itself.
        target=f" --version {args.version.removeprefix('v')}" if args.version else ''
        command=(f'winget install --id {WINGET_ID} --exact{target} --force' if target else f'winget upgrade --id {WINGET_ID} --exact')
        return {**installed,'updated':False,'instructions':command,
                'note':'winget manages this installation, so jira does not replace its own file.'}
    api=Releases()
    try:
        release=api.release(args.version)
        if release.get('draft'): raise UpdateError('Draft releases cannot be installed.')
        if release.get('prerelease') and not args.prerelease: raise UpdateError('Prerelease requires explicit --prerelease.')
        assets={a['name']:a for a in release.get('assets',[]) if a.get('state')=='uploaded'}
        if 'manifest.json' not in assets: raise UpdateError('Release is incomplete: manifest.json is missing.')
        with tempfile.TemporaryDirectory(prefix='jira-update-') as temp:
            manifest_path=Path(temp)/'manifest.json'
            api.download(assets['manifest.json'],manifest_path,2*1024*1024)
            try: manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
            except (ValueError,UnicodeError): raise UpdateError('Invalid release manifest.') from None
            version=verify_manifest(manifest,release)
            if version.is_prerelease and not args.prerelease: raise UpdateError('Prerelease requires --prerelease.')
            if version<Version(__version__) and not args.allow_downgrade: raise UpdateError('Release is older than this installation; use --allow-downgrade explicitly.')
            available=version!=Version(__version__)
            result={**installed,'available_version':str(version),'update_available':available,'release_url':release.get('html_url'),'updated':False}
            if args.check or not available: return result
            if installed['method']=='homebrew':
                result.update(instructions=f'brew upgrade {DISTRIBUTION}',
                              note='Homebrew manages this installation; the tap picks up new releases within a day.')
                return result
            if installed['method']!='standalone':
                wheel=next((a for a in manifest['artifacts'] if a.get('kind')=='wheel'),None)
                if not wheel: raise UpdateError('Release has no Python wheel for this installation.')
                # Exact versions also select release candidates, which pip skips by default.
                package=f'{DISTRIBUTION}=={version}'
                instructions={'pipx':f"pipx install --force '{package}'", 'uv':f"uv tool install --force '{package}'",
                              'python':f"{sys.executable} -m pip install --upgrade '{package}'"}
                # Never mutate an unrelated Python or manager environment; the owning manager upgrades it.
                result.update(instructions=instructions[installed['method']], wheel=wheel['name'],
                              note=f'{DISTRIBUTION} is published on PyPI. To install offline instead, download {wheel["name"]} '
                                   'from this release, verify its manifest checksum, and pass its path to the same command.')
                if installed.get('distribution')=='jsup':
                    # Both distributions ship the jsup module, so the old one must go first; side by side,
                    # uninstalling either later would remove files the other still uses.
                    remove={'pipx':'pipx uninstall jsup','uv':'uv tool uninstall jsup',
                            'python':f'{sys.executable} -m pip uninstall jsup'}[installed['method']]
                    result['migration']=(f"This installation uses the package's old name, jsup. Switch once: {remove}, "
                                         f"then {instructions[installed['method']]}. Configuration and saved credentials are kept.")
                return result
            match=[a for a in manifest['artifacts'] if a.get('kind')=='binary' and a.get('os')==installed['os'] and a.get('arch')==installed['arch']]
            if len(match)!=1: raise UpdateError('No compatible binary for this platform/architecture.')
            item=match[0]
            if item['name'] not in assets: raise UpdateError('Release binary is missing.')
            if not args.yes:
                if args.no_input or args.json or not sys.stdin.isatty(): raise UpdateError('Pass --yes to confirm the executable update.')
                from .ui import confirm
                if not confirm(f'Install {version}?'): raise UpdateError('Update declined.')
            target=Path(sys.executable).absolute()
            with tempfile.TemporaryDirectory(prefix='.jira-update-',dir=target.parent) as staged:
                candidate=Path(staged)/item['name']
                size,digest=api.download(assets[item['name']],candidate,MAX_BINARY)
                if size!=item['size'] or digest!=item['sha256']: raise UpdateError('Release binary checksum/size mismatch; installation was not changed.')
                candidate.chmod(0o700)
                replacement=replace_binary(candidate,target,str(version))
            if replacement:
                result.update(replacement)
            else:
                result['updated']=True
            return result
    finally:
        api.close()
