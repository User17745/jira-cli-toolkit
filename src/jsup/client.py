"""Thin wrapper over the official Jira Cloud REST APIs (v3 + Agile 1.0)."""
from __future__ import annotations

import json
import time
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

    def _req(self, method: str, path: str, **kw):
        safe = kw.pop("retry_safe", method in ("GET", "HEAD"))
        kw.setdefault("timeout", (10, 30))
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
                    time.sleep(delay)
                    continue
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

    def board_issues(self, board_id, jql="", max_results=50, all_results=False):
        params: dict = {"maxResults": max_results}
        if jql:
            params["jql"] = jql
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
