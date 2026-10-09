import base64
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

import requests

from jsup.api import secret_values
from jsup.cli import jira_main

SITE = "https://example.atlassian.net"
EMAIL = "agent@example.com"
TOKEN = "ATATT3xFfGF0-secret-token"
BASIC = base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
CFG = dict(site=SITE, email=EMAIL, token=TOKEN, project="", profile="work", source="keyring")


def response(status=200, body=b"", headers=None, url=SITE + "/rest/api/3/myself"):
    r = requests.Response()
    r.status_code = status
    r.reason = {200: "OK", 204: "No Content", 302: "Found", 404: "Not Found", 503: "Service Unavailable"}.get(status, "")
    r.raw = io.BytesIO(body)
    r.headers.update(headers or {})
    r.request = requests.Request("GET", url).prepare()
    r.encoding = "utf-8"
    return r


class Pipe(io.TextIOWrapper):
    def __init__(self, tty=False):
        super().__init__(io.BytesIO(), encoding="utf-8")
        self.tty = tty

    def isatty(self):
        return self.tty

    def value(self):
        self.flush()
        return self.buffer.getvalue()


class ApiTestBase(unittest.TestCase):
    def setUp(self):
        self.cfg = dict(CFG)
        patcher = patch("jsup.config.resolve_config", side_effect=lambda *a, **k: dict(self.cfg))
        patcher.start()
        self.addCleanup(patcher.stop)
        sleep = patch("jsup.client.time.sleep")
        sleep.start()
        self.addCleanup(sleep.stop)

    def call(self, *argv, replies=(), tty=False, stdin=b""):
        replies = list(replies)
        stdout, stderr = Pipe(tty), io.StringIO()
        with patch("requests.Session.request", side_effect=replies) as request, \
                patch("sys.stdout", stdout), redirect_stderr(stderr), \
                patch("sys.stdin", io.TextIOWrapper(io.BytesIO(stdin))):
            try:
                jira_main(["api", *argv])
                code = 0
            except SystemExit as exit:
                code = exit.code
        return code, stdout.value(), stderr.getvalue(), request

    def error(self, stderr):
        return json.loads(stderr)["error"]


