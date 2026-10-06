import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from jsup import auth, config, credentials
from jsup.client import JiraError


def arguments(**kwargs):
    return SimpleNamespace(**dict(dict(profile=None,site='https://example.invalid',email='user@example.invalid',
        token='hidden-token',project=None,json=True,no_input=True,storage='keyring',token_stdin=False,
        scoped=False,cloud_id=None,cmd='auth-login'), **kwargs))


class AuthTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/'config.json'
        self.addCleanup(patch.stopall)
        patch.object(config,'CONFIG_PATH',self.path).start()
        patch.dict(os.environ,{},clear=True).start()
        self.put=patch.object(credentials,'put').start()
        self.get=patch.object(credentials,'get',return_value='hidden-token').start()
        self.delete=patch.object(credentials,'delete').start()
        self.validate=patch.object(auth,'validate',return_value={'accountId':'account-1','displayName':'Tester'}).start()

    def login(self,**kw): return auth.login(arguments(**kw))

    def test_valid_login_never_writes_token_to_preferences(self):
        data=self.login(profile='work')
        self.assertTrue(data['authenticated'])
        saved=json.loads(self.path.read_text())
        self.assertNotIn('hidden-token',self.path.read_text())
        self.assertEqual(saved['profiles']['work']['storage'],'keyring')
        self.put.assert_called_once()
        if os.name!='nt': self.assertEqual(self.path.stat().st_mode & 0o777,0o600)

    def test_invalid_credentials_are_not_persisted(self):
        self.validate.side_effect=JiraError('GET','/myself',401,'invalid')
        with self.assertRaises(JiraError): self.login()
        self.put.assert_not_called(); self.assertFalse(self.path.exists())

    def test_store_failure_never_writes_config_or_plaintext_fallback(self):
        self.put.side_effect=credentials.CredentialError('locked')
        with self.assertRaises(credentials.CredentialError): self.login()
        self.assertFalse(self.path.exists())

    def test_failed_config_write_keeps_previous_identity_and_cleans_candidate(self):
        self.login(); original=self.path.read_text()
        with patch.object(config,'atomic_json',side_effect=OSError('disk full')):
            with self.assertRaises(OSError): self.login(token='replacement')
        self.assertEqual(self.path.read_text(),original)
        self.delete.assert_called_once()

    def test_profile_identity_is_atomic(self):
        self.login(profile='work')
        for kwargs in ({'profile':'work','site':'https://other.invalid'}, {'site':'https://other.invalid'}):
            args=SimpleNamespace(**kwargs)
            with self.assertRaises(ValueError): config.resolve_config(args)
        cfg=config.resolve_config(SimpleNamespace(profile='work'))
        self.assertEqual(cfg['site'],'https://example.invalid')
        self.assertEqual(cfg['source'],'keyring')

    def test_explicit_profile_ignores_environment_identity(self):
        self.login(profile='work')
        with patch.dict(os.environ,{'JIRA_SITE':'https://other.invalid','JIRA_EMAIL':'other','JIRA_API_TOKEN':'other-token'}):
            cfg=config.resolve_config(SimpleNamespace(profile='work'))
        self.assertEqual(cfg['email'],'user@example.invalid')
        self.assertEqual(cfg['token'],'hidden-token')

    def test_complete_external_identity_does_not_read_profile_credential(self):
        self.login(); self.get.reset_mock()
        cfg=config.resolve_config(arguments(site='https://other.invalid',email='other',token='other-token'))
        self.assertEqual(cfg['source'],'flags'); self.get.assert_not_called()

    def test_context_metadata_does_not_access_keychain(self):
        self.login(); self.get.reset_mock()
        cfg=config.resolve_config(SimpleNamespace(),read_secret=False)
        self.assertEqual(cfg['site'],'https://example.invalid'); self.get.assert_not_called()

    def test_scoped_token_validates_at_gateway(self):
        self.login(scoped=True,cloud_id='cloud-123')
        self.validate.assert_called_once_with('https://api.atlassian.com/ex/jira/cloud-123','user@example.invalid','hidden-token')
        self.assertEqual(config.resolve_config(SimpleNamespace())['api_site'],'https://api.atlassian.com/ex/jira/cloud-123')

    def test_migration_is_repeatable_and_preserves_original_on_failure(self):
        old={'JIRA_SITE':'https://example.invalid','JIRA_EMAIL':'user','JIRA_API_TOKEN':'legacy-secret','JIRA_PROJECT':'ENG'}
        self.path.write_text(json.dumps(old)); original=self.path.read_text()
        self.put.side_effect=credentials.CredentialError('unavailable')
        with self.assertRaises(credentials.CredentialError): auth.migrate(arguments())
        self.assertEqual(self.path.read_text(),original)
        self.put.side_effect=None
        self.assertTrue(auth.migrate(arguments())['migrated'])
        self.assertNotIn('legacy-secret',self.path.read_text())
        self.assertFalse(auth.migrate(arguments())['migrated'])

    def test_logout_does_not_switch_profile_or_revoke_upstream_token(self):
        self.login(profile='work'); self.login(profile='other')
        result=auth.local(arguments(cmd='auth-logout',profile='work'))
        self.assertFalse(result['upstream_revoked'])
        self.assertEqual(json.loads(self.path.read_text())['active_profile'],'other')

    def test_removing_active_profile_does_not_select_another(self):
        self.login(profile='work'); self.login(profile='other')
        auth.local(arguments(cmd='profile-remove',name='other'))
        self.assertIsNone(json.loads(self.path.read_text())['active_profile'])

    def test_status_reports_auth_source_without_secret_and_no_false_refresh(self):
        self.login(); self.validate.reset_mock()
        data=auth.status(SimpleNamespace())
        self.assertTrue(data['authenticated']); self.assertFalse(data['refresh_supported'])
        self.assertNotIn('hidden-token',json.dumps(data))
        self.validate.assert_called_once()

    def test_recovery_cannot_switch_account(self):
        self.login(); original=self.path.read_text()
        self.validate.return_value={'accountId':'other-account'}
        with self.assertRaisesRegex(ValueError,'cannot change'):
            auth.login(arguments(site='https://other.invalid',email=None,token='replacement'),replace=True)
        self.assertEqual(self.path.read_text(),original)

    def test_recovery_checks_account_and_retains_old_credential(self):
        self.login(); original=self.path.read_text()
        self.validate.return_value={'accountId':'other-account'}
        with self.assertRaisesRegex(ValueError,'different account'):
            auth.login(arguments(site=None,email=None,token='replacement'),replace=True)
        self.assertEqual(self.path.read_text(),original)

    def test_no_input_never_prompts(self):
        with patch('builtins.input',side_effect=AssertionError('prompt')), patch('getpass.getpass',side_effect=AssertionError('prompt')):
            with self.assertRaises(ValueError): self.login(site=None,email=None,token=None)

    def test_invalid_site_or_profile_rejected_before_validation(self):
        for kw in ({'site':'http://example.invalid'}, {'site':'https://user:secret@example.invalid'}, {'profile':'../work'}):
            with self.subTest(kw=kw), self.assertRaises(ValueError): self.login(**kw)
        self.validate.assert_not_called()

    def test_malformed_config_is_not_silently_discarded(self):
        for content in ('[]','{oops'):
            self.path.write_text(content)
            with self.assertRaises(ValueError): config.resolve_config(SimpleNamespace())


class CredentialTests(unittest.TestCase):
    def test_native_store_failure_does_not_use_plaintext(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(credentials,'_keyring',side_effect=credentials.CredentialError('locked')):
            path=Path(temp)/'config.json'
            with self.assertRaises(credentials.CredentialError): credentials.put({'storage':'keyring','credential_id':'1'},'secret',path)
            self.assertFalse(path.with_name('credentials.json').exists())

    @unittest.skipIf(os.name=='nt','POSIX file storage only')
    def test_explicit_file_store_protects_permissions_and_deletes_selected_token(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'config.json'; settings={'storage':'file','credential_id':'1'}
            credentials.put(settings,'secret',path)
            self.assertEqual(credentials.get('work',settings,path),'secret')
            self.assertEqual(path.with_name('credentials.json').stat().st_mode & 0o777,0o600)
            credentials.delete(settings,path)
            self.assertEqual(credentials.get('work',settings,path),'')
