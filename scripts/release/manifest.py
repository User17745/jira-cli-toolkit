"""Assemble and validate the complete release asset contract."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

from jsup import __version__
from packaging.version import Version

root=Path('release-assets'); root.mkdir(exist_ok=True)
tag=os.getenv('GITHUB_REF_NAME','v'+__version__)
if Version(tag.removeprefix('v'))!=Version(__version__):
    raise SystemExit('Tag and runtime version disagree.')
version=Version(__version__)
if not version.is_prerelease and not version.is_devrelease and os.getenv('GITHUB_REF_TYPE')=='tag':
    subprocess.run(['git','merge-base','--is-ancestor','HEAD','origin/main'],check=True)
artifacts=[]
expected={'jira-cli-toolkit-linux-x86_64','jira-cli-toolkit-macos-x86_64','jira-cli-toolkit-macos-arm64','jira-cli-toolkit-windows-x86_64.exe'}
for path in sorted(root.iterdir()):
    if path.name in {'manifest.json','SHA256SUMS'}: continue
    data=path.read_bytes()
    item=dict(name=path.name,size=len(data),sha256=hashlib.sha256(data).hexdigest())
    if path.name.startswith('jira-cli-toolkit-'):
        system,arch=path.name.removeprefix('jira-cli-toolkit-').removesuffix('.exe').split('-',1)
        item.update(kind='binary',os=system,arch=arch)
        expected.discard(path.name)
    elif path.suffix=='.whl': item['kind']='wheel'
    elif path.name.endswith('.tar.gz'): item['kind']='sdist'
    else: raise SystemExit('Unexpected release asset: '+path.name)
    artifacts.append(item)
if expected or sum(a['kind']=='wheel' for a in artifacts)!=1 or sum(a['kind']=='sdist' for a in artifacts)!=1:
    raise SystemExit('Release requires all four native binaries, one wheel and one source distribution.')
manifest=dict(schema_version=1,repository='User17745/jira-cli-toolkit',version=__version__,tag=tag,
              commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              channel='prerelease' if version.is_prerelease or version.is_devrelease else 'stable',
              python='>=3.10',platform_requirements={'linux':'glibc >=2.39 (Ubuntu 24.04 build)','macos':'macOS >=15','windows':'Windows Server 2022/Windows 10 or later; native runners validated'},
              provenance={'github_attestations':os.getenv('RELEASE_ATTESTATIONS')=='true',
                          'client_verification':'gh attestation verify ARTIFACT --repo User17745/jira-cli-toolkit'},
              publisher_verification='GitHub authenticated HTTPS; updater verifies integrity, optional attestations require separate gh verification',artifacts=artifacts)
(root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(root/'SHA256SUMS').write_text(''.join(f"{a['sha256']}  {a['name']}\n" for a in artifacts)+hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()+'  manifest.json\n')
print('Complete release manifest verified.')