class ApiCommandTests(ApiTestBase):
    # Requests and inputs

    def test_unwrapped_endpoint_is_called_with_saved_identity_and_no_token_in_arguments(self):
        code, out, _, request = self.call("/rest/api/3/serverInfo", replies=[response(body=b'{"version":"1001.0"}')])
        self.assertEqual(code, 0)
        self.assertEqual(out, b'{"version":"1001.0"}')
        method, url = request.call_args.args
        self.assertEqual((method, url), ("GET", SITE + "/rest/api/3/serverInfo"))
        kw = request.call_args.kwargs
        self.assertFalse(kw["allow_redirects"])
        self.assertEqual(kw["timeout"], (10, 30))
        self.assertNotIn(TOKEN, json.dumps(kw, default=str))

    def test_scoped_tokens_use_the_gateway_base(self):
        self.cfg["api_site"] = "https://api.atlassian.com/ex/jira/abc-123"
        _, _, _, request = self.call("/rest/api/3/myself", replies=[response(
            body=b"{}", url="https://api.atlassian.com/ex/jira/abc-123/rest/api/3/myself")])
        self.assertEqual(request.call_args.args[1], "https://api.atlassian.com/ex/jira/abc-123/rest/api/3/myself")

    def test_query_parameters_repeat_in_order_and_are_encoded(self):
        _, _, _, request = self.call("/rest/api/3/project/search", "--query", "maxResults=20",
                                     "-q", "expand=lead", "-q", "query=a&b c", replies=[response(body=b"{}")])
        params = request.call_args.kwargs["params"]
        self.assertEqual(params, [("maxResults", "20"), ("expand", "lead"), ("query", "a&b c")])
        prepared = requests.Request("GET", SITE + "/x", params=params).prepare()
        self.assertTrue(prepared.url.endswith("?maxResults=20&expand=lead&query=a%26b+c"))

    def test_json_data_is_sent_unchanged_from_inline_file_and_stdin(self):
        body = b'{"fields": {"summary": "x", "customfield_1": [1, 2]}, "update": {}}'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "issue.json")
            path.write_bytes(body)
            for source, stdin in ((body.decode(), b""), ("@" + str(path), b""), ("@-", body)):
                _, _, _, request = self.call("/rest/api/3/issue", "-X", "post", "--data", source,
                                             replies=[response(201, b'{"key":"BUG-1"}')], stdin=stdin)
                kw = request.call_args.kwargs
                self.assertEqual(request.call_args.args[0], "POST")
                self.assertEqual(kw["data"], body)
                self.assertEqual(kw["headers"]["Content-Type"], "application/json")

    def test_body_never_changes_the_method_and_bad_json_is_rejected_before_sending(self):
        for argv in (["--data", "{}"], ["-X", "HEAD", "--data", "{}"], ["-X", "POST", "--data", "{oops"],
                     ["-X", "POST", "--raw-data", "a,b"], ["-X", "POST", "--data", "{}", "--form", "a=b"],
                     ["--content-type", "text/plain"]):
            code, out, err, request = self.call("/rest/api/3/issue", *argv)
            self.assertEqual(code, 2, argv)
            self.assertEqual(self.error(err)["code"], "invalid_input")
            self.assertEqual(out, b"")
            request.assert_not_called()

    def test_raw_data_uses_the_supplied_content_type(self):
        _, _, _, request = self.call("/rest/api/3/x", "-X", "PUT", "--raw-data", "a,b", "--content-type", "text/csv",
                                     replies=[response(204)])
        self.assertEqual(request.call_args.kwargs["data"], b"a,b")
        self.assertEqual(request.call_args.kwargs["headers"]["Content-Type"], "text/csv")

    def test_multipart_upload_with_attachment_header(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "proof.txt")
            path.write_text("proof")
            _, _, _, request = self.call("/rest/api/3/issue/BUG-703/attachments", "-X", "POST", "--form",
                                         f"file=@{path}", "-F", "note=hi", "-H", "X-Atlassian-Token: no-check",
                                         replies=[response(200, b"[]")])
        kw = request.call_args.kwargs
        self.assertIsNone(kw["headers"]["Content-Type"])
        self.assertEqual(kw["headers"]["X-Atlassian-Token"], "no-check")
        self.assertEqual([f[0] for f in kw["files"]], ["file", "note"])
        self.assertEqual(kw["files"][0][1][0], "proof.txt")
        self.assertEqual(kw["files"][1][1], (None, "hi"))

    def test_form_needs_existing_files_and_never_reads_stdin(self):
        for item in ("file=@-", "file=@/nonexistent/proof.txt", "novalue", "=x"):
            code, _, err, request = self.call("/rest/api/3/x", "-X", "POST", "--form", item)
            self.assertEqual(code, 2, item)
            request.assert_not_called()

    # Destination and header boundaries

    def test_paths_that_could_leave_the_site_or_change_the_resource_are_rejected(self):
        for path in ("https://evil.example/rest/api/3/myself", "//evil.example/rest", "rest/api/3/myself",
                     "/api/3/myself", "/rest/../admin", "/rest/api/%2e%2e/x", "/rest/api/3/issue%2fBUG-1",
                     "/rest/api/3/myself?expand=x", "/rest/api/3/my self", "/rest//api", "/rest/api\\3",
                     "/rest/api/3/é", "/rest/api/%zz"):
            code, _, err, request = self.call(path)
            self.assertEqual(code, 2, path)
            self.assertEqual(self.error(err)["code"], "invalid_input", path)
            request.assert_not_called()

    def test_managed_headers_cannot_be_overridden(self):
        for header in ("Authorization: Basic x", "authorization: Bearer x", "Host: evil.example", "Cookie: a=b",
                       "Content-Type: text/plain", "Content-Length: 1", "X-Forwarded-For: 1.2.3.4",
                       "Proxy-Authorization: x", "Transfer-Encoding: chunked", "X-Ok: a\r\nInjected: b", "Bad Name: x"):
            code, _, err, request = self.call("/rest/api/3/myself", "-H", header)
            self.assertEqual(code, 2, header)
            request.assert_not_called()

    def test_permitted_headers_are_sent(self):
        _, _, _, request = self.call("/rest/api/3/myself", "-H", "X-ExperimentalApi: opt-in", "-H", "Accept:text/plain",
                                     replies=[response(body=b"ok", headers={"Content-Type": "text/plain"})])
        headers = request.call_args.kwargs["headers"]
        self.assertEqual(headers["X-ExperimentalApi"], "opt-in")
        self.assertEqual(headers["Accept"], "text/plain")

    def test_redirects_are_not_followed_and_signed_locations_are_trimmed(self):
        location = "https://api.media.atlassian.com/file/abc/binary?token=eyJsigned.jwt&client=x"
        code, out, err, request = self.call("/rest/api/3/attachment/content/1", replies=[response(303, headers={"Location": location})])
        self.assertEqual((code, out, request.call_count), (1, b"", 1))
        error = self.error(err)
        self.assertEqual(error["status"], 303)
        self.assertEqual(error["location"], "https://api.media.atlassian.com/file/abc/binary")
        self.assertNotIn("eyJsigned", err)
        self.assertIn("redirect=false", error["message"])

    # Responses

    def test_upstream_shapes_are_written_unchanged_when_piped(self):
        for body in (b"[1,2]", b'"text"', b"42", b"true", b"null", b"<xml/>"):
            code, out, _, _ = self.call("/rest/api/3/x", replies=[response(body=body, headers={"Content-Type": "application/json"})])
            self.assertEqual((code, out), (0, body))

    def test_json_is_indented_on_a_terminal(self):
        _, out, _, _ = self.call("/rest/api/3/x", tty=True, replies=[response(body=b'{"a":[1]}', headers={"Content-Type": "application/json;charset=UTF-8"})])
        self.assertEqual(out, b'{\n  "a": [\n    1\n  ]\n}\n')

    def test_empty_no_content_and_head_responses_print_nothing(self):
        for argv, reply in ((["-X", "DELETE"], response(204)), (["-X", "HEAD"], response(200, b"")),
                            ([], response(200, b""))):
            code, out, err, _ = self.call("/rest/api/3/x", *argv, replies=[reply])
            self.assertEqual((code, out, err), (0, b"", ""))

    def test_binary_is_not_printed_to_a_terminal(self):
        code, out, err, _ = self.call("/rest/api/3/attachment/content/1", tty=True,
                                      replies=[response(body=b"\x89PNG", headers={"Content-Type": "image/png", "Content-Length": "4"})])
        self.assertEqual((code, out), (0, b""))
        self.assertIn("--output", err)

    def test_output_writes_a_new_file_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder, "body.bin")
            code, out, err, _ = self.call("/rest/api/3/x", "--output", str(target),
                                          replies=[response(body=b"\x00\x01", headers={"Content-Type": "application/octet-stream"})])
            self.assertEqual((code, out, target.read_bytes()), (0, b"", b"\x00\x01"))
            code, _, err, request = self.call("/rest/api/3/x", "-o", str(target), replies=[response(body=b"new")])
            self.assertEqual(code, 2)
            request.assert_not_called()
            self.assertEqual(target.read_bytes(), b"\x00\x01")
            self.assertEqual(sorted(os.listdir(folder)), ["body.bin"])

    def test_include_prints_metadata_to_stderr_and_redacts_cookies(self):
        code, out, err, _ = self.call("/rest/api/3/myself", "--include", replies=[response(
            body=b"{}", headers={"Content-Type": "application/json", "Set-Cookie": "atlassian.xsrf.token=abc"})])
        self.assertEqual(out, b"{}")
        self.assertTrue(err.startswith("HTTP 200 OK\n"))
        self.assertIn("Set-Cookie: [redacted]", err)
        self.assertNotIn("abc", err)

    # Failures

    def test_http_errors_go_to_stderr_as_json_with_upstream_body(self):
        code, out, err, _ = self.call("/rest/api/3/issue/BUG-1", replies=[response(
            404, b'{"errorMessages":["Issue does not exist"]}', {"Content-Type": "application/json"})])
        self.assertEqual((code, out), (1, b""))
        error = self.error(err)
        self.assertEqual((error["code"], error["status"], error["method"], error["path"]),
                         ("jira_error", 404, "GET", "/rest/api/3/issue/BUG-1"))
        self.assertEqual(error["body"], {"errorMessages": ["Issue does not exist"]})

    def test_echoed_credentials_and_derived_auth_values_are_redacted(self):
        echo = f"bad token {TOKEN} header Basic {BASIC}".encode()
        code, _, err, _ = self.call("/rest/api/3/myself", "--include", replies=[response(
            401, echo, {"Content-Type": "text/plain", "X-Debug": f"Basic {BASIC}"})])
        self.assertEqual(code, 1)
        self.assertNotIn(TOKEN, err)
        self.assertNotIn(BASIC, err)
        self.assertIn("[redacted]", err)

    def test_reads_retry_but_writes_are_never_replayed(self):
        code, out, _, request = self.call("/rest/api/3/myself", replies=[response(503), response(body=b"{}")])
        self.assertEqual((code, out, request.call_count), (0, b"{}", 2))
        code, _, err, request = self.call("/rest/api/3/search/jql", "-X", "POST", "-d", "{}",
                                          replies=[response(503), response(body=b"{}")])
        self.assertEqual((code, request.call_count), (1, 1))
        code, _, err, request = self.call("/rest/api/3/issue", "-X", "POST", "-d", "{}", replies=[requests.Timeout()])
        self.assertEqual((code, self.error(err)["code"], request.call_count), (1, "uncertain_outcome", 1))

    def test_permission_denial_is_reported_once_without_prompting(self):
        with patch("jsup.ui.confirm", side_effect=AssertionError("prompted")):
            code, out, err, request = self.call("/rest/api/3/project/SECRET", tty=True, replies=[response(
                403, b'{"errorMessages":["You do not have permission"]}', {"Content-Type": "application/json"})])
        self.assertEqual((code, out, request.call_count), (1, b"", 1))
        self.assertEqual(self.error(err)["status"], 403)

    def test_rate_limits_retry_only_short_server_requested_waits(self):
        with patch("jsup.client.time.sleep") as sleep:
            code, out, _, request = self.call("/rest/api/3/myself", replies=[
                response(429, headers={"Retry-After": "2"}), response(body=b"{}")])
        self.assertEqual((code, out, request.call_count), (0, b"{}", 2))
        sleep.assert_called_once_with(2.0)
        code, _, err, request = self.call("/rest/api/3/myself", replies=[response(429, headers={"Retry-After": "120"})])
        self.assertEqual((code, request.call_count, self.error(err)["status"]), (1, 1, 429))

    def test_unapproved_credential_store_fails_fast_without_sending(self):
        from jsup.credentials import CredentialError
        with patch("jsup.config.resolve_config", side_effect=CredentialError(
                "Could not read the OS credential store without approved access.")):
            code, out, err, request = self.call("/rest/api/3/myself", "--no-input")
        self.assertEqual((code, out), (2, b""))
        self.assertEqual(self.error(err)["code"], "invalid_input")
        request.assert_not_called()

    def test_no_child_process_is_started(self):
        with patch("subprocess.Popen", side_effect=AssertionError("child process")), \
                patch("os.system", side_effect=AssertionError("child process")):
            code, _, _, _ = self.call("/rest/api/3/issue", "-X", "POST", "--data", "{}", replies=[response(201, b"{}")])
        self.assertEqual(code, 0)

    def test_csv_and_columns_are_rejected(self):
        for flag in (["--csv"], ["--columns", "key"]):
            code, _, _, request = self.call("/rest/api/3/myself", *flag)
            self.assertEqual(code, 2)
            request.assert_not_called()

    def test_secret_values_cover_derived_forms(self):
        values = secret_values(EMAIL, "a/b=")
        self.assertIn("a/b=", values)
        self.assertIn("a%2Fb%3D", values)
        self.assertIn(base64.b64encode(f"{EMAIL}:a/b=".encode()).decode(), values)
        self.assertEqual(secret_values(EMAIL, ""), [])


