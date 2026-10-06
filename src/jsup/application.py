"""Application operations shared by grouped commands and legacy aliases."""
from __future__ import annotations

from contextlib import nullcontext
import sys
import webbrowser
from pathlib import Path
from urllib.parse import quote

from . import config, ui
from .client import Jira, JiraError, project_jql


class CommandError(Exception):
    """An actionable input error, reported by the CLI entry point."""


def require_input(args, message: str) -> None:
    if args.no_input or not sys.stdin.isatty():
        raise CommandError(message)


def show_context(args, prog: str, include_help: bool = False) -> None:
    cfg = config.resolve_config(args)
    data = {"site": cfg["site"] or None, "project": cfg["project"] or None}
    if args.json:
        ui.dump_json(data)
    else:
        ui.console.print(f"{prog}: site={data['site'] or '(unset)'}  project={data['project'] or '(unset)'}",
                         markup=False)
        if include_help:
            ui.console.print(f"Try: {prog} --help · {prog} config init · {prog} issue list --open",
                             markup=False)


def _project(cfg: dict, key: str | None = None) -> str:
    result = key or cfg["project"]
    if not result:
        raise CommandError("Pass --project KEY or set a default with config init.")
    return result


def _open_browser(args) -> bool:
    """Browser-only operations need a site URL, not API credentials."""
    if args.cmd == "browse":
        if args.target.startswith("board:"):
            try:
                board_id = int(args.target[6:])
                if board_id < 1:
                    raise ValueError
            except ValueError:
                raise CommandError("Use board:<positive board ID>.") from None
            path = f"/secure/RapidBoard.jspa?rapidView={board_id}"
        else:
            path = f"/browse/{quote(args.target, safe='')}"
    elif args.cmd == "issue-show" and args.web:
        path = f"/browse/{quote(args.key, safe='')}"
    elif args.cmd == "board-show" and args.web:
        # Jira resolves the actual board location, without a project guess.
        path = f"/secure/RapidBoard.jspa?rapidView={args.board_id}"
    else:
        return False
    site = config.resolve_config(args)["site"]
    if not site:
        raise CommandError("Set JIRA_SITE or pass --site to open Jira in a browser.")
    url = site + path
    if not webbrowser.open(url):
        raise CommandError(f"Could not open a browser. Open this URL manually: {url}")
    if args.json:
        ui.dump_json({"url": url, "opened": True})
    else:
        ui.console.print(f"Opening {url}", markup=False)
    return True


def _prepare_intake(args) -> None:
    if not args.name or not args.issue:
        require_input(args, "intake needs --name and --issue when input is unavailable.")
    name = args.name or input("Client name: ").strip()
    issue = args.issue or input("Issue as reported: ").strip()
    if not (name and issue):
        raise CommandError("intake needs a name and an issue.")
    args.summary = f"Callback: {name} — {issue}"
    args.desc = (f"Client: {name}\nIssue as reported: {issue}\n"
                 f"Requested callback: {args.callback}\n"
                 "Source: jsup intake. Assumed open — team to review & update.")
    args.label, args.component, args.assignee = ["callback"], ["ops-runbook"], None


def _dashboard(j: Jira, args, cfg: dict) -> dict:
    keys = args.projects or ([cfg["project"]] if cfg["project"] else [])
    if not keys:
        raise CommandError("Select dashboard projects with --projects KEY ... or --project KEY.")
    rows = []
    for key in dict.fromkeys(keys):
        try:
            count = j.count_issues(project_jql(key) + " AND statusCategory != Done")["count"]
            rows.append({"project": key, "count": count, "approximate": True})
        except JiraError as error:
            if error.status in (401, 403):
                raise
            rows.append({"project": key, "count": None, "error": f"Jira returned HTTP {error.status}"})
    return {"site": cfg["site"], "projects": rows}


