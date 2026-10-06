"""Exercise the real Windows helper after its parent Python process exits."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from jsup import __version__
from jsup.update import probe, replace_binary

if len(sys.argv)>2 and sys.argv[1]=='driver':
    result=replace_binary(Path(sys.argv[2]),Path(sys.argv[3]),__version__)
    assert result['pending']
else:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        target=Path(temp)/'jira-cli-toolkit.exe'
        candidate=Path(temp)/'candidate.exe'
        shutil.copy2(sys.argv[1],target); shutil.copy2(sys.argv[1],candidate)
        subprocess.run([sys.executable,__file__,'driver',str(candidate),str(target)],check=True)
        lock=target.with_name(target.name+'.update-lock')
        for _ in range(120):
            if not lock.exists(): break
            time.sleep(1)
        assert not lock.exists(), 'Windows helper did not complete'
        assert target.with_name(target.name+'.previous').exists(), 'Backup missing'
        probe(target,__version__)
    print('Windows deferred replacement and post-update probe passed.')
