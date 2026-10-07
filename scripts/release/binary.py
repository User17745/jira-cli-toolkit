"""Build and smoke the native one-file binary on the current runner."""
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile

os_name={'Darwin':'macos','Linux':'linux','Windows':'windows'}[platform.system()]
arch={'AMD64':'x86_64','aarch64':'arm64'}.get(platform.machine(),platform.machine())
name=f'jira-cli-toolkit-{os_name}-{arch}'
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile',
               '--name',name,'--collect-submodules','keyring.backends','--collect-data','jsup',
               '--copy-metadata','keyring','scripts/entrypoint.py'],check=True)
path=Path('dist')/(name+('.exe' if os_name=='windows' else ''))
with tempfile.TemporaryDirectory() as home:
    env={k:v for k,v in os.environ.items() if not k.startswith(('JIRA_','JSUP_'))}
    env.update(HOME=home,USERPROFILE=home,XDG_CONFIG_HOME=home,PYINSTALLER_RESET_ENVIRONMENT='1')
    for args in (['--version'],['--help'],['help','auth','login'],['context','show','--json'],['update','--info','--json'],['template','show','callback','--json'],['completion','bash']):
        result=subprocess.run([str(path.absolute()),*args],cwd=home,env=env,text=True,capture_output=True,timeout=60,check=True)
        if args[0]=='--version':
            from jsup import __version__
            assert result.stdout.strip()==f'jira {__version__}',result.stdout
        if args[0]=='--help':
            assert 'usage: jira ' in result.stdout,result.stdout
        if args[0]=='update':
            info=json.loads(result.stdout)
            assert info['method']=='standalone' and info['os']==os_name and info['arch']==arch,info
print(f'Native binary verified: {path}')
if re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', __version__):
    subprocess.run([sys.executable,'scripts/release/installer_smoke.py',str(path.absolute())],check=True,timeout=240)
else:
    print('Fresh installers select stable releases; prerelease builds retain native CLI smoke checks.')
if os_name=='windows':
    subprocess.run([sys.executable,'scripts/release/windows_smoke.py',str(path.absolute())],check=True,timeout=180)
