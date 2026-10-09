import io
import json
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from rich.console import Console

from jsup import ui

from jsup.cli import jira_main

DESKS = [{"id": "4", "projectKey": "TS", "projectName": "Tech Support"},
         {"id": "8", "projectKey": "VM", "projectName": "Migration"},
         {"id": "9", "projectKey": "VM2", "projectName": "migration"}]
QUEUES = [{"id": "10", "name": "Open", "issueCount": 3}, {"id": "11", "name": "Waiting", "issueCount": 0}]
CFG = dict(site="https://example.atlassian.net", email="a@example.com", token="secret", project="", profile="work", source="keyring")


def page(values, start=0, last=True):
    return {"start": start, "limit": 50, "size": len(values), "isLastPage": last, "values": values}


class Fake:
    """Routes Jira._req calls by method and path, recording each one."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, method, path, **kw):
        self.calls.append((method, path, kw))
        reply = self.routes[(method, path)]
        return reply(kw) if callable(reply) else reply


class DeskCommandTests(unittest.TestCase):
    def setUp(self):
        patcher = patch("jsup.config.resolve_config", return_value=dict(CFG))
        patcher.start()
        self.addCleanup(patcher.stop)

    def call(self, *argv, routes):
        fake = Fake(routes)
        out, err = io.StringIO(), io.StringIO()
        with patch("jsup.client.Jira._req", side_effect=fake), patch("sys.stdout", out), redirect_stderr(err), \
                patch.object(ui, "console", Console(file=out, color_system=None, width=200)), \
                patch.object(ui, "err_console", Console(file=err, color_system=None, width=200)):
            try:
                jira_main(list(argv))
                code = 0
            except SystemExit as exit:
                code = exit.code
        return code, out.getvalue(), err.getvalue(), fake.calls

    def test_desk_list_pages_through_start_and_limit(self):
        routes = {("GET", "/rest/servicedeskapi/servicedesk"): lambda kw: page(DESKS[:2], 0, False) if kw["params"]["start"] == 0 else page(DESKS[2:], 2)}
        code, out, _, calls = self.call("desk", "list", "--all", "--json", routes=routes)
        data = json.loads(out)
        self.assertEqual((code, data["fetched"], data["isLastPage"]), (0, 3, True))
        self.assertEqual([c[2]["params"]["start"] for c in calls], [0, 2])

    def test_desk_list_csv_uses_flat_columns(self):
        routes = {("GET", "/rest/servicedeskapi/servicedesk"): page(DESKS[:1])}
        _, out, _, _ = self.call("desk", "list", "--csv", routes=routes)
        self.assertEqual(out.strip().splitlines(), ["id,key,name", "4,TS,Tech Support"])

    def test_desks_resolve_by_id_key_or_unique_name(self):
        routes = {("GET", "/rest/servicedeskapi/servicedesk"): page(DESKS),
                  ("GET", "/rest/servicedeskapi/servicedesk/4/queue"): page(QUEUES)}
        for value in ("4", "TS", "tech support"):
            code, out, _, calls = self.call("desk", "queues", value, "--json", routes=routes)
            self.assertEqual(code, 0, value)
            self.assertEqual(calls[-1][2]["params"]["includeCount"], "true")
        code, _, err, _ = self.call("desk", "queues", "Migration", routes=routes)
        self.assertEqual(code, 2)
        self.assertIn("matches more than one", err)
        self.assertIn("VM / Migration [id:8]", err)

    def test_queue_issues_resolve_the_queue_by_name(self):
        issue = {"key": "TS-1", "fields": {"summary": "Printer", "status": {"name": "Open"}, "assignee": None, "updated": "2026-10-09T10:00"}}
        routes = {("GET", "/rest/servicedeskapi/servicedesk"): page(DESKS),
                  ("GET", "/rest/servicedeskapi/servicedesk/4/queue"): page(QUEUES),
                  ("GET", "/rest/servicedeskapi/servicedesk/4/queue/11/issue"): page([issue])}
        code, out, _, _ = self.call("desk", "queue", "TS", "waiting", "--csv", routes=routes)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip().splitlines()[1], "TS-1,Open,Printer,-,2026-10-09")
        code, out, _, _ = self.call("desk", "queue", "TS", "Waiting", "--json", routes=routes)
        self.assertEqual((json.loads(out)["queueId"], json.loads(out)["queueName"]), ("11", "Waiting"))

    def test_request_list_filters_status_and_desk(self):
        routes = {("GET", "/rest/servicedeskapi/servicedesk"): page(DESKS),
                  ("GET", "/rest/servicedeskapi/request"): page([])}
        _, _, _, calls = self.call("request", "list", "--json", routes=routes)
        self.assertEqual(calls[-1][2]["params"]["requestStatus"], "OPEN_REQUESTS")
        self.assertNotIn("serviceDeskId", calls[-1][2]["params"])
        _, _, _, calls = self.call("request", "list", "--status", "closed", "--desk", "TS", "--json", routes=routes)
        self.assertEqual((calls[-1][2]["params"]["requestStatus"], calls[-1][2]["params"]["serviceDeskId"]), ("CLOSED_REQUESTS", "4"))

    def test_request_view_expands_participants_and_slas(self):
        request = {"issueKey": "TS-1", "summary": "Printer", "currentStatus": {"status": "Open"}, "serviceDeskId": "4",
                   "reporter": {"displayName": "Sam"}, "participants": {"values": [{"displayName": "Noor"}]},
                   "sla": {"values": [{"name": "Time to first response", "ongoingCycle": {"breached": True}}]},
                   "requestFieldValues": [{"label": "Description", "value": "It jams."}]}
        routes = {("GET", "/rest/servicedeskapi/request/TS-1"): request}
        code, out, _, calls = self.call("request", "view", "TS-1", routes=routes)
        self.assertEqual(code, 0)
        self.assertEqual(calls[0][2]["params"]["expand"], "participant,status,sla")
        for text in ("TS-1", "participants=Noor", "Time to first response: breached", "It jams."):
            self.assertIn(text, out)

    def test_comments_are_customer_visible_unless_internal(self):
        routes = {("POST", "/rest/servicedeskapi/request/TS-1/comment"): lambda kw: {"id": "77", "public": kw["json"]["public"]}}
        code, out, _, calls = self.call("request", "comment", "TS-1", "-m", "On it", routes=routes)
        self.assertEqual((code, calls[0][2]["json"]), (0, {"body": "On it", "public": True}))
        self.assertIn("customer-visible comment to TS-1", out)
        _, out, _, calls = self.call("request", "comment", "TS-1", "-m", "Check logs", "--internal", routes=routes)
        self.assertFalse(calls[0][2]["json"]["public"])
        self.assertIn("internal comment", out)

    def test_transition_by_name_with_comment_and_listing_when_missing(self):
        transitions = page([{"id": "761", "name": "Resolve this issue"}, {"id": "801", "name": "Escalate"}])
        routes = {("GET", "/rest/servicedeskapi/request/TS-1/transition"): transitions,
                  ("POST", "/rest/servicedeskapi/request/TS-1/transition"): {}}
        code, out, _, calls = self.call("request", "transition", "TS-1", "--to", "escalate", "-m", "Needs ops", routes=routes)
        self.assertEqual(code, 0)
        self.assertEqual(calls[-1][2]["json"], {"id": "801", "additionalComment": {"body": "Needs ops"}})
        self.assertIn("Moved TS-1 → Escalate", out)
        code, _, err, calls = self.call("request", "transition", "TS-1", routes=routes)
        self.assertEqual(code, 2)
        self.assertIn("Resolve this issue [id:761]", err)
        self.assertFalse(any(c[0] == "POST" for c in calls))

    def test_pagination_limit_is_an_error_not_a_partial_result(self):
        routes = {("GET", "/rest/servicedeskapi/servicedesk"): lambda kw: page([{"id": str(kw["params"]["start"])}], kw["params"]["start"], False)}
        code, out, err, calls = self.call("desk", "list", "--all", routes=routes)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("exceeded 1,000 pages", err)
        self.assertEqual(len(calls), 1000)

    def test_request_text_is_shown_literally_not_as_markup(self):
        request = {"issueKey": "TS-1", "summary": "Broken [/] tag [link=https://evil.example]click[/link]",
                   "currentStatus": {"status": "Open"}, "requestFieldValues": [{"label": "Body", "value": "[bold]x[/bold] [/]"}]}
        code, out, err, _ = self.call("request", "view", "TS-1", routes={("GET", "/rest/servicedeskapi/request/TS-1"): request})
        self.assertEqual(code, 0, err)
        self.assertIn("[link=https://evil.example]click[/link]", out)
        self.assertIn("[bold]x[/bold] [/]", out)

    def test_empty_transitions_say_so(self):
        routes = {("GET", "/rest/servicedeskapi/request/TS-1/transition"): page([])}
        _, out, _, _ = self.call("request", "transitions", "TS-1", routes=routes)
        self.assertIn("No transitions are available", out)

    def test_request_keys_are_url_encoded(self):
        routes = {("GET", "/rest/servicedeskapi/request/TS-1%2F..%2Fx"): {"issueKey": "x"}}
        code, _, _, calls = self.call("request", "view", "TS-1/../x", "--json", routes=routes)
        self.assertEqual((code, calls[0][1]), (0, "/rest/servicedeskapi/request/TS-1%2F..%2Fx"))


if __name__ == "__main__":
    unittest.main()
