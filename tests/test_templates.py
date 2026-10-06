import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from jsup import config, fields, templates, ui
from jsup.commands import build_parser
from jsup.completion import candidates, script


class TemplateTests(unittest.TestCase):
    def test_callback_template_renders_legacy_payload_without_hooks(self):
        data=templates.load('callback')
        values=templates.render(data,{'name':'Example','issue':'Login failed','callback':'Tomorrow'})
        self.assertEqual(values['summary'],'Callback: Example — Login failed')
        self.assertIn('Source: jsup intake.',values['description'])
        self.assertEqual(values['components'],['ops-runbook'])

    def test_undeclared_expression_hooks_and_invalid_versions_fail(self):
        for changed in ({'schema_version':2},{'hook':'run shell'},{'summary':'{name.__class__}'},{'summary':'{unknown}'},{'summary':'{name!r}'}):
            with self.subTest(changed=changed),self.assertRaises(ValueError): templates.validate({**templates.load('callback'),**changed})

    def test_required_variables_are_not_prompted_in_script_mode(self):
        args=build_parser().parse_args(['issue','create','--template','callback','--no-input'])
        with patch('builtins.input',side_effect=AssertionError('prompt')),self.assertRaisesRegex(ValueError,'Missing template variables'):
            templates.apply(args)

    def test_explicit_fields_override_incompatible_template_defaults(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(config,'CONFIG_PATH',Path(temp)/'config.json'):
            j=Mock(); j.issue_types.return_value=[{'id':'1','name':'Task'}]
            j.create_fields.return_value=[{'fieldId':'summary','name':'Summary','required':True,'schema':{'type':'string'}},
                {'fieldId':'description','name':'Description','schema':{'type':'string','system':'description'}},
                {'fieldId':'priority','name':'Priority','schema':{'type':'priority'},'allowedValues':[{'id':'1','name':'Normal'}]},
                {'fieldId':'labels','name':'Labels','schema':{'type':'array','items':'string'}},
                {'fieldId':'components','name':'Components','schema':{'type':'array','items':'component'},'allowedValues':[{'id':'2','name':'Other'}]}]
            args=build_parser().parse_args(['issue','create','--template','callback','--var','name=Example','--var','issue=Problem',
                                          '--summary','Explicit','--priority','Normal','--component','Other','--field','labels:=[]','--no-input'])
            fields.create(j,args,{'site':'https://example.invalid','email':'tester','project':'ENG'})
            values=j.create_with_fields.call_args.args[0]
            self.assertEqual(values['summary'],'Explicit'); self.assertEqual(values['components'],[{'id':'2'}])
            self.assertEqual(values['labels'],[]); self.assertEqual(values['priority'],{'id':'1'})

    def test_cross_project_template_rejects_missing_component(self):
        with self.assertRaisesRegex(ValueError,'unavailable'):
            fields.typed({'name':'Components','schema':{'type':'array','items':'component'},'allowedValues':[{'id':'1','name':'Other'}]},'ops-runbook')

    def test_local_template_lists_and_shows_without_network(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(config,'CONFIG_PATH',Path(temp)/'config.json'):
            path=Path(temp)/'templates'; path.mkdir(); (path/'team.json').write_text(json.dumps({'schema_version':1,'name':'team','type':'Bug','summary':'Example'}))
            self.assertEqual(templates.list_templates()['templates'],['callback','team'])
            self.assertEqual(templates.load('team')['type'],'Bug')

    def test_completion_uses_parser_and_local_profiles_only(self):
        self.assertIn('create',candidates(['issue','cr']))
        self.assertIn('--template',candidates(['issue','create','--tem']))
        self.assertIn('edit',candidates(['issue','comment','e']))
        with tempfile.TemporaryDirectory() as temp,patch.object(config,'CONFIG_PATH',Path(temp)/'config.json'):
            config.atomic_json(config.CONFIG_PATH,{'schema_version':2,'profiles':{'work':{'project':'ENG','token':'should-not-be-read'}}})
            self.assertEqual(candidates(['--profile','w']),['work'])
            self.assertEqual(candidates(['--token','']),[])
        for shell in ('bash','zsh','fish'): self.assertIn('--_complete',script(shell,'jira-cli-toolkit'))

    def test_csv_is_parseable_and_flattens_selected_issue_fields(self):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            ui.csv_data({'issues':[{'key':'ENG-1','fields':{'summary':'Comma, quote " and newline\nvalue','status':{'name':'Done'},'assignee':{'displayName':'Tester'}}}]},'key,summary,status,assignee')
        rows=list(csv.DictReader(io.StringIO(output.getvalue())))
        self.assertEqual(rows[0]['summary'],'Comma, quote " and newline\nvalue')
        self.assertEqual(rows[0]['status'],'Done'); self.assertEqual(rows[0]['assignee'],'Tester')