class ApiPaginateTests(ApiTestBase):
    """--paginate follows Jira's page protocols and prints one merged result."""

    def page(self, data):
        return response(body=json.dumps(data).encode(), headers={"Content-Type": "application/json"})

    def merged(self, out):
        return json.loads(out)

    def test_offset_pages_merge_until_total(self):
        code, out, _, request = self.call("/rest/api/3/project/search", "--query", "maxResults=2", "--paginate", replies=[
            self.page({"startAt": 0, "maxResults": 2, "total": 3, "isLast": False, "values": [{"id": 1}, {"id": 2}]}),
            self.page({"startAt": 2, "maxResults": 2, "total": 3, "isLast": True, "values": [{"id": 3}]})])
        self.assertEqual(code, 0)
        result = self.merged(out)
        self.assertEqual([v["id"] for v in result["values"]], [1, 2, 3])
        self.assertEqual((result["fetched"], result["isLast"]), (3, True))
        second = request.call_args_list[1].kwargs["params"]
        self.assertIn(("startAt", "2"), second)
        self.assertEqual([p for p in second if p[0] == "maxResults"], [("maxResults", "2")])

    def test_offset_pages_without_total_stop_on_a_short_page(self):
        code, out, _, request = self.call("/rest/agile/1.0/board/1/issue", "--paginate", replies=[
            self.page({"startAt": 0, "maxResults": 2, "issues": [{"key": "A-1"}, {"key": "A-2"}]}),
            self.page({"startAt": 2, "maxResults": 2, "issues": [{"key": "A-3"}]})])
        self.assertEqual((code, self.merged(out)["fetched"], request.call_count), (0, 3, 2))

    def test_cursor_pages_use_the_token_in_the_query_or_the_body(self):
        code, out, _, request = self.call("/rest/api/3/search/jql", "--query", "jql=project = BUG", "--paginate", replies=[
            self.page({"issues": [{"key": "B-2"}], "nextPageToken": "t1", "isLast": False}),
            self.page({"issues": [{"key": "B-1"}], "isLast": True})])
        self.assertEqual(code, 0)
        self.assertIn(("nextPageToken", "t1"), request.call_args_list[1].kwargs["params"])
        result = self.merged(out)
        self.assertNotIn("nextPageToken", result)
        self.assertEqual((result["fetched"], result["isLast"]), (2, True))
        code, out, _, request = self.call("/rest/api/3/search/jql", "-X", "POST", "--data", '{"jql":"project = BUG"}',
                                          "--paginate", replies=[
            self.page({"issues": [{"key": "B-2"}], "nextPageToken": "t1"}),
            self.page({"issues": [{"key": "B-1"}], "isLast": True})])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(request.call_args_list[1].kwargs["data"]), {"jql": "project = BUG", "nextPageToken": "t1"})

    def test_service_desk_pages_use_start_and_is_last_page(self):
        code, out, _, request = self.call("/rest/servicedeskapi/servicedesk", "--paginate", replies=[
            self.page({"start": 0, "limit": 1, "size": 1, "isLastPage": False, "values": [{"id": "1"}]}),
            self.page({"start": 1, "limit": 1, "size": 1, "isLastPage": True, "values": [{"id": "2"}]})])
        self.assertEqual(code, 0)
        self.assertIn(("start", "1"), request.call_args_list[1].kwargs["params"])
        result = self.merged(out)
        self.assertEqual((result["size"], result["isLastPage"], result["fetched"]), (2, True, 2))

    def test_max_items_stops_early_and_marks_the_result_incomplete(self):
        code, out, _, request = self.call("/rest/api/3/project/search", "--paginate", "--max-items", "3", replies=[
            self.page({"startAt": 0, "maxResults": 2, "total": 10, "values": [{"id": 1}, {"id": 2}]}),
            self.page({"startAt": 2, "maxResults": 2, "total": 10, "values": [{"id": 3}, {"id": 4}]})])
        result = self.merged(out)
        self.assertEqual((code, result["fetched"], result["isLast"], request.call_count), (0, 3, False, 2))

    def test_loops_and_format_changes_fail_without_partial_output(self):
        code, out, err, _ = self.call("/rest/api/3/search/jql", "--paginate", replies=[
            self.page({"issues": [{"key": "A"}], "nextPageToken": "same"}),
            self.page({"issues": [{"key": "B"}], "nextPageToken": "same"})])
        self.assertEqual((code, out), (1, b""))
        self.assertIn("repeated a cursor", self.error(err)["message"])
        code, out, err, _ = self.call("/rest/api/3/project/search", "--paginate", replies=[
            self.page({"startAt": 0, "maxResults": 1, "total": 2, "values": [{"id": 1}]}),
            self.page({"start": 1, "isLastPage": True, "values": [{"id": 2}]})])
        self.assertEqual((code, out), (1, b""))
        self.assertIn("changed its paging format", self.error(err)["message"])

    def test_errors_on_a_later_page_name_the_page(self):
        code, out, err, _ = self.call("/rest/api/3/project/search", "--paginate", replies=[
            self.page({"startAt": 0, "maxResults": 1, "total": 2, "values": [{"id": 1}]}),
            response(403, b'{"errorMessages":["no"]}', {"Content-Type": "application/json"})])
        error = self.error(err)
        self.assertEqual((code, out, error["page"], error["status"]), (1, b"", 2, 403))
        self.assertTrue(error["message"].startswith("Page 2: "))

    def test_page_limit_stops_runaway_offsets(self):
        endless = [self.page({"startAt": i, "maxResults": 1, "values": [{"id": i}]}) for i in range(4)]
        with patch("jsup.api.MAX_PAGES", 3):
            code, out, err, request = self.call("/rest/api/3/project/search", "--paginate", replies=endless)
        self.assertEqual((code, out, request.call_count), (1, b"", 3))
        self.assertIn("Stopped after 3 pages", self.error(err)["message"])

    def test_unpaged_responses_and_unsupported_combinations_are_rejected(self):
        code, _, err, _ = self.call("/rest/api/3/myself", "--paginate", replies=[self.page({"accountId": "x"})])
        self.assertEqual((code, self.error(err)["code"]), (2, "invalid_input"))
        with tempfile.TemporaryDirectory() as folder:
            for argv in (["-X", "POST", "--data", "{}"], ["--output", str(Path(folder, "out.json"))], ["--include"],
                         ["--max-items", "5"]):
                path = "/rest/api/3/issue" if "POST" in argv else "/rest/api/3/project/search"
                flags = argv if argv == ["--max-items", "5"] else [*argv, "--paginate"]
                code, out, err, request = self.call(path, *flags)
                self.assertEqual((code, out), (2, b""), argv)
                request.assert_not_called()
        code, _, _, request = self.call("/rest/api/3/search/jql", "-X", "POST", "--data", "[1]", "--paginate")
        self.assertEqual(code, 2)
        request.assert_not_called()

    def test_merged_json_is_indented_on_a_terminal(self):
        _, out, _, _ = self.call("/rest/servicedeskapi/servicedesk", "--paginate", tty=True, replies=[
            self.page({"start": 0, "isLastPage": True, "values": [{"id": "1"}]})])
        self.assertTrue(out.startswith(b"{\n  "))