def _fetch(j: Jira, args, cfg: dict):
    project = lambda key=None: _project(cfg, key)
    cmd = args.cmd
    pagination = {}
    if getattr(args, "all", False):
        pagination["all_results"] = True
    if cmd in {"project-list", "board-list", "sprint-list", "comment-list"} and args.max != 50:
        pagination["limit"] = args.max
    if cmd == "dashboard":
        return _dashboard(j, args, cfg)
    if cmd in ("issue-create", "intake"):
        desc = (Path(args.desc_file).read_text() if cmd == "issue-create" and args.desc_file
                else args.desc)
        return j.issue_create(project(), args.summary, desc, args.type,
                              args.priority, args.label, args.component, args.assignee)
    if cmd == "issue-list":
        if args.jql:
            if args.open or args.project:
                raise CommandError("--jql is a complete query; omit --open and --project.")
            jql = args.jql
        else:
            jql = project_jql(project())
            if args.open:
                jql += " AND statusCategory != Done"
            jql += " ORDER BY updated DESC"
        return j.search(jql, args.max, **pagination)
    if cmd == "issue-move":
        return j.move(args.key, args.to)
    if cmd == "issue-delete":
        return j.issue_delete(args.key)
    operations = {
        "me": lambda: j.me(),
        "project-list": lambda: j.projects(**pagination),
        "project-show": lambda: j.project_get(project(args.key)),
        "open": lambda: j.open_tickets(project(), args.jql, args.max, **pagination),
        "issue-show": lambda: j.issue_get(args.key),
        "transitions": lambda: j.transitions(args.key),
        "comment-add": lambda: j.comment_add(args.key, args.message),
        "comment-list": lambda: j.comments(args.key, **pagination),
        "board-list": lambda: j.boards(project=(args.jql_project or
                                    (None if args.legacy else cfg["project"] or None)), **pagination),
        "board-show": lambda: j.board_get(args.board_id),
        "board-create": lambda: j.board_create(args.name, project(), args.jql, args.filter_id, args.type),
        "board-issues": lambda: j.board_issues(args.board_id, args.jql, args.max, **pagination),
        "board-feature": lambda: j.board_feature(args.board_id, args.feature, args.enable),
        "sprint-list": lambda: j.sprints(args.board, args.state, **pagination),
        "sprint-create": lambda: j.sprint_create(args.board, args.name, args.goal),
        "sprint-state": lambda: j.sprint_set_state(args.sprint_id, args.state),
        "sprint-add": lambda: j.sprint_add_issues(args.sprint_id, args.keys),
        "component-list": lambda: j.components(project()),
        "component-create": lambda: j.component_create(project(), args.name, args.desc),
    }
    return operations[cmd]()


def _render(data, args, cfg: dict, prog: str) -> None:
    if args.json:
        ui.dump_json(data)
        return
    cmd = args.cmd
    if cmd == "dashboard":
        ui.console.print(f"{prog} → {cfg['site']}", markup=False)
        for row in data["projects"]:
            value = (f"approximately {row['count']} open" if row["count"] is not None
                     else f"unavailable: {row['error']}")
            ui.console.print(f"  {row['project']}: {value}", markup=False)
    elif cmd == "me":
        ui.console.print(f"✓ {data.get('displayName')} ({data.get('emailAddress')})", markup=False)
    elif cmd in ("open", "issue-list"):
        ui.issues_table(data, "Open issues" if cmd == "open" or args.open else "Issues")
    elif cmd == "issue-show":
        ui.issue_panel(data)
    elif cmd == "board-issues":
        ui.issues_table(data, f"Board {args.board_id}")
    elif cmd == "comment-list":
        ui.comments_table(data)
    elif cmd == "board-list":
        ui.boards_table(data)
    elif cmd == "sprint-list":
        ui.sprints_table(data)
    elif cmd == "component-list":
        ui.simple_table("Components", [{"name": c.get("name"), "desc": c.get("description") or ""}
                                      for c in data], ["name", "desc"])
    elif cmd == "project-list":
        ui.simple_table("Projects", [{"key": p["key"], "name": p.get("name", "")} for p in data],
                        ["key", "name"])
    elif cmd == "issue-move":
        ui.console.print(f"Moved {data['moved']} → {data['to']}", markup=False)
    elif cmd == "issue-delete":
        ui.console.print(f"Deleted {args.key}", markup=False)
    else:
        ui.console.print(f"✓ {data}", markup=False)


def run(args, prog: str) -> None:
    if args.cmd == "config-init":
        require_input(args, "config init requires interactive input; use environment variables for scripts.")
        if args.json:
            raise CommandError("config init is interactive; omit --json.")
        config.init_config()
        return
    if args.cmd == "config-show":
        config.show_config(as_json=args.json)
        return
    if args.cmd == "context-show":
        show_context(args, prog)
        return
    if _open_browser(args):
        return
    if args.cmd == "dashboard" and args.json and prog == "jsup":
        cfg = config.resolve_config(args)
        ui.dump_json({"project": cfg["project"], "hint": "use open/board-list"})
        return
    if args.cmd == "issue-move" and not args.to:
        require_input(args, "Pass --to <transition name or ID> when input is unavailable.")
    if args.cmd == "issue-delete" and not args.yes:
        require_input(args, "Pass --yes to confirm deletion when input is unavailable.")
        if not ui.confirm(f"Permanently delete {args.key}?"):
            raise CommandError("Aborted.")
    if args.cmd == "intake":
        _prepare_intake(args)
    cfg = config.resolve_config(args)
    if not (cfg["site"] and cfg["email"] and cfg["token"]):
        raise CommandError(f"Not configured yet. Run: {prog} config init")
    j = Jira(cfg["site"], cfg["email"], cfg["token"])
    try:
        if args.cmd == "issue-move" and not args.to:
            transitions = j.transitions(args.key).get("transitions", [])
            if not transitions:
                raise CommandError("No transitions available.")
            selection = ui.pick("Move to", [f"{t['name']} [{t['id']}]" for t in transitions])
            args.to = transitions[selection]["id"]
        with ui.err_console.status("Talking to Jira…", spinner="dots") if not args.json else nullcontext():
            data = _fetch(j, args, cfg)
        _render(data, args, cfg, prog)
    finally:
        j.close()
