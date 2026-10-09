import json
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from jsup import __version__
from jsup.update import verify_manifest

ROOT=Path(__file__).resolve().parents[1]


class ReleaseContractTests(unittest.TestCase):
    def test_manifest_requires_complete_binary_and_python_matrix(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{'GITHUB_REF_NAME':'v'+__version__,'GITHUB_REF_TYPE':'branch'},clear=False):
            original=Path.cwd()
            try:
                os.chdir(temp)
                assets=Path('release-assets'); assets.mkdir()
                names=['jira-cli-toolkit-linux-x86_64','jira-cli-toolkit-macos-x86_64','jira-cli-toolkit-macos-arm64','jira-cli-toolkit-windows-x86_64.exe','jsup.whl','jsup.tar.gz']
                for name in names: (assets/name).write_bytes(b'fixture')
                with patch('subprocess.check_output',return_value='a'*40): runpy.run_path(str(ROOT/'scripts/release/manifest.py'))
                manifest=json.loads((assets/'manifest.json').read_text())
                verify_manifest(manifest,{'tag_name':'v'+__version__})
                self.assertEqual(len(manifest['artifacts']),6)
                (assets/names[0]).unlink()
                with patch('subprocess.check_output',return_value='a'*40), self.assertRaises(SystemExit): runpy.run_path(str(ROOT/'scripts/release/manifest.py'))
            finally: os.chdir(original)

    def test_tag_version_mismatch_stops_before_publication(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'GITHUB_REF_NAME':'v99.0.0','GITHUB_REF_TYPE':'tag'}):
            original=Path.cwd()
            try:
                os.chdir(temp)
                with self.assertRaisesRegex(SystemExit,'disagree'): runpy.run_path(str(ROOT/'scripts/release/manifest.py'))
            finally: os.chdir(original)


class WingetManifestTests(unittest.TestCase):
    def test_manifests_use_the_release_windows_binary(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("winget", Path(__file__).resolve().parents[1] / "scripts" / "release" / "winget.py")
        winget = importlib.util.module_from_spec(spec); spec.loader.exec_module(winget)
        manifest = {"repository": "User17745/jira-cli-toolkit", "channel": "stable", "version": "2.6.0", "tag": "v2.6.0",
                    "artifacts": [{"name": "jira-cli-toolkit-windows-x86_64.exe", "kind": "binary", "os": "windows", "arch": "x86_64", "sha256": "ab" * 32},
                                  {"name": "jira-cli-toolkit-linux-x86_64", "kind": "binary", "os": "linux", "arch": "x86_64", "sha256": "cd" * 32}]}
        files = winget.manifests(manifest, "2026-10-09")
        installer = files["User17745.JiraCliToolkit.installer.yaml"]
        self.assertIn("InstallerUrl: https://github.com/User17745/jira-cli-toolkit/releases/download/v2.6.0/jira-cli-toolkit-windows-x86_64.exe", installer)
        self.assertIn("InstallerSha256: " + "AB" * 32, installer)
        self.assertIn("Commands:\n- jira\n", installer)
        self.assertIn("PackageVersion: 2.6.0", files["User17745.JiraCliToolkit.yaml"])
        self.assertIn("not affiliated with or endorsed by Atlassian", files["User17745.JiraCliToolkit.locale.en-US.yaml"])
        with self.assertRaises(SystemExit):
            winget.manifests({**manifest, "channel": "prerelease"}, "2026-10-09")
