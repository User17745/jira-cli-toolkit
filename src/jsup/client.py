"""Thin wrapper over the official Jira Cloud REST APIs (v3 + Agile 1.0)."""
from __future__ import annotations

import json
import time
from contextlib import ExitStack
from pathlib import Path
import os
import tempfile
from urllib.parse import quote

import requests


class JiraError(Exception):
    def __init__(self, method: str, path: str, status: int, body: str):
        self.method, self.path, self.status, self.body = method, path, status, body
        super().__init__(f"{method} {path} -> {status}: {body[:500]}")


class UncertainOutcome(requests.RequestException):
    """A mutation may have reached Jira; it must not be replayed automatically."""


def identifier(value):
    return quote(str(value), safe="")


def project_jql(project: str) -> str:
    """Quote project identifiers in generated JQL."""
    return f"project = {json.dumps(project, ensure_ascii=False)}"


def adf(text: str) -> dict:
    """Plain text -> Atlassian Document Format (required by API v3)."""
    return {"type": "doc", "version": 1,
            "content": [{"type": "paragraph",
                         "content": [{"type": "text", "text": line or " "}]}
                        for line in (text or "").splitlines() or [""]]}


def adf_to_text(node) -> str:
    if isinstance(node, str):
        return node
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    out = []
    for c in node.get("content", []) or []:
        out.append(adf_to_text(c))
        if isinstance(c, dict) and c.get("type") == "paragraph":
            out.append("\n")
    return "".join(out).strip()


