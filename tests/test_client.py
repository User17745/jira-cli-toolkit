import unittest
from unittest.mock import Mock, patch

from jsup.client import Jira


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.jira = Jira("https://example.invalid", "tester", "secret")
        self.addCleanup(self.jira.close)

    def test_requests_have_bounded_timeouts(self):
        response = Mock(status_code=200, text="{}")
        response.json.return_value = {}
        with patch.object(self.jira.s, "request", return_value=response) as request:
            self.jira.me()
        self.assertEqual(request.call_args.kwargs["timeout"], (10, 30))

    def test_generated_project_jql_cannot_inject_another_query(self):
        with patch.object(self.jira, "search", return_value={}) as search:
            self.jira.open_tickets('ENG" OR project = "OTHER')
        self.assertEqual(search.call_args.args[0],
                         'project = "ENG\\" OR project = \\"OTHER" AND statusCategory != Done ORDER BY updated DESC')

    def test_count_and_board_view_use_supported_endpoints(self):
        with patch.object(self.jira, "_req", return_value={}) as request:
            self.jira.count_issues('project = "ENG"')
            request.assert_called_with("POST", "/rest/api/3/search/approximate-count", json={"jql": 'project = "ENG"'})
            self.jira.board_get(12)
            request.assert_called_with("GET", "/rest/agile/1.0/board/12")


if __name__ == "__main__":
    unittest.main()
