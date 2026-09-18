"""Thin wrapper over the official Jira Cloud REST APIs (v3 + Agile 1.0)."""
from __future__ import annotations

import requests


class JiraError(Exception):
    def __init__(self, method: str, path: str, status: int, body: str):
        self.method, self.path, self.status, self.body = method, path, status, body
        super().__init__(f"{method} {path} -> {status}: {body[:500]}")


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
        r = self.s.request(method, self.site + path, **kw)
        if r.status_code in (200, 201):
            return r.json() if r.text else {}
        if r.status_code == 204:
            return {}
        raise JiraError(method, path, r.status_code, r.text)

    # -- identity / projects -------------------------------------------------
    def me(self): return self._req("GET", "/rest/api/3/myself")
    def projects(self): return self._req("GET", "/rest/api/3/project")
    def project_get(self, key): return self._req("GET", f"/rest/api/3/project/{key}")

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
               fields="summary,status,assignee,priority,updated,components,labels"):
        try:
            return self._req("GET", "/rest/api/3/search/jql",
                             params={"jql": jql, "maxResults": max_results,
                                     "fields": fields})
        except JiraError as e:
            if e.status not in (404, 410):
                raise
            return self._req("GET", "/rest/api/3/search",
                             params={"jql": jql, "maxResults": max_results,
                                     "fields": fields})

    def open_tickets(self, project, extra="", max_results=50):
        jql = f"project = {project} AND statusCategory != Done"
        if extra:
            jql += f" AND ({extra})"
        return self.search(jql + " ORDER BY updated DESC", max_results)

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

    def comments(self, key):
        return self._req("GET", f"/rest/api/3/issue/{key}/comment")

    # -- components ---------------------------------------------------------------
    def components(self, project):
        return self._req("GET", f"/rest/api/3/project/{project}/components")

    def component_create(self, project, name, description=""):
        return self._req("POST", "/rest/api/3/component",
                         json={"name": name, "description": description,
                               "project": project})

    # -- boards (Agile API; no rename/columns write endpoints exist) --------------
    def boards(self, project=None, name=None):
        params = {}
        if project:
            params["projectKeyOrId"] = project
        if name:
            params["name"] = name
        return self._req("GET", "/rest/agile/1.0/board", params=params)

    def board_issues(self, board_id, jql="", max_results=50):
        params: dict = {"maxResults": max_results}
        if jql:
            params["jql"] = jql
        return self._req("GET", f"/rest/agile/1.0/board/{board_id}/issue",
                         params=params)

    def board_create(self, name, project, jql=None, filter_id=None, btype="scrum"):
        if filter_id is None:
            f = self._req("POST", "/rest/api/3/filter",
                          json={"name": name,
                                "jql": jql or f"project = {project} ORDER BY Rank ASC",
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
    def sprints(self, board_id, state="active,future"):
        return self._req("GET", f"/rest/agile/1.0/board/{board_id}/sprint",
                         params={"state": state, "maxResults": 50})

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
