from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from jsup.commands import build_parser
from jsup import maintenance
from jsup.client import Jira


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.j=Mock()
        self.cfg={'site':'https://example.invalid','email':'tester','project':'ENG'}
        self.parser=build_parser('jira-cli-toolkit')
        self.j.edit_fields.return_value={
            'summary':{'name':'Summary','schema':{'type':'string'},'required':True,'operations':['set']},
            'labels':{'name':'Labels','schema':{'type':'array','items':'string'},'operations':['set','add','remove']},
            'priority':{'name':'Priority','schema':{'type':'priority'},'allowedValues':[{'id':'1','name':'High'}]},
            'parent':{'name':'Parent','schema':{'type':'issuelink'}}}

    def run_command(self,argv): return maintenance.handle(self.j,self.parser.parse_args(argv),self.cfg)

    def test_edit_resolves_metadata_and_incremental_collection_operations(self):
        self.run_command(['issue','edit','ENG-1','--summary','Updated','--priority','High','--parent','ENG-2','--add-label','new','--remove-label','old'])
        self.j.edit_issue.assert_called_once_with('ENG-1',{'summary':'Updated','priority':{'id':'1'},'parent':{'key':'ENG-2'}},
                                                {'labels':[{'add':'new'},{'remove':'old'}]})

    def test_conflicting_replacement_unknown_fields_and_required_clear_fail(self):
        for flags in (['--label','a','--add-label','b'],['--field','unknown=value'],['--field','summary:=null'],[]):
            with self.subTest(flags=flags), self.assertRaises(ValueError): self.run_command(['issue','edit','ENG-1',*flags])
        self.j.edit_issue.assert_not_called()

    def test_unsupported_collection_operation_is_rejected(self):
        self.j.edit_fields.return_value['labels']['operations']=['set']
        with self.assertRaisesRegex(ValueError,'does not allow'): self.run_command(['issue','edit','ENG-1','--remove-label','old'])

    def test_assignment_current_user_unassignment_and_ambiguous_names(self):
        self.j.me.return_value={'accountId':'current'}
        self.run_command(['issue','assign','ENG-1','--user','me'])
        self.j.assign.assert_called_with('ENG-1','current')
        self.run_command(['issue','unassign','ENG-1']); self.j.assign.assert_called_with('ENG-1',None)
        self.j.assignable_users.return_value=[{'accountId':'1','displayName':'Alex'},{'accountId':'2','displayName':'Alex'}]
        with self.assertRaisesRegex(ValueError,'ambiguous'): self.run_command(['issue','assign','ENG-1','--user','Alex'])
        self.run_command(['issue','assign','ENG-1','--user','id:2']); self.j.assign.assert_called_with('ENG-1','2')

    def test_link_direction_and_type_are_explicit(self):
        self.j.link_types.return_value=[{'id':'1','name':'Blocks'}]
        self.run_command(['issue','link','ENG-1','ENG-2','--type','Blocks','--direction','outward'])
        self.j.link.assert_called_with('ENG-2','ENG-1','1')
        self.run_command(['issue','link','ENG-1','ENG-2','--type','id:1','--direction','inward'])
        self.j.link.assert_called_with('ENG-1','ENG-2','1')

    def test_comment_file_edit_delete_and_missing_body(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'comment.txt'; path.write_text('Evidence')
            self.run_command(['issue','comment','edit','ENG-1','10','--message-file',str(path)])
        self.j.comment_edit.assert_called_once_with('ENG-1',10,'Evidence')
        self.run_command(['issue','comment','delete','ENG-1','10','--yes'])
        self.j.comment_delete.assert_called_once_with('ENG-1',10)
        with self.assertRaises(ValueError): self.run_command(['issue','comment','add','ENG-1','--no-input'])

    def test_list_filters_are_quoted_and_full_jql_cannot_be_mixed(self):
        a=self.parser.parse_args(['issue','list','--assignee','me','--status','In progress','--label','a" OR project=OTHER','--type','Bug','--order','asc','--fields','summary,status','--all'])
        maintenance.issue_list(self.j,a,self.cfg)
        query=self.j.search.call_args.args[0]
        self.assertIn('currentUser()',query); self.assertIn('status IN ("In progress")',query)
        self.assertIn('a\\" OR project=OTHER',query)
        self.assertTrue(query.endswith('ORDER BY updated ASC'))
        self.assertEqual(self.j.search.call_args.kwargs,{'all_results':True,'fields':'summary,status'})
        with self.assertRaises(ValueError): maintenance.issue_list(self.j,self.parser.parse_args(['issue','list','--jql','x','--status','Done']),self.cfg)

    def test_board_search_does_not_require_or_guess_a_project(self):
        a=self.parser.parse_args(['issue','list','--board','12','--open'])
        maintenance.issue_list(self.j,a,self.cfg)
        self.j.board_issues.assert_called_once_with(12,'statusCategory != Done ORDER BY updated DESC',50)


class AttachmentTests(unittest.TestCase):
    def setUp(self):
        self.j=Jira('https://example.invalid','tester','secret'); self.addCleanup(self.j.close)

    def test_upload_is_multipart_and_closes_files(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'proof.txt'; path.write_text('proof')
            with patch.object(self.j,'_req',side_effect=[{'enabled':True,'uploadLimit':100},[{'id':'1'}]]) as req:
                self.assertEqual(self.j.attachment_upload('ENG-1',[path]),[{'id':'1'}])
            kw=req.call_args.kwargs
            self.assertEqual(kw['headers']['X-Atlassian-Token'],'no-check')
            self.assertIsNone(kw['headers']['Content-Type'])
            self.assertTrue(kw['files'][0][1][1].closed)

    def test_disabled_or_oversized_upload_does_not_write(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'proof'; path.write_bytes(b'123')
            for settings in ({'enabled':False},{'enabled':True,'uploadLimit':1}):
                with patch.object(self.j,'_req',return_value=settings) as req, self.assertRaises(ValueError): self.j.attachment_upload('ENG-1',[path])
                self.assertEqual(req.call_count,1)

    def test_download_sanitizes_name_and_prevents_overwrite(self):
        response=Mock(status_code=200); response.iter_content.return_value=[b'proof']
        with tempfile.TemporaryDirectory() as temp, patch.object(self.j,'attachment_info',return_value={'filename':'..\\..\\proof.txt','size':5}), patch.object(self.j.s,'get',return_value=response):
            result=self.j.attachment_download(1,temp)
            path=Path(temp)/'proof.txt'; self.assertEqual(path.read_bytes(),b'proof')
            self.assertEqual(result['bytes'],5)
            with self.assertRaises(ValueError): self.j.attachment_download(1,temp)

    def test_interrupted_download_removes_partial_file(self):
        response=Mock(status_code=200); response.iter_content.return_value=[b'partial']
        with tempfile.TemporaryDirectory() as temp, patch.object(self.j,'attachment_info',return_value={'filename':'proof.txt','size':20}), patch.object(self.j.s,'get',return_value=response):
            with self.assertRaisesRegex(ValueError,'interrupted'): self.j.attachment_download(1,temp)
            self.assertEqual(list(Path(temp).iterdir()),[])
            response.close.assert_called_once()
