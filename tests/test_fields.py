import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from jsup import config, fields
from jsup.client import JiraError


def args(**kw):
    return SimpleNamespace(**dict(dict(type='Bug',summary='Example',priority=None,desc=None,desc_file=None,editor=False,
         assignee=None,label=[],component=[],parent=None,field=[],fields_file=None,refresh=False,json=True,no_input=True),**kw))


class FieldTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.addCleanup(patch.stopall)
        patch.object(config,'CONFIG_PATH',Path(self.temp.name)/'config.json').start()
        self.cfg={'site':'https://example.invalid','email':'tester','profile':'work','project':'ENG'}
        self.j=Mock()
        self.j.issue_types.return_value=[{'id':'2','name':'Bug'},{'id':'1','name':'Task'}]
        self.meta=[{'fieldId':'summary','name':'Summary','required':True,'schema':{'type':'string'}},
                   {'fieldId':'customfield_1','name':'Severity','required':True,'schema':{'type':'option'},'allowedValues':[{'id':'10','value':'Severe'},{'id':'11','value':'Minor'}]},
                   {'fieldId':'description','name':'Description','schema':{'type':'string','system':'description'}},
                   {'fieldId':'parent','name':'Parent','schema':{'type':'issuelink'}}]
        self.j.create_fields.return_value=self.meta
        self.j.create_with_fields.return_value={'key':'ENG-1'}
        self.j.transition_with_fields.return_value={'moved':'ENG-1','transition_id':'99'}

    def test_required_custom_field_uses_project_metadata_and_type_ids(self):
        fields.create(self.j,args(field=['Severity=Severe'],desc='Details',parent='ENG-2'),self.cfg)
        payload=self.j.create_with_fields.call_args.args[0]
        self.assertEqual(payload['issuetype'],{'id':'2'})
        self.assertEqual(payload['customfield_1'],{'id':'10'})
        self.assertEqual(payload['parent'],{'key':'ENG-2'})
        self.assertEqual(payload['description']['type'],'doc')
        self.assertNotIn('labels',payload)

    def test_script_missing_required_field_fails_before_mutation(self):
        with self.assertRaisesRegex(ValueError,'Severity'): fields.create(self.j,args(),self.cfg)
        self.j.create_with_fields.assert_not_called()

    def test_unknown_issue_type_does_not_assume_task_exists(self):
        with self.assertRaisesRegex(ValueError,'unavailable'): fields.create(self.j,args(type='Story'),self.cfg)
        self.j.create_fields.assert_not_called()

    def test_omitted_type_requires_explicit_selection_in_scripts(self):
        with self.assertRaisesRegex(ValueError,'--type'): fields.create(self.j,args(type=None),self.cfg)

    def test_duplicate_names_have_id_escape_hatch(self):
        choices=[{'id':'1','name':'Bug'},{'id':'2','name':'Bug'}]
        with self.assertRaisesRegex(ValueError,'ambiguous'): fields.choose(choices,'Bug','type')
        self.assertEqual(fields.choose(choices,'id:2','type')['id'],'2')
        meta={'a':{'name':'Duplicate'},'b':{'name':'Duplicate'}}
        with self.assertRaisesRegex(ValueError,'ambiguous'): fields.field_key(meta,'Duplicate')
        self.assertEqual(fields.field_key(meta,'a'),'a')

    def test_structured_complex_input_is_preserved(self):
        payload={'id':'10','child':{'id':'99'}}
        data=fields.supplied(args(field=['customfield_1:={"id":"10","child":{"id":"99"}}']),fields.normalize(self.meta))
        self.assertEqual(data['customfield_1'],payload)

    def test_typed_numbers_dates_arrays_users_and_rich_text(self):
        cases=[({'type':'number'},'3.5',3.5),({'type':'date'},'2026-10-06','2026-10-06'),
               ({'type':'array','items':'string'},'one,two',['one','two']),({'type':'user'},'id:abc',{'accountId':'abc'})]
        for schema,raw,expected in cases:
            self.assertEqual(fields.typed({'name':'Field','schema':schema},raw),expected)
        rich=fields.typed({'schema':{'type':'string','custom':'example:textarea'}},'Text')
        self.assertEqual(rich['type'],'doc')
        for schema,raw in [({'type':'date'},'yesterday'),({'type':'number'},'many'),({'type':'vendor'},'custom')]:
            with self.assertRaises(ValueError): fields.typed({'name':'Field','schema':schema},raw)

    def test_cache_is_scoped_and_refreshable(self):
        fields.create(self.j,args(field=['Severity=Minor']),self.cfg)
        fields.create(self.j,args(field=['Severity=Minor']),self.cfg)
        self.assertEqual(self.j.issue_types.call_count,1)
        fields.create(self.j,args(field=['Severity=Minor'],refresh=True),self.cfg)
        self.assertEqual(self.j.issue_types.call_count,2)
        fields.create(self.j,args(field=['Severity=Minor']),{**self.cfg,'email':'other'})
        self.assertEqual(self.j.issue_types.call_count,3)

    def test_validation_failure_invalidates_cache(self):
        self.j.create_with_fields.side_effect=JiraError('POST','/issue',400,'invalid option')
        with self.assertRaises(JiraError): fields.create(self.j,args(field=['Severity=Minor']),self.cfg)
        self.assertEqual(list((config.CONFIG_PATH.parent/'cache').glob('*.json')),[])

    def test_transition_required_fields_are_discovered(self):
        meta={'resolution':{'name':'Resolution','required':True,'schema':{'type':'resolution'},'allowedValues':[{'id':'1','name':'Done'}]}}
        self.j.transition_fields.return_value={'transitions':[{'id':'99','name':'Close','fields':meta}]}
        a=args(field=['resolution=Done']); a.key='ENG-1'; a.to='Close'
        result=fields.transition(self.j,a,self.cfg)
        self.j.transition_with_fields.assert_called_once_with('ENG-1','99',{'resolution':{'id':'1'}})
        self.assertEqual(result['to'],'Close')

    def test_guided_required_field_selection_respects_no_input(self):
        a=args(json=False,no_input=False)
        with patch('sys.stdin.isatty',return_value=True),patch.object(fields.ui,'pick',return_value=1):
            fields.create(self.j,a,self.cfg)
        self.assertEqual(self.j.create_with_fields.call_args.args[0]['customfield_1'],{'id':'11'})
        self.j.reset_mock()
        with patch('builtins.input',side_effect=AssertionError('prompt')):
            with self.assertRaises(ValueError): fields.create(self.j,args(),self.cfg)

    def test_project_and_type_cannot_be_overridden_by_custom_values(self):
        self.j.create_fields.return_value=self.meta+[{'fieldId':'project','name':'Project','schema':{'type':'string'}}]
        with self.assertRaisesRegex(ValueError,'--project'): fields.create(self.j,args(field=['project=OTHER']),self.cfg)
