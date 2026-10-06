"""Publish only complete artifacts; never overwrite an already published version."""
import json
import os
from pathlib import Path
import subprocess

repo='User17745/jira-cli-toolkit'
root=Path('release-assets')
manifest=json.loads((root/'manifest.json').read_text()); tag=manifest['tag']
prerelease=manifest['channel']=='prerelease'
existing=subprocess.run(['gh','release','view',tag,'--repo',repo,'--json','isDraft'],capture_output=True,text=True)
if existing.returncode==0 and not json.loads(existing.stdout)['isDraft']:
    raise SystemExit('This version is already published; refusing to mutate immutable release assets.')
notes=Path('release-notes.md')
notes.write_text(f"Jira CLI Toolkit {manifest['version']}\n\nCommit: {manifest['commit']}\n\n"
                f"[Migration and roadmap](https://github.com/{repo}/blob/{tag}/docs/sprints/v2-upgrade/roadmap.md).\n\n"
                'Use the manifest for platform requirements and SHA-256 checksums. Python users retain both jsup and jira-cli-toolkit commands. '
                'API tokens and local profiles are preserved during executable updates. The repository is private; downloads require repository read access.\n\n'
                'Prereleases are for validation and do not become latest stable. macOS binaries are not notarized; Windows binaries are not code-signed.\n')
if existing.returncode!=0:
    subprocess.run(['gh','release','create',tag,'--repo',repo,'--verify-tag','--draft','--title','Jira CLI Toolkit '+manifest['version'],'--notes-file',str(notes)],check=True)
files=[str(p) for p in root.iterdir() if p.is_file()]
subprocess.run(['gh','release','upload',tag,*files,'--repo',repo,'--clobber'],check=True)
args=['gh','release','edit',tag,'--repo',repo,'--draft=false','--prerelease='+str(prerelease).lower(),'--latest=false' if prerelease else '--latest']
subprocess.run(args,check=True)
print('Published complete release: '+tag)