class Jira:
    def __init__(self, site: str, email: str, token: str):
        self.site = site
        self.s = requests.Session()
        self.s.auth = (email, token)
        self.s.headers.update({"Accept": "application/json",
                               "Content-Type": "application/json"})

    def _send(self, method: str, path: str, *, safe: bool, **kw) -> requests.Response:
        """Send one request to the trusted site; return the final response unparsed.

        Safe requests retry bounded transient failures. A write whose connection drops
        raises UncertainOutcome and is never replayed. Redirects are not followed, so
        credentials never travel to another destination.
        """
        kw.setdefault("timeout", (10, 30))
        kw["allow_redirects"] = False
        for attempt in range(3):
            try:
                r = self.s.request(method, self.site + path, **kw)
            except (requests.Timeout, requests.ConnectionError):
                if not safe:
                    raise UncertainOutcome(
                        "Connection lost during a write. The outcome is unknown; inspect Jira before retrying.") from None
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
                continue
            if safe and r.status_code in (429, 502, 503, 504) and attempt < 2:
                try:
                    delay = float(r.headers.get("Retry-After", 2 ** attempt))
                except (TypeError, ValueError):
                    delay = 2 ** attempt
                # Do not retry earlier than a long server-requested wait.
                if 0 <= delay <= 30:
                    r.close()
                    time.sleep(delay)
                    continue
            return r

    def _req(self, method: str, path: str, **kw):
        safe = kw.pop("retry_safe", method in ("GET", "HEAD"))
        r = self._send(method, path, safe=safe, **kw)
        if r.status_code == 204 or (200 <= r.status_code < 300 and not r.text):
            return {}
        if 200 <= r.status_code < 300:
            try:
                data = r.json()
            except ValueError:
                raise JiraError(method, path, 502, "Jira returned malformed JSON.") from None
            if not isinstance(data, (dict, list)):
                raise JiraError(method, path, 502, "Jira returned an unexpected response shape.")
            return data
        raise JiraError(method, path, r.status_code, r.text)

    def _offset(self, path, key="values", *, params=None, limit=50, all_results=False):
        """Collect offset pages with a total-result limit, honoring server caps."""
        collected, offset, last = [], 0, {}
        for _ in range(10000):
            size = 100 if all_results else min(100, limit - len(collected))
            page = self._req("GET", path, params={**(params or {}), "startAt": offset, "maxResults": size})
            if not isinstance(page, dict) or not isinstance(page.get(key), list):
                raise JiraError("GET", path, 502, "Invalid paginated response.")
            batch = page[key]
            collected.extend(batch if all_results else batch[:size])
            last = page
            offset += len(batch)
            done = page.get("isLast") is True or (isinstance(page.get("total"), int) and offset >= page["total"])
            if not batch or done or (not all_results and len(collected) >= limit):
                break
            if "total" not in page and "isLast" not in page and len(batch) < size:
                break
        else:
            raise JiraError("GET", path, 502, "Pagination exceeded the safety limit.")
        last = {**last, key: collected, "startAt": 0, "fetched": len(collected)}
        if "total" in last:
            last["isLast"] = offset >= last["total"]
        return last

    def close(self):
        self.s.close()

    # -- identity / projects -------------------------------------------------
    def me(self): return self._req("GET", "/rest/api/3/myself")
    def projects(self, limit=50, all_results=False):
        return self._offset("/rest/api/3/project/search", limit=limit, all_results=all_results)["values"]
    def project_get(self, key): return self._req("GET", f"/rest/api/3/project/{identifier(key)}")

    # -- issues ---------------------------------------------------------------
    def issue_create(self, project, summary, desc="", itype="Task",
                     priority=None, labels=(), components=(), assignee=None,
                     extra_fields=None):
        fields: dict = {"project": {"key": project}, "summary": summary,
                        "description": adf(desc), "issuetype": {"name": itype}}
        if priority: fields["priority"] = {"name": priority}
        if labels: fields["labels"] = list(labels)
        if components: fields["components"] = [{"name": c} for c in components]
        if assignee: fields["assignee"] = {"accountId": assignee}
        if extra_fields: fields.update(extra_fields)
        return self._req("POST", "/rest/api/3/issue", json={"fields": fields})

    def issue_get(self, key):
        return self._req("GET", f"/rest/api/3/issue/{key}")

    def issue_delete(self, key, delete_subtasks=False):
        params = {"deleteSubtasks": "true"} if delete_subtasks else {}
        return self._req("DELETE", f"/rest/api/3/issue/{key}", params=params)

    def search(self, jql, max_results=50,
               fields="summary,status,assignee,priority,updated,components,labels", all_results=False):
        collected, token, seen, page = [], None, set(), {}
        path = "/rest/api/3/search/jql"
        for _ in range(10000):
            size = 100 if all_results else min(100, max_results - len(collected))
            payload = {"jql": jql, "maxResults": size, "fields": fields.split(",") if isinstance(fields, str) else fields}
            if token:
                payload["nextPageToken"] = token
            # POST search is read-only and avoids URL-length limits.
            page = self._req("POST", path, json=payload, retry_safe=True)
            if not isinstance(page, dict) or not isinstance(page.get("issues"), list):
                raise JiraError("POST", path, 502, "Invalid search response.")
            batch = page["issues"]
            collected.extend(batch if all_results else batch[:size])
            token = page.get("nextPageToken")
            if page.get("isLast") is True or (not all_results and len(collected) >= max_results):
                break
            if not token:
                if page.get("isLast") is False:
                    raise JiraError("POST", path, 502, "Search indicated another page without a cursor.")
                break
            if token in seen or not batch:
                raise JiraError("POST", path, 502, "Search pagination did not advance.")
            seen.add(token)
        else:
            raise JiraError("POST", path, 502, "Pagination exceeded the safety limit.")
        return {**page, "issues": collected, "fetched": len(collected)}

    def open_tickets(self, project, extra="", max_results=50, **options):
        jql = project_jql(project) + " AND statusCategory != Done"
        if extra:
            jql += f" AND ({extra})"
        return self.search(jql + " ORDER BY updated DESC", max_results, **options)

    def count_issues(self, jql):
        return self._req("POST", "/rest/api/3/search/approximate-count", json={"jql": jql}, retry_safe=True)

    # -- workflow --------------------------------------------------------------
    def transitions(self, key):
        return self._req("GET", f"/rest/api/3/issue/{key}/transitions")

    def move(self, key, to: str):
        trs = self.transitions(key).get("transitions", [])
        match = next((t for t in trs if t["id"] == to
                      or t["name"].lower() == to.lower()), None)
        if not match:
            avail = ", ".join(f'{t["name"]} [{t["id"]}]' for t in trs)
            raise JiraError("POST", f"/rest/api/3/issue/{key}/transitions",
                            422, f"No transition '{to}'. Available: {avail}")
        self._req("POST", f"/rest/api/3/issue/{key}/transitions",
                  json={"transition": {"id": match["id"]}})
        return {"moved": key, "to": match["name"]}

    # -- comments ---------------------------------------------------------------
    def comment_add(self, key, body):
        return self._req("POST", f"/rest/api/3/issue/{key}/comment",
                         json={"body": adf(body)})

    def comments(self, key, limit=50, all_results=False):
        return self._offset(f"/rest/api/3/issue/{identifier(key)}/comment", "comments", limit=limit, all_results=all_results)

    # -- components ---------------------------------------------------------------
    def components(self, project):
        return self._req("GET", f"/rest/api/3/project/{project}/components")

    def component_create(self, project, name, description=""):
        return self._req("POST", "/rest/api/3/component",
                         json={"name": name, "description": description,
                               "project": project})

    # -- project-specific metadata and editable fields -------------------------
    def issue_types(self, project):
        return self._offset(f"/rest/api/3/issue/createmeta/{identifier(project)}/issuetypes",
                            "issueTypes", all_results=True)["issueTypes"]

    def create_fields(self, project, issue_type):
        return self._offset(f"/rest/api/3/issue/createmeta/{identifier(project)}/issuetypes/{identifier(issue_type)}",
                            "fields", all_results=True)["fields"]

    def project_statuses(self, project):
        return self._req("GET", f"/rest/api/3/project/{identifier(project)}/statuses")

    def edit_fields(self, key):
        return self._req("GET", f"/rest/api/3/issue/{identifier(key)}/editmeta").get("fields", {})

    def transition_fields(self, key):
        return self._req("GET", f"/rest/api/3/issue/{identifier(key)}/transitions", params={"expand": "transitions.fields"})

    def create_with_fields(self, fields):
        return self._req("POST", "/rest/api/3/issue", json={"fields": fields})

    def edit_issue(self, key, fields, updates=None):
        payload = {"fields": fields}
        if updates:
            payload["update"] = updates
        self._req("PUT", f"/rest/api/3/issue/{identifier(key)}", json=payload)
        return {"updated": key, "fields": sorted(fields), "operations": sorted(updates or {})}

    def transition_with_fields(self, key, transition_id, fields):
        self._req("POST", f"/rest/api/3/issue/{identifier(key)}/transitions",
                  json={"transition": {"id": transition_id}, "fields": fields})
        return {"moved": key, "transition_id": transition_id}

    def assignable_users(self, key, query):
        return self._req("GET", "/rest/api/3/user/assignable/search", params={"issueKey": key, "query": query, "maxResults": 100})

    def assign(self, key, account_id):
        self._req("PUT", f"/rest/api/3/issue/{identifier(key)}/assignee", json={"accountId": account_id})
        return {"issue": key, "assignee": account_id}

    def link_types(self):
        return self._req("GET", "/rest/api/3/issueLinkType").get("issueLinkTypes", [])

    def link(self, inward, outward, link_type):
        self._req("POST", "/rest/api/3/issueLink", json={"type": {"id": link_type},
                  "inwardIssue": {"key": inward}, "outwardIssue": {"key": outward}})
        return {"inward": inward, "outward": outward, "type_id": link_type}

    def unlink(self, link_id):
        self._req("DELETE", f"/rest/api/3/issueLink/{identifier(link_id)}")
        return {"deleted_link": str(link_id)}

    def comment_edit(self, key, comment_id, body):
        return self._req("PUT", f"/rest/api/3/issue/{identifier(key)}/comment/{identifier(comment_id)}", json={"body": adf(body)})

    def comment_delete(self, key, comment_id):
        self._req("DELETE", f"/rest/api/3/issue/{identifier(key)}/comment/{identifier(comment_id)}")
        return {"deleted_comment": str(comment_id), "issue": key}

    def attachment_info(self, attachment_id):
        return self._req("GET", f"/rest/api/3/attachment/{identifier(attachment_id)}")

    def attachment_upload(self, key, paths):
        settings = self._req("GET", "/rest/api/3/attachment/meta")
        if not settings.get("enabled"):
            raise ValueError("Attachments are disabled on this Jira site.")
        limit = min(settings.get("uploadLimit", 50 * 1024 * 1024), 50 * 1024 * 1024)
        with ExitStack() as stack:
            files = []
            total_size = 0
            for name in paths:
                path = Path(name)
                if not path.is_file() or not 0 < path.stat().st_size <= limit:
                    raise ValueError(f"Attachment must be a nonempty file no larger than {limit} bytes: {path}")
                total_size += path.stat().st_size
                if total_size > 50 * 1024 * 1024:
                    raise ValueError("A single upload is limited to 50 MiB across all files.")
                files.append(("file", (path.name, stack.enter_context(path.open("rb")), "application/octet-stream")))
            return self._req("POST", f"/rest/api/3/issue/{identifier(key)}/attachments", files=files,
                             headers={"X-Atlassian-Token": "no-check", "Content-Type": None})

    def attachment_download(self, attachment_id, destination):
        metadata = self.attachment_info(attachment_id)
        size = metadata.get("size")
        if not isinstance(size, int) or not 0 <= size <= 250 * 1024 * 1024:
            raise ValueError("Invalid attachment size or attachment exceeds the 250 MiB download limit.")
        name = Path(metadata.get("filename", "attachment").replace("\\", "/")).name
        if name in ("", ".", ".."):
            raise ValueError("Jira returned an unsafe attachment filename.")
        output = Path(destination)
        if output.is_dir():
            output = output / name
        if output.exists():
            raise ValueError(f"Destination already exists: {output}")
        response = self.s.get(self.site + f"/rest/api/3/attachment/content/{identifier(attachment_id)}",
                              params={"redirect": "false"}, stream=True, timeout=(10, 60), allow_redirects=False)
        temporary = None
        try:
            if response.status_code != 200:
                raise JiraError("GET", "/attachment/content", response.status_code, "Attachment download failed.")
            fd, temporary = tempfile.mkstemp(prefix=".jira-attachment-", dir=output.parent)
            received = 0
            with os.fdopen(fd, "wb") as stream:
                for chunk in response.iter_content(1024 * 1024):
                    received += len(chunk)
                    if received > size:
                        raise ValueError("Attachment exceeds its declared size.")
                    stream.write(chunk)
            if received != size:
                raise ValueError("Attachment download was interrupted; no partial destination was retained.")
            # Hard-link creation fails atomically if another download created the destination.
            os.link(temporary, output)
            return {"attachment_id": str(attachment_id), "file": str(output.absolute()), "bytes": received}
        finally:
            response.close()
            if temporary is not None:
                os.unlink(temporary)

    def attachment_delete(self, attachment_id):
        self._req("DELETE", f"/rest/api/3/attachment/{identifier(attachment_id)}")
        return {"deleted_attachment": str(attachment_id)}

    # -- boards (Agile API; no rename/columns write endpoints exist) --------------
    def boards(self, project=None, name=None, limit=50, all_results=False):
        params = {}
        if project:
            params["projectKeyOrId"] = project
        if name:
            params["name"] = name
        return self._offset("/rest/agile/1.0/board", params=params, limit=limit, all_results=all_results)

    def board_get(self, board_id):
        return self._req("GET", f"/rest/agile/1.0/board/{board_id}")

    def board_issues(self, board_id, jql="", max_results=50, all_results=False, fields=None):
        params: dict = {"maxResults": max_results}
        if jql:
            params["jql"] = jql
        if fields:
            params["fields"] = fields
        return self._offset(f"/rest/agile/1.0/board/{board_id}/issue", "issues", params=params,
                            limit=max_results, all_results=all_results)

    def board_create(self, name, project, jql=None, filter_id=None, btype="scrum"):
        if filter_id is None:
            f = self._req("POST", "/rest/api/3/filter",
                          json={"name": name,
                                "jql": jql or project_jql(project) + " ORDER BY Rank ASC",
                                "description": f"Filter for board {name}"})
            filter_id = int(f["id"])
        return self._req("POST", "/rest/agile/1.0/board",
                         json={"name": name, "type": btype, "filterId": filter_id,
                               "location": {"type": "project",
                                            "projectKeyOrId": project}})

    def board_feature(self, board_id, feature, enabling: bool):
        return self._req("PUT", f"/rest/agile/1.0/board/{board_id}/features",
                         json={"boardId": int(board_id), "enabling": enabling,
                               "feature": feature})

    # -- sprints ------------------------------------------------------------------
    def sprints(self, board_id, state="active,future", limit=50, all_results=False):
        return self._offset(f"/rest/agile/1.0/board/{board_id}/sprint", params={"state": state},
                            limit=limit, all_results=all_results)

    def sprint_create(self, board_id, name, goal=""):
        return self._req("POST", "/rest/agile/1.0/sprint",
                         json={"name": name, "goal": goal or None,
                               "originBoardId": int(board_id)})

    def sprint_set_state(self, sprint_id, state: str):
        return self._req("POST", f"/rest/agile/1.0/sprint/{sprint_id}",
                         json={"state": state})

    def sprint_add_issues(self, sprint_id, keys):
        return self._req("POST", f"/rest/agile/1.0/sprint/{sprint_id}/issue",
                         json={"issues": list(keys)})
