"""Publish only complete artifacts; never overwrite an already published version."""
import json
import os
from pathlib import Path
import subprocess
from packaging.version import Version

repo='User17745/jira-cli-toolkit'
root=Path('release-assets')
manifest=json.loads((root/'manifest.json').read_text()); tag=manifest['tag']
prerelease=manifest['channel']=='prerelease'
existing=subprocess.run(['gh','release','view',tag,'--repo',repo,'--json','isDraft'],capture_output=True,text=True)
if existing.returncode==0 and not json.loads(existing.stdout)['isDraft']:
    published=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/{tag}'],text=True))
    asset=next((a for a in published['assets'] if a['name']=='manifest.json'),None)
    if not asset: raise SystemExit('Published release has no manifest; manual repair is required.')
    original=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/assets/{asset["id"]}','-H','Accept: application/octet-stream'],text=True))
    if original['commit']!=manifest['commit'] or original['version']!=manifest['version']:
        raise SystemExit('Published release does not match the requested commit/version.')
    assets={a['name']:a for a in published['assets']}
    for item in original['artifacts']:
        if item['name'] not in assets or assets[item['name']]['size']!=item['size']:
            raise SystemExit('Published release is incomplete; refusing to overwrite it.')
    print('Matching complete release already published; preserving its assets.')
    raise SystemExit(0)
notes=Path('release-notes.md')
notes.write_text(f"Jira CLI Toolkit {manifest['version']}\n\nCommit: {manifest['commit']}\n\n"
                f"[Migration and roadmap](https://github.com/{repo}/blob/{tag}/docs/sprints/v2-upgrade/roadmap.md).\n\n"
                'Use the manifest for platform requirements and SHA-256 checksums. Use the short jira command. Python users also retain jsup and jira-cli-toolkit compatibility commands. '
                'API tokens and local profiles are preserved during executable updates. The repository and release assets are public; downloads do not require GitHub or Jira credentials.\n\n'
                'Prereleases are for validation and do not become latest stable. macOS binaries are not notarized; Windows binaries are not code-signed.\n')
if existing.returncode!=0:
    subprocess.run(['gh','release','create',tag,'--repo',repo,'--verify-tag','--draft','--title','Jira CLI Toolkit '+manifest['version'],'--notes-file',str(notes)],check=True)
files=[str(p) for p in root.iterdir() if p.is_file()]
subprocess.run(['gh','release','upload',tag,*files,'--repo',repo,'--clobber'],check=True)
latest=False
if not prerelease:
    current=subprocess.run(['gh','api',f'repos/{repo}/releases/latest'],capture_output=True,text=True)
    if current.returncode==0:
        latest=Version(manifest['version'])>Version(json.loads(current.stdout)['tag_name'].removeprefix('v'))
    elif 'HTTP 404' in current.stderr:
        latest=True
    else:
        raise SystemExit('Could not validate latest stable; leaving the release as a draft.')
args=['gh','release','edit',tag,'--repo',repo,'--draft=false','--prerelease='+str(prerelease).lower(),'--latest' if latest else '--latest=false']
subprocess.run(args,check=True)
print('Published complete release: '+tag)
