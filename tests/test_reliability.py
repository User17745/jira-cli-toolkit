import unittest
from unittest.mock import Mock, patch

import requests
from jsup.client import Jira, JiraError, UncertainOutcome


def response(status=200, data=None, headers=None):
    r = Mock(status_code=status, text='response', headers=headers or {})
    r.json.return_value = data if data is not None else {}
    return r


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.jira = Jira('https://example.invalid', 'user', 'secret')
        self.addCleanup(self.jira.close)

    def test_safe_reads_retry_rate_limit_and_honor_delay(self):
        with patch.object(self.jira.s, 'request', side_effect=[response(429, headers={'Retry-After': '2'}), response(data={'accountId':'1'})]) as req, patch('jsup.client.time.sleep') as sleep:
            self.assertEqual(self.jira.me(), {'accountId':'1'})
        self.assertEqual(req.call_count, 2)
        sleep.assert_called_once_with(2)

    def test_long_retry_after_is_not_retried_early(self):
        with patch.object(self.jira.s, 'request', return_value=response(429, headers={'Retry-After':'300'})) as req, patch('jsup.client.time.sleep') as sleep:
            with self.assertRaises(JiraError): self.jira.me()
        self.assertEqual(req.call_count, 1)
        sleep.assert_not_called()

    def test_auth_and_permission_failures_never_retry(self):
        for status in (401, 403):
            with self.subTest(status=status), patch.object(self.jira.s, 'request', return_value=response(status)) as req:
                with self.assertRaises(JiraError): self.jira.me()
                self.assertEqual(req.call_count, 1)

    def test_read_timeout_retries_are_bounded(self):
        with patch.object(self.jira.s, 'request', side_effect=requests.ReadTimeout) as req, patch('jsup.client.time.sleep'):
            with self.assertRaises(requests.ReadTimeout): self.jira.me()
            self.assertEqual(req.call_count, 3)

    def test_mutation_timeout_is_uncertain_and_never_replayed(self):
        with patch.object(self.jira.s, 'request', side_effect=requests.ReadTimeout) as req:
            with self.assertRaises(UncertainOutcome): self.jira.issue_create('ENG','test')
            self.assertEqual(req.call_count, 1)

    def test_server_error_does_not_replay_mutation(self):
        with patch.object(self.jira.s, 'request', return_value=response(503)) as req:
            with self.assertRaises(JiraError): self.jira.issue_create('ENG','test')
            self.assertEqual(req.call_count, 1)

    def test_malformed_success_is_reported(self):
        r=response(); r.json.side_effect=ValueError('invalid')
        with patch.object(self.jira.s, 'request', return_value=r):
            with self.assertRaisesRegex(JiraError, 'malformed JSON'): self.jira.me()

    def test_scalar_success_is_rejected(self):
        with patch.object(self.jira.s, 'request', return_value=response(data='unexpected')):
            with self.assertRaisesRegex(JiraError, 'unexpected response'): self.jira.me()

    def test_search_collects_cursor_pages_without_total(self):
        with patch.object(self.jira, '_req', side_effect=[{'issues':[{'key':'E-1'}],'nextPageToken':'next','isLast':False},{'issues':[{'key':'E-2'}],'isLast':True}]) as req:
            data=self.jira.search('x'*3000, all_results=True)
        self.assertEqual(data['fetched'],2); self.assertNotIn('total',data)
        self.assertEqual(req.call_args.kwargs['json']['nextPageToken'],'next')
        self.assertEqual(req.call_args.args[0],'POST')
        self.assertTrue(req.call_args.kwargs['retry_safe'])

    def test_search_total_limit_is_not_page_size(self):
        with patch.object(self.jira, '_req', side_effect=[{'issues':[{'key':str(i)} for i in range(100)],'nextPageToken':'next','isLast':False},{'issues':[{'key':'last'}],'isLast':True}]) as req:
            data=self.jira.search('project=E',101)
        self.assertEqual(len(data['issues']),101)
        self.assertEqual(req.call_args.kwargs['json']['maxResults'],1)

    def test_repeated_cursor_and_missing_cursor_fail(self):
        for pages in ([{'issues':[{}],'isLast':False}], [{'issues':[{}],'nextPageToken':'same'},{'issues':[{}],'nextPageToken':'same'}]):
            with self.subTest(pages=pages), patch.object(self.jira, '_req', side_effect=pages):
                with self.assertRaises(JiraError): self.jira.search('query',all_results=True)

    def test_offset_server_caps_and_empty_page_terminate(self):
        with patch.object(self.jira, '_req', side_effect=[{'values':[{'id':1}],'total':3},{'values':[{'id':2}],'total':3},{'values':[],'total':3}]) as req:
            data=self.jira.boards(all_results=True)
        self.assertEqual(data['fetched'],2)
        self.assertEqual(req.call_args.kwargs['params']['startAt'],2)
        self.assertFalse(data['isLast'])

    def test_offset_limits_and_endpoint_item_keys(self):
        for method, args, key in [('projects',[], 'values'),('comments',['E-1'],'comments'),('sprints',[1],'values'),('board_issues',[1],'issues')]:
            with self.subTest(method=method), patch.object(self.jira, '_req', return_value={key:[{'id':1},{'id':2}], 'total':10}):
                kwargs={'max_results':2} if method=='board_issues' else {'limit':2}
                data=getattr(self.jira,method)(*args,**kwargs)
                items=data if isinstance(data,list) else data[key]
                self.assertEqual(len(items),2)
