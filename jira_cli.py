#!/usr/bin/env python3
"""jira-support-cli — support tickets from the terminal using official Jira Cloud REST APIs.

Uses only:
  - Jira Cloud platform API v3 (/rest/api/3/...)
  - Jira Software Agile API  (/rest/agile/1.0/...) for boards (optional)

Auth: Basic auth with email + API token (https://id.atlassian.com/manage-profile/security/api-tokens)

Config via env (or .env in this dir / cwd):
  JIRA_SITE=https://YOUR-site.atlassian.net
  JIRA_EMAIL=you@example.com
  JIRA_API_TOKEN=xxxx
  JIRA_PROJECT=SUP   (optional default)

Examples:
  python jira_cli.py me
  python jira_cli.py project-create --key SUP --name "Support" --lead-me
  python jira_cli.py issue-create --project SUP --summary "Login fails" --desc "steps..." --type Task
  python jira_cli.py open --project SUP
  python jira_cli.py issue-show SUP-123
  python jira_cli.py issue-move SUP-123 --to "In Progress"
  python jira_cli.py comment-add SUP-123 -m "Looking into it"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Missing dependency: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


# ---------- config ----------

def load_dotenv() -> None:
    for p in (Path(__file__).parent / ".env", Path.cwd() / ".env"):
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_cfg(args) -> dict:
    load_dotenv()
    site = (args.site or os.getenv("JIRA_SITE", "")).rstrip("/")
    email = args.email or os.getenv("JIRA_EMAIL", "")
    token = args.token or os.getenv("JIRA_API_TOKEN", "")
    if not site or not email or not token:
        print("Missing JIRA_SITE / JIRA_EMAIL / JIRA_API_TOKEN.\n"
              "Set env or .env, or pass --site/--email/--token. See .env.example",
              file=sys.stderr)
        sys.exit(2)
    return {"site": site, "email": email, "token": token,
            "project": args.project or os.getenv("JIRA_PROJECT", "")}


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


# ---------- client ----------

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
        raise SystemExit(f"{method} {path} -> {r.status_code}: {r.text[:1000]}")

    # me / project
    def me(self): return self._req("GET", "/rest/api/3/myself")

    def project_create(self, key, name, project_type="software",
                       template="com.pyxis.greenhopper.jira:gh-scrum-template",
                       lead=None, desc="Support queue managed from CLI"):
        body = {"key": key, "name": name, "projectTypeKey": project_type,
                "projectTemplateKey": template, "description": desc,
                "leadAccountId": lead, "assigneeType": "PROJECT_LEAD"}
        return self._req("POST", "/rest/api/3/project", json=body)

    def project_get(self, key): return self._req("GET", f"/rest/api/3/project/{key}")

    # issues
    def issue_create(self, project, summary, desc="", itype="Task",
                     priority=None, labels=(), assignee=None):
        fields: dict = {"project": {"key": project}, "summary": summary,
                        "description": adf(desc), "issuetype": {"name": itype}}
        if priority: fields["priority"] = {"name": priority}
        if labels: fields["labels"] = list(labels)
        if assignee: fields["assignee"] = {"accountId": assignee}
        return self._req("POST", "/rest/api/3/issue", json={"fields": fields})

    def issue_get(self, key):
        return self._req("GET", f"/rest/api/3/issue/{key}")

    def search(self, jql, max_results=50, fields="summary,status,assignee,priority,updated"):
        # New endpoint first, old fallback
        try:
            return self._req("GET", "/rest/api/3/search/jql",
                             params={"jql": jql, "maxResults": max_results,
                                     "fields": fields})
        except SystemExit as e:
            if "410" not in str(e) and "404" not in str(e):
                raise
            return self._req("GET", "/rest/api/3/search",
                             params={"jql": jql, "maxResults": max_results,
                                     "fields": fields})

    def open_tickets(self, project, extra="", max_results=50):
        jql = f"project = {project} AND statusCategory != Done"
        if extra: jql += f" AND ({extra})"
        jql += " ORDER BY updated DESC"
        return self.search(jql, max_results)

    # workflow / status
    def transitions(self, key):
        return self._req("GET", f"/rest/api/3/issue/{key}/transitions")

    def move(self, key, to: str):
        trs = self.transitions(key).get("transitions", [])
        match = next((t for t in trs if t["id"] == to or
                      t["name"].lower() == to.lower()), None)
        if not match:
            avail = ", ".join(f'{t["name"]} [{t["id"]}]' for t in trs)
            raise SystemExit(f"No transition '{to}'. Available: {avail}")
        self._req("POST", f"/rest/api/3/issue/{key}/transitions",
                  json={"transition": {"id": match["id"]}})
        return {"moved": key, "to": match["name"]}

    # comments
    def comment_add(self, key, body):
        return self._req("POST", f"/rest/api/3/issue/{key}/comment",
                         json={"body": adf(body)})

    def comments(self, key):
        return self._req("GET", f"/rest/api/3/issue/{key}/comment")

    # boards (Jira Software Agile API — no update/rename endpoint exists)
    def boards(self, project=None, name=None):
        params = {}
        if project: params["projectKeyOrId"] = project
        if name: params["name"] = name
        return self._req("GET", "/rest/agile/1.0/board", params=params)

    def board_issues(self, board_id, jql="", max_results=50):
        params: dict = {"maxResults": max_results}
        if jql: params["jql"] = jql
        return self._req("GET", f"/rest/agile/1.0/board/{board_id}/issue",
                         params=params)

    def board_create(self, name, project, jql=None, filter_id=None,
                     btype="scrum"):
        if filter_id is None:
            f = self._req("POST", "/rest/api/3/filter",
                          json={"name": name,
                                "jql": jql or f"project = {project} ORDER BY Rank ASC",
                                "description": f"Filter for board {name}"})
            filter_id = int(f["id"])
        return self._req("POST", "/rest/agile/1.0/board",
                         json={"name": name, "type": btype,
                               "filterId": filter_id,
                               "location": {"type": "project",
                                            "projectKeyOrId": project}})

    def board_feature(self, board_id, feature, enabling: bool):
        # No official rename/columns write API exists; feature toggles do.
        return self._req("PUT", f"/rest/agile/1.0/board/{board_id}/features",
                         json={"boardId": int(board_id), "enabling": enabling,
                               "feature": feature})


# ---------- output ----------

def out(data, as_json: bool, fmt=None):
    if as_json or fmt is None:
        print(json.dumps(data, indent=2))
    else:
        fmt(data)


def fmt_issues(data):
    issues = data.get("issues", [])
    print(f"{len(issues)} issue(s) (total={data.get('total', '?')})")
    for i in issues:
        f = i.get("fields", {})
        st = (f.get("status") or {}).get("name", "?")
        asg = (f.get("assignee") or {}).get("displayName", "-")
        print(f"- {i['key']} [{st}] {f.get('summary','')} (assignee={asg})")


def fmt_issue(d):
    f = d.get("fields", {})
    print(f"{d.get('key')}: {f.get('summary','')}")
    print(f"  status={ (f.get('status') or {}).get('name') }  "
          f"type={ (f.get('issuetype') or {}).get('name') }  "
          f"priority={ (f.get('priority') or {}).get('name') }")
    desc = f.get("description")
    if desc: print(f"  desc: {adf_to_text(desc)[:500]}")


def fmt_comments(d):
    for c in d.get("comments", []):
        author = (c.get("author") or {}).get("displayName", "?")
        print(f"- [{c.get('id')}] {author}: {adf_to_text(c.get('body'))[:300]}")


# ---------- cli ----------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Jira support-ticket CLI (official REST APIs)")
    p.add_argument("--site"); p.add_argument("--email"); p.add_argument("--token")
    p.add_argument("--project", "-p", help="default project key")
    p.add_argument("--json", action="store_true", help="raw JSON output")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("me", help="show authenticated user")

    c = sub.add_parser("project-create", help="create a new Jira project")
    c.add_argument("--key", required=True); c.add_argument("--name", required=True)
    c.add_argument("--type", default="software",
                   choices=["software", "service_desk", "business"])
    c.add_argument("--template",
                   default="com.pyxis.greenhopper.jira:gh-scrum-template",
                   help="for JSM use e.g. com.atlassian.servicedesk:itil-v2-service-desk-template")
    c.add_argument("--lead", help="lead accountId (default: --lead-me)")
    c.add_argument("--lead-me", action="store_true")
    c.add_argument("--desc", default="Support queue managed from CLI")

    c = sub.add_parser("project-show", help="show project details")
    c.add_argument("key", nargs="?")

    c = sub.add_parser("issue-create", help="create support ticket")
    c.add_argument("--summary", "-s", required=True)
    c.add_argument("--desc", "-d", default="")
    c.add_argument("--desc-file", help="read description from file")
    c.add_argument("--type", "-t", default="Task")
    c.add_argument("--priority"); c.add_argument("--assignee")
    c.add_argument("--label", action="append", default=[])

    c = sub.add_parser("open", help="list all open tickets")
    c.add_argument("--jql", default="", help="extra JQL, e.g. 'priority = High'")
    c.add_argument("--max", type=int, default=50)

    c = sub.add_parser("issue-show", help="show one ticket")
    c.add_argument("key")

    c = sub.add_parser("issue-move", help="transition ticket to new status")
    c.add_argument("key"); c.add_argument("--to", required=True,
                   help="transition name or id (run without --to to list)")

    c = sub.add_parser("transitions", help="list available transitions")
    c.add_argument("key")

    c = sub.add_parser("comment-add", help="add comment to ticket")
    c.add_argument("key"); c.add_argument("-m", "--message", required=True)

    c = sub.add_parser("comment-list", help="list comments")
    c.add_argument("key")

    c = sub.add_parser("board-list", help="list boards (Agile API)")
    c.add_argument("--jql-project", help="filter by project key")

    c = sub.add_parser("board-create", help="create filter + scrum/kanban board")
    c.add_argument("--name", required=True)
    c.add_argument("--jql", help="board filter JQL (default: project = KEY ORDER BY Rank)")
    c.add_argument("--filter-id", type=int)
    c.add_argument("--type", default="scrum", choices=["scrum", "kanban"])

    c = sub.add_parser("board-issues", help="list issues on a board")
    c.add_argument("board_id", type=int)
    c.add_argument("--jql", default="")
    c.add_argument("--max", type=int, default=50)

    c = sub.add_parser("board-feature", help="enable/disable a board feature (Agile API)")
    c.add_argument("board_id", type=int)
    c.add_argument("--feature", required=True,
                   help="e.g. jsw.agility.reports, jsw.agility.sprints, jsw.agility.backlog")
    group = c.add_mutually_exclusive_group(required=True)
    group.add_argument("--enable", action="store_true")
    group.add_argument("--disable", action="store_true")
    return p


def main():
    args = build_parser().parse_args()
    cfg = get_cfg(args)
    j = Jira(cfg["site"], cfg["email"], cfg["token"])
    proj = lambda k=None: k or cfg["project"] or sys.exit("Pass --project KEY")

    if args.cmd == "me":
        out(j.me(), args.json)
    elif args.cmd == "project-create":
        lead = args.lead or (j.me()["accountId"] if args.lead_me or True else None)
        out(j.project_create(args.key, args.name, args.type, args.template, lead, args.desc), args.json)
    elif args.cmd == "project-show":
        out(j.project_get(proj(args.key)), args.json)
    elif args.cmd == "issue-create":
        desc = Path(args.desc_file).read_text() if args.desc_file else args.desc
        out(j.issue_create(proj(), args.summary, desc, args.type,
                           args.priority, args.label, args.assignee), args.json)
    elif args.cmd == "open":
        out(j.open_tickets(proj(), args.jql, args.max), args.json, fmt_issues)
    elif args.cmd == "issue-show":
        out(j.issue_get(args.key), args.json, fmt_issue)
    elif args.cmd == "transitions":
        out(j.transitions(args.key), args.json)
    elif args.cmd == "issue-move":
        out(j.move(args.key, args.to), args.json)
    elif args.cmd == "comment-add":
        out(j.comment_add(args.key, args.message), args.json)
    elif args.cmd == "comment-list":
        out(j.comments(args.key), args.json, fmt_comments)
    elif args.cmd == "board-list":
        out(j.boards(project=args.jql_project), args.json,
            lambda d: [print(f"- {b['id']} [{b['type']}] {b['name']}")
                       for b in d.get("values", [])])
    elif args.cmd == "board-create":
        out(j.board_create(args.name, proj(), args.jql, args.filter_id,
                           args.type), args.json)
    elif args.cmd == "board-issues":
        out(j.board_issues(args.board_id, args.jql, args.max),
            args.json, fmt_issues)
    elif args.cmd == "board-feature":
        out(j.board_feature(args.board_id, args.feature, args.enable),
            args.json)

if __name__ == "__main__":
    main()
