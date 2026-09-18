"""jsup — friendly Jira Cloud CLI (official REST APIs + Rich TUI).

Global flags: --project/-p, --json, --site/--email/--token overrides.
Config lives in ~/.config/jsup/config.json (see: jsup config init).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import webbrowser
from pathlib import Path

from . import ui
from .client import Jira, JiraError
from .config import get_config, init_config, show_config

EXAMPLES = """examples:
  jsup config init                 first-time setup wizard
  jsup me                          check auth
  jsup open -p RP                  open support tickets
  jsup intake -p RP                guided callback-task wizard
  jsup issue-show RP-21
  jsup issue-move RP-21            pick transition interactively
  jsup comment-add RP-21 -m "On it"
  jsup sprint-list --board 1525
  jsup browse RP-21                open in browser
"""


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--site"); common.add_argument("--email")
    common.add_argument("--token")
    common.add_argument("--project", "-p", help="default project key")
    common.add_argument("--json", action="store_true", help="raw JSON (for scripts)")
    p = argparse.ArgumentParser(prog="jsup",
                                description="Friendly Jira Cloud CLI (official REST APIs)",
                                epilog=EXAMPLES,
                                parents=[common],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    S = lambda *a, **k: sub.add_parser(*a, parents=[common], **k)

    c = S("config", help="setup & inspect local config")
    c.add_argument("action", choices=["init", "show"])

    S("me", help="show authenticated user")
    S("dashboard", help="boards + open-ticket counts (default view)")

    c = S("project-list", help="list projects")
    c = S("project-show", help="show project details")
    c.add_argument("key", nargs="?")

    c = S("issue-create", help="create an issue")
    c.add_argument("--summary", "-s", required=True)
    c.add_argument("--desc", "-d", default="")
    c.add_argument("--desc-file", help="read description from file")
    c.add_argument("--type", "-t", default="Task")
    c.add_argument("--priority"); c.add_argument("--assignee")
    c.add_argument("--label", action="append", default=[])
    c.add_argument("--component", action="append", default=[])

    c = S("intake", help="guided callback/support-task wizard")
    c.add_argument("--name", help="client name")
    c.add_argument("--issue", help="issue as reported")
    c.add_argument("--callback", default="not specified", help="requested callback time")
    c.add_argument("--type", default="Task")
    c.add_argument("--priority", default="High")

    c = S("open", help="list open tickets")
    c.add_argument("--jql", default="", help="extra JQL, e.g. 'priority = High'")
    c.add_argument("--max", type=int, default=50)

    c = S("issue-show", help="show one issue")
    c.add_argument("key")

    c = S("issue-move", help="transition issue (interactive without --to)")
    c.add_argument("key")
    c.add_argument("--to", help="transition name or id")

    c = S("transitions", help="list available transitions")
    c.add_argument("key")

    c = S("issue-delete", help="permanently delete an issue (asks first)")
    c.add_argument("key")
    c.add_argument("--yes", action="store_true", help="skip confirmation")

    c = S("comment-add", help="add comment")
    c.add_argument("key"); c.add_argument("-m", "--message", required=True)

    c = S("comment-list", help="list comments")
    c.add_argument("key")

    c = S("board-list", help="list boards")
    c.add_argument("--jql-project", help="filter by project key")

    c = S("board-create", help="create filter + scrum/kanban board")
    c.add_argument("--name", required=True)
    c.add_argument("--jql", help="board filter JQL")
    c.add_argument("--filter-id", type=int)
    c.add_argument("--type", default="scrum", choices=["scrum", "kanban"])

    c = S("board-issues", help="list issues on a board")
    c.add_argument("board_id", type=int)
    c.add_argument("--jql", default="")
    c.add_argument("--max", type=int, default=50)

    c = S("board-feature", help="enable/disable a board feature")
    c.add_argument("board_id", type=int)
    c.add_argument("--feature", required=True,
                   help="e.g. jsw.agility.reports (team-managed boards only)")
    g = c.add_mutually_exclusive_group(required=True)
    g.add_argument("--enable", action="store_true")
    g.add_argument("--disable", action="store_true")

    c = S("sprint-list", help="list sprints on a board")
    c.add_argument("--board", type=int, required=True)
    c.add_argument("--state", default="active,future")

    c = S("sprint-create", help="create a sprint on a board")
    c.add_argument("--board", type=int, required=True)
    c.add_argument("--name", required=True)
    c.add_argument("--goal", default="")

    c = S("sprint-state", help="start/close a sprint")
    c.add_argument("sprint_id", type=int)
    c.add_argument("state", choices=["active", "closed", "future"])

    c = S("sprint-add", help="move issues into a sprint")
    c.add_argument("sprint_id", type=int)
    c.add_argument("keys", nargs="+")

    c = S("component-list", help="list project components")
    c = S("component-create", help="create a project component")
    c.add_argument("--name", required=True)
    c.add_argument("--desc", default="")

    c = S("browse", help="open issue/board in browser")
    c.add_argument("target", help="issue key or board:<id>")
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    if not args.cmd:
        args.cmd = "dashboard"

    if args.cmd == "config":
        init_config() if args.action == "init" else show_config()
        return

    cfg = get_config(args)
    j = Jira(cfg["site"], cfg["email"], cfg["token"])
    as_json = args.json
    proj = lambda k=None: k or cfg["project"] or sys.exit("Pass -p KEY or set a default: jsup config init")

    def show(data, render):
        ui.dump_json(data) if as_json else ui.emit(data, render)

    try:
        import contextlib
        spin = ui.console.status("Talking to Jira…", spinner="dots")
        with spin if not as_json else contextlib.nullcontext():
            cmd = args.cmd
            if cmd == "me":
                data = j.me()
            elif cmd == "dashboard":
                data = None
            elif cmd == "project-list":
                data = j.projects()
            elif cmd == "project-show":
                data = j.project_get(proj(args.key))
            elif cmd in ("issue-create", "intake"):
                if cmd == "intake":
                    name = args.name or input("Client name: ").strip()
                    issue = args.issue or input("Issue as reported: ").strip()
                    if not (name and issue):
                        sys.exit("intake needs a name and an issue.")
                    summary, desc = f"Callback: {name} — {issue}", (
                        f"Client: {name}\nIssue as reported: {issue}\n"
                        f"Requested callback: {args.callback}\n"
                        "Source: jsup intake. Assumed open — team to review & update.")
                    data = j.issue_create(proj(), summary, desc, args.type,
                                          args.priority, ["callback"], ["ops-runbook"])
                else:
                    desc = Path(args.desc_file).read_text() if args.desc_file else args.desc
                    data = j.issue_create(proj(), args.summary, desc, args.type,
                                          args.priority, args.label, args.component,
                                          args.assignee)
            elif cmd == "open":
                data = j.open_tickets(proj(), args.jql, args.max)
            elif cmd == "issue-show":
                data = j.issue_get(args.key)
            elif cmd == "transitions":
                data = j.transitions(args.key)
            elif cmd == "issue-move":
                data = j.move(args.key, args.to) if args.to else None
            elif cmd == "issue-delete":
                data = {"deleted": args.key}
            elif cmd == "comment-add":
                data = j.comment_add(args.key, args.message)
            elif cmd == "comment-list":
                data = j.comments(args.key)
            elif cmd == "board-list":
                data = j.boards(project=args.jql_project)
            elif cmd == "board-create":
                data = j.board_create(args.name, proj(), args.jql, args.filter_id, args.type)
            elif cmd == "board-issues":
                data = j.board_issues(args.board_id, args.jql, args.max)
            elif cmd == "board-feature":
                data = j.board_feature(args.board_id, args.feature, args.enable)
            elif cmd == "sprint-list":
                data = j.sprints(args.board, args.state)
            elif cmd == "sprint-create":
                data = j.sprint_create(args.board, args.name, args.goal)
            elif cmd == "sprint-state":
                data = j.sprint_set_state(args.sprint_id, args.state)
            elif cmd == "sprint-add":
                data = j.sprint_add_issues(args.sprint_id, args.keys)
            elif cmd == "component-list":
                data = j.components(proj())
            elif cmd == "component-create":
                data = j.component_create(proj(), args.name, args.desc)
            elif cmd == "browse":
                data = None
            else:
                sys.exit(f"unknown command {cmd}")
    except JiraError as e:
        hint = ""
        if e.status == 403:
            hint = " (permission denied — project/global admin may be required)"
        elif e.status == 404:
            hint = " (not found — check the key/id)"
        ui.err_console.print(f"[red]Error:[/] {e}{hint}")
        sys.exit(1)

    # interactive follow-ups run after the spinner stops
    if args.cmd == "dashboard":
        _dashboard(j, cfg, as_json)
    elif args.cmd == "issue-move" and not args.to:
        trs = j.transitions(args.key).get("transitions", [])
        if not trs:
            sys.exit("No transitions available.")
        i = ui.pick("Move to", [f'{t["name"]} [{t["id"]}]' for t in trs])
        show(j.move(args.key, trs[i]["id"]),
             lambda d: ui.console.print(f"Moved {d['moved']} → [green]{d['to']}[/]"))
    elif args.cmd == "issue-delete":
        if not args.yes and not ui.confirm(f"Permanently delete {args.key}?"):
            sys.exit("Aborted.")
        show(j.issue_delete(args.key),
             lambda d: ui.console.print(f"[green]Deleted {args.key}[/]"))
    elif args.cmd == "browse":
        url = (f"{cfg['site']}/browse/{args.target}" if not args.target.startswith("board:")
               else f"{cfg['site']}/jira/software/c/projects/{proj()}/boards/{args.target[6:]}")
        ui.console.print(f"Opening {url}")
        webbrowser.open(url)
    elif args.cmd == "me":
        show(data, lambda d: ui.console.print(
            f"[green]✓[/] {d.get('displayName')} ({d.get('emailAddress')})"))
    elif args.cmd == "open":
        show(data, lambda d: ui.issues_table(d, f"Open — {proj()}"))
    elif args.cmd == "board-issues":
        show(data, lambda d: ui.issues_table(d, f"Board {args.board_id}"))
    elif args.cmd == "issue-show":
        show(data, ui.issue_panel)
    elif args.cmd == "comment-list":
        show(data, ui.comments_table)
    elif args.cmd == "board-list":
        show(data, ui.boards_table)
    elif args.cmd == "sprint-list":
        show(data, ui.sprints_table)
    elif args.cmd == "component-list":
        rows = data if isinstance(data, list) else []
        show(data, lambda d: ui.simple_table(f"Components — {proj()}",
              [{"name": c.get("name"), "desc": (c.get("description") or "")[:70]} for c in rows],
              ["name", "desc"]))
    elif args.cmd == "project-list":
        show(data, lambda d: ui.simple_table("Projects",
              [{"key": p["key"], "name": p.get("name", "")} for p in d],
              ["key", "name"]))
    else:
        show(data, lambda d: ui.console.print(f"[green]✓[/] {d}"))


def _dashboard(j: Jira, cfg: dict, as_json: bool) -> None:
    """Default view: open-ticket counts per known project + boards."""
    if as_json:
        ui.dump_json({"project": cfg.get("project"), "hint": "use open/board-list"})
        return
    ui.console.print(f"[bold]jsup[/] → {cfg['site']}  (default project: {cfg.get('project') or '-'})")
    for key in ["RP", "RD", "BUG"]:
        try:
            total = j.open_tickets(key, max_results=1).get("total", "?")
            ui.console.print(f"  {key}: [yellow]{total}[/] open")
        except JiraError:
            ui.console.print(f"  {key}: [dim]unreachable[/]")
    ui.console.print("[dim]Tip: jsup open -p RP · jsup intake -p RP · jsup --help[/]")


if __name__ == "__main__":
    main()
