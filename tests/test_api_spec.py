import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

import requests

from jsup import api_spec
from jsup.api import ApiError
from jsup.cli import jira_main

FIXTURE = {
    "openapi": "3.0.1",
    "info": {"title": "Fixture", "version": "1001.0.0"},
    "paths": {
        "/rest/api/3/issue": {"post": {
            "operationId": "createIssue", "summary": "Create issue",
            "description": "Creates an issue.\n\n**[Permissions](#permissions) required:** *Create issues* permission.\n\nMore.",
            "x-atlassian-oauth2-scopes": [{"scheme": "OAuth2", "scopes": ["write:jira-work"], "state": "Current"}],
            "x-atlassian-connect-scope": "WRITE",
            "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/IssueUpdate"}}}},
            "responses": {"201": {"description": "Created", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Created"}}}},
                          "400": {"description": "Bad", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Errors"}}}}}}},
        "/rest/api/3/issue/{issueIdOrKey}": {
            "parameters": [{"name": "issueIdOrKey", "in": "path", "required": True, "schema": {"type": "string"}}],
            "get": {"operationId": "getIssue", "responses": {"200": {"description": "OK"}}},
            "delete": {"operationId": "deleteIssue", "responses": {"204": {"description": "Deleted"}}}},
        "/rest/api/3/issue/createmeta": {"get": {"operationId": "getCreateIssueMeta", "responses": {"200": {"description": "OK"}}}},
        "/rest/api/3/node": {"get": {"operationId": "getNode", "responses": {"200": {"description": "OK", "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/Node"}}}}}}},
        "/rest/api/3/remote": {"get": {"operationId": "getRemote", "responses": {"200": {"description": "OK", "content": {
            "application/json": {"schema": {"$ref": "https://evil.example/schema.json"}}}}}}},
    },
    "components": {"schemas": {
        "IssueUpdate": {"type": "object", "properties": {"fields": {"type": "object"}, "update": {"$ref": "#/components/schemas/Update"}}},
        "Update": {"type": "object"},
        "Created": {"type": "object", "properties": {"key": {"type": "string"}}},
        "Errors": {"type": "object"},
        "Node": {"type": "object", "properties": {"child": {"$ref": "#/components/schemas/Node"}}},
    }},
}


class FakeResponse:
    def __init__(self, status=200, body=b"", headers=None):
        self.status_code, self.body, self.headers = status, body, headers or {}

    def iter_content(self, size):
        for i in range(0, len(self.body), size):
            yield self.body[i:i + size]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def get(self, url, **kw):
        self.calls.append((url, kw))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def ok(document=FIXTURE, etag='"v1"'):
    return FakeResponse(200, json.dumps(document).encode(), {"ETag": etag})


class SpecTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def describe(self, path, method="GET", session=None):
        return api_spec.describe(path, method, self.folder, session or FakeSession(ok()))

    def test_first_lookup_downloads_without_credentials_or_redirects(self):
        session = FakeSession(ok())
        result = self.describe("/rest/api/3/issue", "POST", session)
        url, kw = session.calls[0]
        self.assertEqual(url, api_spec.SOURCES["platform"][1])
        self.assertFalse(kw["allow_redirects"])
        self.assertNotIn("auth", kw)
        self.assertNotIn("Authorization", kw["headers"])
        self.assertEqual(result["operationId"], "createIssue")
        self.assertEqual(result["permissions"], "*Create issues* permission.")
        self.assertEqual(result["scopes"]["connect"], "WRITE")
        self.assertEqual(result["source"]["family"], "platform")
        self.assertFalse(result["source"]["stale"])

    def test_concrete_paths_match_templates_and_literals_win(self):
        self.describe("/rest/api/3/issue", "POST")
        result = self.describe("/rest/api/3/issue/BUG-703")
        self.assertEqual((result["template"], result["pathParameters"]), ("/rest/api/3/issue/{issueIdOrKey}", {"issueIdOrKey": "BUG-703"}))
        self.assertEqual(result["parameters"][0]["x-value"], "BUG-703")
        self.assertEqual(self.describe("/rest/api/3/issue/createmeta")["operationId"], "getCreateIssueMeta")
        # A method the literal path lacks falls through to the template that has it.
        self.assertEqual(self.describe("/rest/api/3/issue/createmeta", "DELETE")["operationId"], "deleteIssue")

    def test_missing_operations_are_reported_not_invented(self):
        self.describe("/rest/api/3/issue", "POST")
        with self.assertRaises(ApiError) as missing:
            self.describe("/rest/api/3/issue", "GET")
        self.assertEqual((missing.exception.code, missing.exception.details["methods"]), ("spec_not_found", ["POST"]))
        with self.assertRaises(ApiError) as unknown:
            self.describe("/rest/api/3/brand/new/endpoint")
        self.assertIn("can still be sent", str(unknown.exception))

    def test_references_resolve_locally_with_cycle_and_external_limits(self):
        self.describe("/rest/api/3/issue", "POST")
        body = self.describe("/rest/api/3/issue", "POST")["requestBody"]["content"]["application/json"]["schema"]
        self.assertEqual((body["x-schema"], body["properties"]["update"]["x-schema"]), ("IssueUpdate", "Update"))
        node = self.describe("/rest/api/3/node")["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertIn("recursive", node["properties"]["child"]["x-note"])
        remote = self.describe("/rest/api/3/remote")["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertEqual(remote["$ref"], "https://evil.example/schema.json")
        self.assertIn("not followed", remote["x-note"])

    def test_error_responses_are_summarized(self):
        responses = self.describe("/rest/api/3/issue", "POST")["responses"]
        self.assertEqual(responses["400"], {"description": "Bad"})
        self.assertEqual(responses["201"]["content"]["application/json"]["schema"]["x-schema"], "Created")

    def test_refresh_is_conditional_and_keeps_the_cache_when_offline_or_invalid(self):
        api_spec.refresh(["platform"], self.folder, FakeSession(ok()))
        unchanged = FakeSession(FakeResponse(304))
        self.assertEqual(api_spec.refresh(["platform"], self.folder, unchanged)[0]["status"], "unchanged")
        self.assertEqual(unchanged.calls[0][1]["headers"]["If-None-Match"], '"v1"')
        self.assertEqual(unchanged.calls[0][1]["headers"]["Accept-Encoding"], "identity")
        before = (self.folder / "platform.json").read_bytes()
        for reply, code in ((requests.ConnectionError(), "network_error"), (FakeResponse(200, b"not json"), "spec_invalid"),
                            (FakeResponse(200, b'{"swagger": "2.0", "paths": {}}'), "spec_invalid"),
                            (FakeResponse(302, headers={"Location": "https://evil.example/"}), "spec_unavailable")):
            with self.assertRaises(ApiError) as failure:
                api_spec.refresh(["platform"], self.folder, FakeSession(reply))
            self.assertEqual(failure.exception.code, code)
            self.assertEqual((self.folder / "platform.json").read_bytes(), before)
        # Lookups keep working from the cache while offline.
        self.assertEqual(api_spec.describe("/rest/api/3/issue", "POST", self.folder,
                                           FakeSession(requests.ConnectionError()))["operationId"], "createIssue")

    def test_oversized_downloads_are_rejected(self):
        with patch.object(api_spec, "MAX_SPEC", 100), self.assertRaises(ApiError) as big:
            api_spec.refresh(["platform"], self.folder, FakeSession(ok()))
        self.assertEqual(big.exception.code, "spec_invalid")
        self.assertFalse((self.folder / "platform.json").exists())

    def test_no_cache_and_no_network_fails_clearly(self):
        with self.assertRaises(ApiError) as failure:
            self.describe("/rest/api/3/issue", "POST", FakeSession(requests.ConnectionError()))
        self.assertIn("No cached copy exists yet", str(failure.exception))

    def test_tampered_cache_is_detected(self):
        self.describe("/rest/api/3/issue", "POST")
        (self.folder / "platform.json").write_text(json.dumps({**FIXTURE, "info": {"title": "x", "version": "2"}}))
        with self.assertRaises(ApiError) as tampered:
            self.describe("/rest/api/3/issue", "POST", FakeSession())
        self.assertIn("hash", str(tampered.exception))

    def test_old_caches_are_marked_stale(self):
        self.describe("/rest/api/3/issue", "POST")
        index = json.loads((self.folder / "index.json").read_text())
        index["platform"]["checked_at"] = "2020-01-01T00:00:00+00:00"
        (self.folder / "index.json").write_text(json.dumps(index))
        self.assertTrue(self.describe("/rest/api/3/issue", "POST", FakeSession())["source"]["stale"])
        self.assertTrue(api_spec.status(self.folder)[0]["stale"])

    def test_families_are_chosen_by_path_prefix(self):
        self.assertEqual(api_spec.family_for("/rest/api/3/myself"), "platform")
        self.assertEqual(api_spec.family_for("/rest/agile/1.0/board"), "software")
        self.assertEqual(api_spec.family_for("/rest/servicedeskapi/request"), "service-management")


class SpecCommandTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        api_spec.refresh(["platform"], Path(folder.name), FakeSession(ok()))
        for target in (patch.object(api_spec, "cache_dir", return_value=Path(folder.name)),
                       # Discovery must never resolve an identity or touch the credential store.
                       patch("jsup.config.resolve_config", side_effect=AssertionError("identity resolved")),
                       patch("requests.Session.request", side_effect=AssertionError("Jira contacted"))):
            target.start()
            self.addCleanup(target.stop)

    def call(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with patch("sys.stdout", out), redirect_stderr(err):
            try:
                jira_main(["api", *argv])
                code = 0
            except SystemExit as exit:
                code = exit.code
        return code, out.getvalue(), err.getvalue()

    def test_spec_prints_json_without_credentials(self):
        code, out, err = self.call("/rest/api/3/issue", "-X", "POST", "--spec")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out)["operationId"], "createIssue")

    def test_spec_rejects_request_options_and_extra_arguments(self):
        for argv in (["--data", "{}", "-X", "POST"], ["--query", "a=b"], ["--output", "x.json"], ["-H", "X-A: b"]):
            code, out, err = self.call("/rest/api/3/issue", "--spec", *argv)
            self.assertEqual((code, out), (2, ""), argv)
            self.assertEqual(json.loads(err)["error"]["code"], "invalid_input")
        code, _, err = self.call("/rest/api/3/issue", "extra", "--spec")
        self.assertEqual(code, 2)

    def test_spec_status_and_unknown_action(self):
        code, out, _ = self.call("spec", "status")
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)[0]["cached"])
        self.assertEqual(self.call("spec", "nope")[0], 2)

    def test_not_found_is_a_json_error_with_exit_1(self):
        code, out, err = self.call("/rest/api/3/unknown", "--spec")
        self.assertEqual((code, out), (1, ""))
        self.assertEqual(json.loads(err)["error"]["code"], "spec_not_found")


if __name__ == "__main__":
    unittest.main()
