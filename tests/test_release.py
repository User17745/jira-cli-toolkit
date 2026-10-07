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
