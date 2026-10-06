import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import call, patch

import requests
from rich.console import Console

from jsup import application, cli, config, ui
from jsup.client import Jira, JiraError


class CLITests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        temp = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.config_path = Path(temp) / "config.json"
        self.config_path.write_text(json.dumps({
            "JIRA_SITE": "https://example.invalid", "JIRA_EMAIL": "tester@example.invalid",
            "JIRA_API_TOKEN": "test-secret", "JIRA_PROJECT": "ENG",
        }))
        self.stack.enter_context(patch.object(config, "CONFIG_PATH", self.config_path))
        self.stack.enter_context(patch.dict(os.environ, {}, clear=True))
        self.out, self.err = io.StringIO(), io.StringIO()
        self.stack.enter_context(contextlib.redirect_stdout(self.out))
        self.stack.enter_context(contextlib.redirect_stderr(self.err))
        self.stack.enter_context(patch.object(ui, "console", Console(file=self.out, color_system=None)))
        self.stack.enter_context(patch.object(ui, "err_console", Console(file=self.err, color_system=None)))
        self.factory = self.stack.enter_context(patch.object(application, "Jira", autospec=Jira))
        self.jira = self.factory.return_value
        self.stack.enter_context(patch("sys.stdin.isatty", return_value=False))

    def invoke(self, argv, legacy=False):
        self.out.seek(0)
        self.out.truncate()
        self.err.seek(0)
        self.err.truncate()
        try:
            (cli.main if legacy else cli.toolkit_main)(argv)
        except SystemExit as error:
            return error.code
        return 0

    def test_help_and_version_do_not_read_configuration_or_contact_jira(self):
        with patch.object(config, "resolve_config", side_effect=AssertionError("unexpected config")):
            for argv in (["--help"], ["help"], ["help", "issue", "create"],
                         ["help", "issue", "comment", "add"], ["help", "issue-show"],
                         ["issue"], ["issue", "comment"], ["--version"]):
                with self.subTest(argv=argv):
                    self.assertEqual(self.invoke(argv), 0)
                    self.assertTrue(self.out.getvalue())
        self.factory.assert_not_called()

    def test_unknown_help_path_is_a_usage_error(self):
        self.assertEqual(self.invoke(["help", "issue", "unknown"]), 2)
        self.factory.assert_not_called()

    def test_new_root_and_context_are_local_and_do_not_expose_credentials(self):
        for argv in ([], ["--json"], ["context", "show", "--json"]):
            with self.subTest(argv=argv):
                self.assertEqual(self.invoke(argv), 0)
                self.assertNotIn("test-secret", self.out.getvalue())
                self.assertNotIn("tester@example.invalid", self.out.getvalue())
                if "--json" in argv:
                    self.assertEqual(json.loads(self.out.getvalue()),
                                     {"site": "https://example.invalid", "project": "ENG"})
        self.factory.assert_not_called()

    def test_config_json_masks_token_and_works_without_authentication(self):
        self.assertEqual(self.invoke(["config", "show", "--json"]), 0)
        data = json.loads(self.out.getvalue())
        self.assertTrue(data["token_configured"])
        self.assertNotIn("test-secret", self.out.getvalue())
        self.factory.assert_not_called()

    def test_root_works_without_configuration(self):
        self.config_path.unlink()
        self.assertEqual(self.invoke(["--json"]), 0)
        self.assertEqual(json.loads(self.out.getvalue()), {"site": None, "project": None})
        self.factory.assert_not_called()

    def test_config_precedence_reaches_client_and_query(self):
        with patch.dict(os.environ, {"JIRA_SITE": "https://env.invalid", "JIRA_PROJECT": "ENV"}):
            self.jira.search.return_value = {"issues": []}
            self.assertEqual(self.invoke(["--site", "https://flag.invalid", "-p", "FLAG",
                                          "--json", "issue", "list"]), 0)
        self.factory.assert_called_once_with("https://flag.invalid", "tester@example.invalid", "test-secret")
        self.jira.search.assert_called_once_with('project = "FLAG" ORDER BY updated DESC', 50)

    def test_general_list_includes_done_unless_open_is_requested(self):
        self.jira.search.return_value = {"issues": [], "nextPageToken": "next"}
        self.assertEqual(self.invoke(["issue", "list", "--json"]), 0)
        self.jira.search.assert_called_once_with('project = "ENG" ORDER BY updated DESC', 50)
        self.assertEqual(json.loads(self.out.getvalue()), {"issues": [], "nextPageToken": "next"})
        self.jira.search.reset_mock()
        self.assertEqual(self.invoke(["issue", "list", "--open", "--json"]), 0)
        self.jira.search.assert_called_once_with('project = "ENG" AND statusCategory != Done ORDER BY updated DESC', 50)

    def test_complete_jql_ignores_configured_project(self):
        self.jira.search.return_value = {"issues": []}
        self.assertEqual(self.invoke(["issue", "list", "--jql", "assignee = currentUser()", "--json"]), 0)
        self.jira.search.assert_called_once_with("assignee = currentUser()", 50)

    def test_ambiguous_jql_filters_are_rejected_without_search(self):
        for extra in (["--open"], ["-p", "OTHER"]):
            with self.subTest(extra=extra):
                self.assertEqual(self.invoke(["issue", "list", "--jql", "priority = High", *extra]), 2)
        self.jira.search.assert_not_called()

    def test_generic_create_has_no_support_metadata(self):
        self.jira.issue_types.return_value = [{"id": "1", "name": "Task"}]
        self.jira.create_fields.return_value = [{"fieldId": "summary", "name": "Summary", "required": True, "schema": {"type": "string"}}]
        self.jira.create_with_fields.return_value = {"key": "ENG-1"}
        self.assertEqual(self.invoke(["issue", "create", "--type", "Task", "-s", "Example", "--json"]), 0)
        self.jira.create_with_fields.assert_called_once_with({"project": {"key": "ENG"}, "issuetype": {"id": "1"}, "summary": "Example"})
        self.jira.issue_create.return_value = {"key": "ENG-1"}
        self.assertEqual(self.invoke(["issue-create", "-s", "Example", "--json"]), 0)
        self.jira.issue_create.assert_called_once_with("ENG", "Example", "", "Task", None, [], [], None)

    def test_legacy_intake_preserves_explicit_callback_workflow(self):
        self.jira.issue_create.return_value = {"key": "ENG-1"}
        self.assertEqual(self.invoke(["intake", "--name", "Example", "--issue", "Login failed",
                                      "--callback", "Tomorrow", "--json", "--no-input"], legacy=True), 0)
        fields = self.jira.issue_create.call_args.args
        self.assertEqual(fields[0:2], ("ENG", "Callback: Example — Login failed"))
        self.assertIn("Requested callback: Tomorrow", fields[2])
        self.assertEqual(fields[3:7], ("Task", "High", ["callback"], ["ops-runbook"]))

    def test_dashboard_queries_only_selected_projects_and_labels_estimates(self):
        self.jira.count_issues.return_value = {"count": 9}
        self.assertEqual(self.invoke(["dashboard", "--json"]), 0)
        self.jira.count_issues.assert_called_once_with('project = "ENG" AND statusCategory != Done')
        row = json.loads(self.out.getvalue())["projects"][0]
        self.assertEqual(row, {"project": "ENG", "count": 9, "approximate": True})
        self.assertEqual(self.invoke(["dashboard"]), 0)
        self.assertIn("approximately 9", self.out.getvalue())

    def test_dashboard_explicit_projects_are_deduplicated(self):
        self.jira.count_issues.return_value = {"count": 0}
        self.assertEqual(self.invoke(["dashboard", "--projects", "HR", "MKT", "HR", "--json"]), 0)
        self.assertEqual(self.jira.count_issues.call_args_list,
                         [call('project = "HR" AND statusCategory != Done'),
                          call('project = "MKT" AND statusCategory != Done')])

    def test_dashboard_without_a_project_has_an_actionable_error(self):
        with patch.dict(os.environ, {"JIRA_PROJECT": ""}):
            saved = json.loads(self.config_path.read_text())
            saved["JIRA_PROJECT"] = ""
            self.config_path.write_text(json.dumps(saved))
            self.assertEqual(self.invoke(["dashboard"]), 2)
        self.jira.count_issues.assert_not_called()
        self.assertIn("--projects", self.err.getvalue())

    def test_legacy_root_retains_dashboard_and_json_contract(self):
        self.jira.count_issues.return_value = {"count": 3}
        self.assertEqual(self.invoke([], legacy=True), 0)
        self.jira.count_issues.assert_called_once_with('project = "ENG" AND statusCategory != Done')
        self.factory.reset_mock()
        self.assertEqual(self.invoke(["--json"], legacy=True), 0)
        self.assertEqual(json.loads(self.out.getvalue()), {"project": "ENG", "hint": "use open/board-list"})
        self.factory.assert_not_called()

    def test_web_views_require_only_a_site_and_never_invent_a_project(self):
        self.config_path.unlink()
        cases = [
            (["issue", "view", "ENG-1", "--web"], "/browse/ENG-1"),
            (["board", "view", "12", "--web"], "/secure/RapidBoard.jspa?rapidView=12"),
            (["browse", "board:12"], "/secure/RapidBoard.jspa?rapidView=12"),
        ]
        with patch("jsup.application.webbrowser.open", return_value=True) as browser:
            for argv, path in cases:
                with self.subTest(argv=argv):
                    self.assertEqual(self.invoke(["--site", "https://example.invalid", *argv, "--json"]), 0)
                    self.assertEqual(json.loads(self.out.getvalue())["url"], "https://example.invalid" + path)
                    browser.assert_called_with("https://example.invalid" + path)
        self.factory.assert_not_called()

    def test_invalid_legacy_board_target_does_not_open_browser(self):
        with patch("jsup.application.webbrowser.open") as browser:
            self.assertEqual(self.invoke(["browse", "board:not-an-id"]), 2)
            browser.assert_not_called()

    def test_board_list_uses_context_while_legacy_list_preserves_all_boards(self):
        self.jira.boards.return_value = {"values": []}
        self.assertEqual(self.invoke(["board", "list", "--json"]), 0)
        self.jira.boards.assert_called_with(project="ENG")
        self.assertEqual(self.invoke(["board-list", "--json"], legacy=True), 0)
        self.jira.boards.assert_called_with(project=None)

    def test_grouped_feature_disable_is_false(self):
        self.jira.board_feature.return_value = {}
        self.assertEqual(self.invoke(["board", "feature", "disable", "12", "--feature", "reports", "--json"]), 0)
        self.jira.board_feature.assert_called_once_with(12, "reports", False)

    def test_legacy_daily_and_planning_commands_preserve_api_arguments(self):
        cases = [
            (["me"], "me", (), {}),
            (["project-list"], "projects", (), {}),
            (["project-show", "OTHER"], "project_get", ("OTHER",), {}),
            (["open", "--jql", "priority = High"], "open_tickets", ("ENG", "priority = High", 50), {}),
            (["issue-show", "ENG-1"], "issue_get", ("ENG-1",), {}),
            (["issue-move", "ENG-1", "--to", "Done"], "move", ("ENG-1", "Done"), {}),
            (["transitions", "ENG-1"], "transitions", ("ENG-1",), {}),
            (["comment-add", "ENG-1", "-m", "Example"], "comment_add", ("ENG-1", "Example"), {}),
            (["comment-list", "ENG-1"], "comments", ("ENG-1",), {}),
            (["board-list", "--jql-project", "OTHER"], "boards", (), {"project": "OTHER"}),
            (["board-create", "--name", "Example"], "board_create", ("Example", "ENG", None, None, "scrum"), {}),
            (["board-issues", "12"], "board_issues", (12, "", 50), {}),
            (["board-feature", "12", "--feature", "reports", "--enable"], "board_feature", (12, "reports", True), {}),
            (["sprint-list", "--board", "12"], "sprints", (12, "active,future"), {}),
            (["sprint-create", "--board", "12", "--name", "Example"], "sprint_create", (12, "Example", ""), {}),
            (["sprint-state", "4", "active"], "sprint_set_state", (4, "active"), {}),
            (["sprint-add", "4", "ENG-1", "ENG-2"], "sprint_add_issues", (4, ["ENG-1", "ENG-2"]), {}),
            (["component-list"], "components", ("ENG",), {}),
            (["component-create", "--name", "Example", "--desc", "Description"],
             "component_create", ("ENG", "Example", "Description"), {}),
        ]
        for argv, method, positional, keyword in cases:
            with self.subTest(argv=argv):
                endpoint = getattr(self.jira, method)
                endpoint.reset_mock()
                endpoint.return_value = {"marker": method}
                self.assertEqual(self.invoke(["--json", *argv], legacy=True), 0)
                endpoint.assert_called_once_with(*positional, **keyword)
                self.assertEqual(json.loads(self.out.getvalue()), {"marker": method})

    def test_interactive_setup_still_saves_legacy_configuration(self):
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=[
            "https://setup.invalid", "new@example.invalid", "HR",
        ]), patch("getpass.getpass", return_value="new-test-secret"):
            self.assertEqual(self.invoke(["config", "init"], legacy=True), 0)
        saved = json.loads(self.config_path.read_text())
        self.assertEqual(saved, {"JIRA_SITE": "https://setup.invalid", "JIRA_EMAIL": "new@example.invalid",
                                 "JIRA_API_TOKEN": "new-test-secret", "JIRA_PROJECT": "HR"})
        if os.name != "nt":  # Windows permissions are enforced through ACLs.
            self.assertEqual(self.config_path.stat().st_mode & 0o777, 0o600)
        self.factory.assert_not_called()

    def test_scripted_commands_never_prompt_for_missing_input(self):
        with patch("builtins.input", side_effect=AssertionError("unexpected prompt")):
            for argv in (["issue", "transition", "ENG-1"], ["issue", "delete", "ENG-1"],
                         ["intake"], ["config", "init"]):
                with self.subTest(argv=argv):
                    self.assertEqual(self.invoke([*argv, "--no-input"]), 2)
                    self.assertTrue(self.err.getvalue())
        self.factory.assert_not_called()

    def test_json_does_not_bypass_delete_confirmation(self):
        self.assertEqual(self.invoke(["issue", "delete", "ENG-1", "--json"]), 2)
        self.jira.issue_delete.assert_not_called()

    def test_confirmed_delete_uses_api_and_preserves_json(self):
        self.jira.issue_delete.return_value = {}
        self.assertEqual(self.invoke(["issue", "delete", "ENG-1", "--yes", "--json"]), 0)
        self.jira.issue_delete.assert_called_once_with("ENG-1")
        self.assertEqual(json.loads(self.out.getvalue()), {})
        self.jira.close.assert_called_once()

    def test_interactive_transition_errors_are_caught_and_session_closed(self):
        with patch("sys.stdin.isatty", return_value=True), patch.object(ui, "pick", return_value=0):
            self.jira.transitions.return_value = {"transitions": [{"id": "2", "name": "Done"}]}
            self.jira.transition_fields.return_value = {"transitions": [{"id": "2", "name": "Done", "fields": {}}]}
            self.jira.transition_with_fields.side_effect = JiraError("POST", "/transition", 403, "Forbidden")
            self.assertEqual(self.invoke(["issue", "transition", "ENG-1"]), 1)
        self.assertIn("permission denied", self.err.getvalue())
        self.jira.close.assert_called_once()

    def test_auth_failure_is_not_a_successful_dashboard(self):
        self.jira.count_issues.side_effect = JiraError("POST", "/count", 401, "Unauthorized")
        self.assertEqual(self.invoke(["dashboard", "--json"]), 1)
        self.assertEqual(json.loads(self.out.getvalue())["error"]["status"], 401)
        self.assertIn("authentication failed", self.out.getvalue())

    def test_network_errors_do_not_print_tracebacks_or_credentials(self):
        self.jira.me.side_effect = requests.ConnectionError("test-secret")
        self.assertEqual(self.invoke(["user", "me", "--json"]), 1)
        self.assertEqual(json.loads(self.out.getvalue())["error"]["code"], "network_error")
        self.assertNotIn("test-secret", self.out.getvalue() + self.err.getvalue())
        self.jira.close.assert_called_once()

    def test_all_pagination_reaches_client(self):
        self.jira.search.return_value = {"issues": [], "isLast": True}
        self.assertEqual(self.invoke(["issue", "list", "--all", "--json"]), 0)
        self.jira.search.assert_called_once_with('project = "ENG" ORDER BY updated DESC', 50, all_results=True)

    def test_json_errors_redact_server_echoed_credentials(self):
        self.jira.me.side_effect = JiraError("GET", "/myself", 401, "test-secret invalid")
        self.assertEqual(self.invoke(["user", "me", "--json"]), 1)
        error = json.loads(self.out.getvalue())["error"]
        self.assertEqual(error["code"], "jira_error")
        self.assertNotIn("test-secret", error["message"])
        self.assertIn("[redacted]", error["message"])

    def test_legacy_json_errors_keep_stderr_contract(self):
        self.jira.me.side_effect = JiraError("GET", "/myself", 401, "test-secret invalid")
        self.assertEqual(self.invoke(["me", "--json"], legacy=True), 1)
        self.assertEqual(self.out.getvalue(), "")
        self.assertNotIn("test-secret", self.err.getvalue())

    def test_new_destructive_commands_require_explicit_confirmation(self):
        for argv in (["issue", "unlink", "1"], ["issue", "comment", "delete", "ENG-1", "1"], ["issue", "attachment", "delete", "1"]):
            with self.subTest(argv=argv):
                self.assertEqual(self.invoke([*argv, "--json", "--no-input"]), 2)
                self.assertIn("--yes", json.loads(self.out.getvalue())["error"]["message"])
        self.factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
