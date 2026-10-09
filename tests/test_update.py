import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from jsup import update

Releases = update.Releases


def args(**kw): return SimpleNamespace(**dict(dict(info=False,version=None,prerelease=False,allow_downgrade=False,check=True,yes=False,no_input=True,json=True),**kw))


def manifest(version='2.0.0'):
    return {'schema_version':1,'repository':update.REPO,'version':version,'tag':'v'+version,
            'artifacts':[{'name':'jira-cli-toolkit-linux-x86_64','kind':'binary','os':'linux','arch':'x86_64','size':3,'sha256':hashlib.sha256(b'new').hexdigest()},
                         {'name':'jsup.whl','kind':'wheel','size':2,'sha256':'a'*64}]}


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.api=Mock()
        self.release={'tag_name':'v2.0.0','draft':False,'prerelease':False,'assets':[
            {'name':'manifest.json','id':1,'size':300,'state':'uploaded'},
            {'name':'jira-cli-toolkit-linux-x86_64','id':2,'size':3,'state':'uploaded'}]}
        self.api.release.return_value=self.release
        self.addCleanup(patch.stopall)
        # The fixture offers 2.0.0; simulate an older installation regardless of
        # the source version so a release bump cannot turn upgrade tests into no-ops.
        patch.object(update,'__version__','1.0.0').start()
        patch.object(update,'Releases',return_value=self.api).start()
        self.installed={'version':update.__version__,'method':'standalone','os':'linux','arch':'x86_64','executable':'/tmp/jira','python':'3.12'}
        patch.object(update,'installation',return_value=self.installed).start()
        self.data=manifest()
        def download(asset,path,limit):
            if asset['name']=='manifest.json': path.write_text(json.dumps(self.data)); return 300,'digest'
            path.write_bytes(b'new'); return 3,hashlib.sha256(b'new').hexdigest()
        self.api.download.side_effect=download

    def test_check_does_not_modify_installation(self):
        with patch.object(update,'replace_binary') as replacement:
            result=update.handle(args())
        self.assertTrue(result['update_available']); self.assertFalse(result['updated'])
        replacement.assert_not_called(); self.assertEqual(self.api.download.call_count,1)

    def test_info_needs_neither_credentials_nor_network(self):
        self.assertEqual(update.handle(args(info=True)),self.installed)
        self.api.release.assert_not_called()

    def test_prerelease_and_downgrade_require_opt_in(self):
        for version,message in [('2.0.0rc1','Prerelease'),('0.1.0','Downgrades')]:
            with self.subTest(version=version), self.assertRaisesRegex(update.UpdateError,message): update.handle(args(version=version))
        self.api.release.assert_not_called()

    def test_noop_same_version_does_not_require_confirmation(self):
        self.data=manifest(update.__version__); self.release['tag_name']='v'+update.__version__
        result=update.handle(args(check=False,version=update.__version__))
        self.assertFalse(result['update_available'])

    def test_incomplete_draft_and_prerelease_releases_fail(self):
        for changed in ({'draft':True},{'prerelease':True},{'assets':[]}):
            self.api.release.return_value={**self.release,**changed}
            with self.subTest(changed=changed), self.assertRaises(update.UpdateError): update.handle(args())

    def test_manifest_wrong_schema_repository_or_version_fails(self):
        for changed in ({'schema_version':2},{'repository':'other/repo'},{'version':'3.0.0'}):
            self.data={**manifest(),**changed}
            with self.subTest(changed=changed), self.assertRaises(update.UpdateError): update.handle(args())

    def test_unsupported_platform_and_confirmation_are_explicit(self):
        self.installed['arch']='arm64'
        with self.assertRaisesRegex(update.UpdateError,'compatible'): update.handle(args(check=False,yes=True))
        self.installed['arch']='x86_64'
        with self.assertRaisesRegex(update.UpdateError,'--yes'): update.handle(args(check=False))

    def test_package_manager_returns_owning_environment_instructions(self):
        expected={'pipx':"pipx install --force 'jira-cli-toolkit==",'uv':"uv tool install --force 'jira-cli-toolkit==",
                  'python':" -m pip install --upgrade 'jira-cli-toolkit=="}
        for method in ('pipx','uv','python'):
            self.installed.update(method=method,distribution='jira-cli-toolkit')
            with self.subTest(method=method):
                result=update.handle(args(check=False))
                self.assertFalse(result['updated'])
                self.assertIn(expected[method],result['instructions'])
                self.assertNotIn('migration',result)
        self.assertEqual(self.api.download.call_count,3)

    def test_homebrew_installs_are_upgraded_by_brew_not_replaced(self):
        self.installed.update(method='homebrew',distribution=None)
        with patch.object(update,'replace_binary') as replace:
            result=update.handle(args(check=False))
        replace.assert_not_called()
        self.assertEqual(result['instructions'],'brew upgrade jira-cli-toolkit')
        self.assertFalse(result['updated'])

    def test_homebrew_installs_reject_explicit_versions(self):
        self.installed.update(method='homebrew',distribution=None)
        with self.assertRaisesRegex(update.UpdateError,'latest stable release'):
            update.handle(args(check=False,version='2.0.0'))
        self.api.release.assert_not_called()

    def test_winget_installs_get_winget_commands_without_network(self):
        self.installed.update(method='winget',distribution=None)
        with patch.object(update,'replace_binary') as replace:
            result=update.handle(args(check=False))
            pinned=update.handle(args(check=False,version='2.0.0'))
        replace.assert_not_called(); self.api.release.assert_not_called()
        self.assertEqual(result['instructions'],'winget upgrade --id User17745.JiraCliToolkit --exact')
        self.assertEqual(pinned['instructions'],'winget install --id User17745.JiraCliToolkit --exact --version 2.0.0 --force')
        # Version policy applies before any manager-specific advice.
        with patch.object(update,'__version__','3.0.0'), self.assertRaisesRegex(update.UpdateError,'--allow-downgrade'):
            update.handle(args(check=False,version='2.0.0'))
        with self.assertRaisesRegex(update.UpdateError,'--prerelease'):
            update.handle(args(check=False,version='2.1.0rc1'))
        with self.assertRaisesRegex(update.UpdateError,'valid release version'):
            update.handle(args(check=False,version='latest'))

    def test_frozen_binaries_in_a_homebrew_cellar_are_detected(self):
        patch.stopall()  # setUp stubs installation(); this test needs the real one
        with patch.object(update.sys,'frozen',True,create=True), \
                patch.object(update.sys,'executable','/opt/homebrew/Cellar/jira-cli-toolkit/2.5.2/bin/jira'):
            self.assertEqual(update.installation()['method'],'homebrew')
        with patch.object(update.sys,'frozen',True,create=True), \
                patch.object(update.sys,'executable','/Users/me/.local/bin/jira'):
            self.assertEqual(update.installation()['method'],'standalone')
        winget='C:/Users/me/AppData/Local/Microsoft/WinGet/Packages/User17745.JiraCliToolkit_Microsoft.Winget.Source_8wekyb3d8bbwe/jira-cli-toolkit-windows-x86_64.exe'
        with patch.object(update.sys,'frozen',True,create=True), patch.object(update.sys,'executable',winget):
            self.assertEqual(update.installation()['method'],'winget')
        machine='C:/Program Files/WinGet/Packages/User17745.JiraCliToolkit_x/jira-cli-toolkit-windows-x86_64.exe'
        with patch.object(update.sys,'frozen',True,create=True), patch.object(update.sys,'executable',machine):
            self.assertEqual(update.installation()['method'],'winget')
        custom='D:/Tools/jira/jira-cli-toolkit-windows-x86_64.exe'
        with patch.object(update.sys,'frozen',True,create=True), patch.object(update.sys,'executable',custom), \
                patch.object(update,'_winget_owns',return_value=True):
            self.assertEqual(update.installation()['method'],'winget')

    def test_installs_tracked_as_jsup_get_a_one_time_switch(self):
        self.installed.update(method='pipx',distribution='jsup')
        result=update.handle(args(check=False))
        self.assertIn('pipx uninstall jsup, then pipx install --force',result['migration'])
        self.installed.update(method='python',distribution='jsup')
        migration=update.handle(args(check=False))['migration']
        self.assertIn(' -m pip uninstall jsup, then ',migration)
        self.assertIn("pip install --upgrade 'jira-cli-toolkit==",migration)

    def test_checksum_failure_preserves_target(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'jira'; target.write_bytes(b'old')
            self.data['artifacts'][0]['sha256']='0'*64
            with patch.object(update.sys,'executable',str(target)), patch.object(update,'replace_binary') as replace:
                with self.assertRaisesRegex(update.UpdateError,'checksum'): update.handle(args(check=False,yes=True))
                replace.assert_not_called()
            self.assertEqual(target.read_bytes(),b'old')

    @unittest.skipIf(os.name=='nt','POSIX replacement; Windows helper tested by native smoke')
    def test_binary_replacement_rolls_back_on_post_install_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'jira'; target.write_bytes(b'old'); target.chmod(0o755)
            candidate=Path(temp)/'candidate'; candidate.write_bytes(b'new')
            with patch.object(update,'probe',side_effect=[None,update.UpdateError('broken')]):
                with self.assertRaisesRegex(update.UpdateError,'restored'): update.replace_binary(candidate,target,'2.0.0')
            self.assertEqual(target.read_bytes(),b'old')
            self.assertFalse(target.with_name('jira.update-lock').exists())

    @unittest.skipIf(os.name=='nt','POSIX atomic replacement')
    def test_successful_replacement_preserves_previous_binary_and_config(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'jira'; target.write_bytes(b'old'); target.chmod(0o755)
            cfg=Path(temp)/'config.json'; cfg.write_text('keep')
            candidate=Path(temp)/'candidate'; candidate.write_bytes(b'new')
            with patch.object(update,'probe'): update.replace_binary(candidate,target,'2.0.0')
            self.assertEqual(target.read_bytes(),b'new')
            self.assertEqual(target.with_name('jira.previous').read_bytes(),b'old')
            self.assertEqual(cfg.read_text(),'keep'); self.assertEqual(target.stat().st_mode & 0o777,0o755)

    @unittest.skipIf(os.name=='nt','Windows applies updates from a helper after this process exits')
    def test_output_modules_load_before_the_executable_is_replaced(self):
        # A frozen 2.1.0 crashed after updating: rich imported rich.pretty from the replaced file.
        import sys
        for name in [m for m in sys.modules if m == 'rich.pretty' or m.startswith('rich.pretty.')]:
            del sys.modules[name]
        loaded_at_swap = []
        real_replace = update.os.replace
        def replace(source, destination):
            loaded_at_swap.append('rich.pretty' in sys.modules)
            real_replace(source, destination)
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'jira'; target.write_bytes(b'old'); target.chmod(0o755)
            candidate=Path(temp)/'candidate'; candidate.write_bytes(b'new')
            with patch.object(update,'probe'), patch.object(update.os,'replace',side_effect=replace):
                update.replace_binary(candidate,target,'2.0.0')
        self.assertTrue(loaded_at_swap and all(loaded_at_swap))

    def test_lock_and_backup_prevent_conflicting_updates(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'jira'; target.write_bytes(b'old'); candidate=Path(temp)/'new'; candidate.write_bytes(b'new')
            lock=target.with_name('jira.update-lock'); lock.mkdir()
            with self.assertRaisesRegex(update.UpdateError,'Another update'): update.replace_binary(candidate,target,'2.0.0')
            lock.rmdir(); target.with_name('jira.previous').write_bytes(b'backup')
            with self.assertRaisesRegex(update.UpdateError,'backup'): update.replace_binary(candidate,target,'2.0.0')
            self.assertFalse(lock.exists())

    def test_private_download_redirect_does_not_forward_token(self):
        api=object.__new__(Releases); api.session=Mock()
        redirect=Mock(status_code=302,headers={'Location':'https://release-assets.githubusercontent.com/blob'})
        api.session.get.return_value=redirect
        blob=Mock(status_code=200); blob.iter_content.return_value=[b'new']
        with tempfile.TemporaryDirectory() as temp, patch.object(update.requests,'get',return_value=blob) as get:
            size,digest=api.download({'id':1,'size':3},Path(temp)/'out',100)
            self.assertEqual(size,3); self.assertNotIn('headers',get.call_args.kwargs)

    def test_download_rejects_untrusted_redirect_truncation_and_excess_size(self):
        api=object.__new__(Releases); api.session=Mock()
        with tempfile.TemporaryDirectory() as temp:
            for response in (Mock(status_code=302,headers={'Location':'https://evil.invalid/blob'}),Mock(status_code=200)):
                response.iter_content.return_value=[b'x']
                api.session.get.return_value=response
                with self.assertRaises(update.UpdateError): api.download({'id':1,'size':3},Path(temp)/'out',100)
            api.session.get.return_value=Mock(status_code=200,iter_content=Mock(return_value=[b'too large']))
            with self.assertRaises(update.UpdateError): api.download({'id':1,'size':3},Path(temp)/'out',100)

    def test_github_credentials_never_borrow_jira_token(self):
        with patch.dict(os.environ,{'JIRA_API_TOKEN':'jira-secret'},clear=True),patch.object(update.shutil,'which',return_value=None):
            self.assertIsNone(update.github_token())


class InstallationTests(unittest.TestCase):
    def test_custom_manager_directories_use_receipts_and_do_not_guess_from_names(self):
        with tempfile.TemporaryDirectory(prefix='looks-like-pipx-') as temp:
            prefix=Path(temp)
            with patch.object(update.sys,'prefix',str(prefix)),patch.object(update.sys,'executable',str(prefix/'bin/python')),patch.object(update.sys,'frozen',False,create=True):
                self.assertEqual(update.installation()['method'],'python')
                (prefix/'uv-receipt.toml').write_text('fixture')
                self.assertEqual(update.installation()['method'],'uv')
                (prefix/'uv-receipt.toml').unlink()
                (prefix/'pipx_metadata.json').write_text('{}')
                self.assertEqual(update.installation()['method'],'pipx')
