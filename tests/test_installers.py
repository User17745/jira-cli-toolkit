"""Installer integrity, conflict and platform checks using local download fixtures."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(os.name == 'nt', 'POSIX installer; Windows is exercised by native CI')
class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'tools'
        self.bin.mkdir()
        self.assets = self.root / 'assets'
        self.assets.mkdir()
        self.destination = self.root / 'install with spaces'
        self.env = dict(os.environ, PATH=str(self.bin)+os.pathsep+os.defpath,
                        JIRA_INSTALL_TEST_ASSETS=str(self.assets),
                        JIRA_INSTALL_TEST_OS='Linux', JIRA_INSTALL_TEST_ARCH='x86_64',
                        JIRA_INSTALL_TEST_EXEC_MARKER=str(self.root/'executed'))
        self.tool('uname', 'if [ "$1" = "-s" ]; then echo "$JIRA_INSTALL_TEST_OS"; else echo "$JIRA_INSTALL_TEST_ARCH"; fi')
        self.tool('sw_vers', 'echo "${JIRA_INSTALL_TEST_MACOS:-15.4}"')
        self.tool('getconf', 'echo "${JIRA_INSTALL_TEST_GLIBC:-glibc 2.39}"')
        curl = self.bin/'curl'
        curl.write_text(f'#!{sys.executable}\n'+'''import os,sys,shutil
from pathlib import Path
args=sys.argv[1:]
url=next(a for a in args if a.startswith('https://'))
base='https://github.com/User17745/jira-cli-toolkit/releases/'
version=os.environ.get('JIRA_INSTALL_TEST_VERSION','2.1.0')
if url==base+'latest': print(base+'tag/v'+version,end='');sys.exit(0)
assert url.startswith(base+'download/v'+version+'/'),url
name=url.rsplit('/',1)[1]
source=Path(os.environ['JIRA_INSTALL_TEST_ASSETS'])/name
if not source.exists():sys.exit(22)
shutil.copyfile(source,args[args.index('-o')+1])
''')
        curl.chmod(0o755)
        self.prepare()

    def tool(self, name, script):
        p=self.bin/name
        p.write_text('#!/bin/sh\n'+script+'\n')
        p.chmod(0o755)

    def prepare(self, os_name='linux', arch='x86_64', version='2.1.0'):
        self.asset='jira-cli-toolkit-'+os_name+'-'+arch
        p=self.assets/self.asset
        p.write_text('#!/bin/sh\ntouch "$JIRA_INSTALL_TEST_EXEC_MARKER"\n'+f'if [ "$1" = "--version" ]; then echo "jira {version}"; else echo "usage: jira"; fi\n')
        manifest={'schema_version':1,'repository':'User17745/jira-cli-toolkit','version':'2.1.0','channel':'stable'}
        (self.assets/'manifest.json').write_text(json.dumps(manifest))
        (self.assets/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in (p,self.assets/'manifest.json')))

    def invoke(self, *extra):
        return subprocess.run(['bash',str(ROOT/'scripts/install.sh'),'--install-dir',str(self.destination),*extra],
                              env=self.env,capture_output=True,text=True,timeout=30)

    def test_success_latest_and_pinned_versions(self):
        for version in ([], ['--version','2.1.0']):
            with self.subTest(version=version):
                r=self.invoke(*version)
                self.assertEqual(r.returncode,0,r.stderr)
                self.assertEqual((self.destination/'jira').read_bytes(),(self.assets/self.asset).read_bytes())
                self.assertTrue(os.access(self.destination/'jira',os.X_OK))
                self.assertIn('jira auth login',r.stdout)
                shutil.rmtree(self.destination)

    def test_macos_architectures(self):
        for arch in ('arm64','x86_64'):
            with self.subTest(arch=arch):
                self.env.update(JIRA_INSTALL_TEST_OS='Darwin',JIRA_INSTALL_TEST_ARCH=arch)
                self.prepare('macos',arch)
                r=self.invoke();self.assertEqual(r.returncode,0,r.stderr)
                shutil.rmtree(self.destination)

    def test_corrupt_binary_is_not_executed_or_installed(self):
        with open(self.assets/self.asset,'a') as stream: stream.write('corrupt')
        r=self.invoke();self.assertNotEqual(r.returncode,0)
        self.assertIn('Checksum mismatch',r.stderr)
        self.assertFalse((self.root/'executed').exists())
        self.assertFalse(self.destination.exists())

    def test_corrupt_manifest_and_duplicate_checksums_fail(self):
        for mutation in ('manifest','duplicate'):
            with self.subTest(mutation=mutation):
                self.prepare()
                if mutation=='manifest':(self.assets/'manifest.json').write_text('{}')
                else:
                    p=self.assets/'SHA256SUMS';p.write_text(p.read_text()+p.read_text())
                r=self.invoke();self.assertNotEqual(r.returncode,0)
                self.assertFalse((self.root/'executed').exists())
                self.assertFalse(self.destination.exists())

    def test_wrong_version_is_not_installed(self):
        self.prepare(version='1.0.0')
        r=self.invoke();self.assertNotEqual(r.returncode,0)
        self.assertIn('unexpected version',r.stderr)
        self.assertFalse(self.destination.exists())

    def test_existing_file_or_symlink_is_not_overwritten(self):
        self.destination.mkdir()
        p=self.destination/'jira';p.write_text('existing')
        r=self.invoke();self.assertNotEqual(r.returncode,0);self.assertEqual(p.read_text(),'existing')
        p.unlink();p.symlink_to(self.root/'missing')
        r=self.invoke();self.assertNotEqual(r.returncode,0);self.assertTrue(p.is_symlink())

    def test_existing_commands_on_path_are_not_shadowed(self):
        for name in ('jira', 'jsup', 'jira-cli-toolkit'):
            with self.subTest(command=name):
                self.tool(name,'echo another CLI')
                r=self.invoke();self.assertNotEqual(r.returncode,0)
                self.assertIn('already exists',r.stderr)
                self.assertFalse(self.destination.exists())
                (self.bin/name).unlink()

    def test_unsupported_platforms_and_old_runtimes_fail(self):
        cases=[{'JIRA_INSTALL_TEST_ARCH':'aarch64'}, {'JIRA_INSTALL_TEST_GLIBC':'musl 1.2'},
               {'JIRA_INSTALL_TEST_GLIBC':'glibc 2.38'}, {'JIRA_INSTALL_TEST_OS':'Darwin','JIRA_INSTALL_TEST_MACOS':'14.6'},
               {'JIRA_INSTALL_TEST_OS':'Unknown'}]
        baseline=self.env.copy()
        for changes in cases:
            with self.subTest(changes=changes):
                self.env={**baseline,**changes}
                r=self.invoke();self.assertNotEqual(r.returncode,0)
                self.assertFalse(self.destination.exists())

    def test_missing_asset_and_invalid_version_fail(self):
        (self.assets/self.asset).unlink()
        self.assertNotEqual(self.invoke().returncode,0)
        self.assertNotEqual(self.invoke('--version','../bad').returncode,0)
        self.assertFalse(self.destination.exists())


if __name__=='__main__':unittest.main()