class ApiIdentityTests(unittest.TestCase):
    """Uses the real resolver against a temporary profile file, not a mocked identity."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        config = Path(folder.name, "config.json")
        config.write_text(json.dumps({"schema_version": 2, "active_profile": "work", "profiles": {"work": {
            "site": SITE, "email": EMAIL, "storage": "file", "credential_id": "work-id", "project": "BUG"}}}))
        Path(folder.name, "credentials.json").write_text(json.dumps({"work-id": TOKEN}))
        for target in (patch("jsup.config.CONFIG_PATH", config),
                       patch.dict(os.environ, {}, clear=False)):
            target.start()
            self.addCleanup(target.stop)
        for key in ("JIRA_SITE", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROFILE", "JIRA_PROJECT"):
            os.environ.pop(key, None)

    def call(self, *argv, replies=()):
        err = io.StringIO()
        with patch("requests.Session.request", side_effect=list(replies)) as request, \
                patch("sys.stdout", Pipe()), redirect_stderr(err):
            try:
                jira_main(["api", *argv])
                code = 0
            except SystemExit as exit:
                code = exit.code
        return code, err.getvalue(), request

    def test_saved_profile_is_used(self):
        code, _, request = self.call("/rest/api/3/myself", "--profile", "work", replies=[response(body=b"{}")])
        self.assertEqual((code, request.call_args.args[1]), (0, SITE + "/rest/api/3/myself"))

    def test_profile_is_never_mixed_with_identity_flags(self):
        code, err, request = self.call("/rest/api/3/myself", "--profile", "work", "--token", "other-token")
        self.assertEqual(code, 2)
        self.assertIn("cannot be combined", json.loads(err)["error"]["message"])
        self.assertNotIn("other-token", err)
        request.assert_not_called()

    def test_environment_identity_is_complete_or_rejected(self):
        with patch.dict(os.environ, {"JIRA_SITE": "https://other.atlassian.net"}):
            code, err, request = self.call("/rest/api/3/myself")
        self.assertEqual(code, 2)
        request.assert_not_called()
        with patch.dict(os.environ, {"JIRA_SITE": "https://other.atlassian.net", "JIRA_EMAIL": "bot@example.com",
                                     "JIRA_API_TOKEN": "env-token"}):
            code, _, request = self.call("/rest/api/3/myself", replies=[response(body=b"{}", url="https://other.atlassian.net/")])
        self.assertEqual((code, request.call_args.args[1]), (0, "https://other.atlassian.net/rest/api/3/myself"))

    def test_unknown_profile_is_rejected(self):
        code, err, request = self.call("/rest/api/3/myself", "--profile", "nope")
        self.assertEqual(code, 2)
        self.assertIn("Unknown profile", json.loads(err)["error"]["message"])
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
