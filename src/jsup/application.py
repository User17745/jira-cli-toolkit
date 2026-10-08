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
    if args.no_input or args.json or not sys.stdin.isatty():
        raise CommandError(message)


def show_context(args, prog: str, include_help: bool = False) -> None:
    cfg = config.resolve_config(args, read_secret=False)
    data = {"site": cfg["site"] or None, "project": cfg["project"] or None}
    if cfg.get("profile"):
        data.update(profile=cfg["profile"], board=cfg.get("board"))
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
    site = config.resolve_config(args, read_secret=False)["site"]
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
    from .templates import load, render
    values = render(load("callback"), {"name": name, "issue": issue, "callback": args.callback})
    args.summary, args.desc = values["summary"], values["description"]
    args.label, args.component, args.assignee = values["labels"], values["components"], None



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
    if cmd in {"sprint-list", "sprint-create"} and not args.board:
        args.board = cfg.get("board")
        if not args.board:
            raise CommandError("Pass --board ID or select a default with context use --board ID.")
    pagination = {}
    if getattr(args, "all", False):
        pagination["all_results"] = True
    if cmd in {"project-list", "board-list", "sprint-list", "comment-list"} and args.max != 50:
        pagination["limit"] = args.max
    if cmd == "dashboard":
        return _dashboard(j, args, cfg)
    if cmd in ("issue-create", "intake"):
        if cmd == "issue-create" and not args.legacy:
            from .fields import create
            return create(j, args, cfg)
        desc = (Path(args.desc_file).read_text() if cmd == "issue-create" and args.desc_file
                else args.desc)
        return j.issue_create(project(), args.summary, desc, args.type,
                              args.priority, args.label, args.component, args.assignee)
    if cmd == "issue-list":
        from .maintenance import issue_list
        return issue_list(j, args, cfg)
    if cmd in {"issue-edit", "issue-assign", "issue-unassign", "issue-link", "issue-unlink", "comment-add", "comment-edit", "comment-delete", "attachment-list", "attachment-upload", "attachment-download", "attachment-delete"}:
        from .maintenance import handle
        return handle(j, args, cfg)
    if cmd == "template-validate":
        from . import fields, templates
        from types import SimpleNamespace
        creation = SimpleNamespace(**{**vars(args), "summary": None, "desc": None, "desc_file": None,
            "editor": False, "priority": None, "assignee": None, "label": [], "component": [],
            "parent": None, "field": [], "fields_file": None})
        templates.apply(creation, validating=True)
        fields.prepare_create(j, creation, cfg)
        return {"valid": True, "template": args.template, "project": cfg["project"], "type": creation.type}
    if cmd == "issue-move":
        if not args.legacy:
            from .fields import transition
            return transition(j, args, cfg)
        return j.move(args.key, args.to)
    if cmd in {"project-types", "project-fields", "project-statuses"}:
        from .fields import cached, choose
        selected = project(args.key)
        if cmd == "project-statuses":
            return j.project_statuses(selected)
        types = cached(cfg, selected, "types", lambda: j.issue_types(selected), args.refresh)
        if cmd == "project-types":
            return types
        issue_type = choose(types, args.type, "--type")
        return cached(cfg, selected, "create:" + issue_type["id"],
                      lambda: j.create_fields(selected, issue_type["id"]), args.refresh)
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
    if args.csv:
        ui.csv_data(data, args.columns)
        return
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
        ui.issues_table(data, "Open issues" if cmd == "open" or args.open else "Issues", args.columns)
    elif cmd == "issue-show":
        ui.issue_panel(data)
    elif cmd == "board-issues":
        ui.issues_table(data, f"Board {args.board_id}", args.columns)
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
    if args.json and args.csv:
        raise CommandError("Choose --json or --csv, not both.")
    if args.csv and args.cmd not in {"issue-list", "open", "board-list", "board-issues", "project-list", "comment-list", "sprint-list", "component-list", "project-types", "project-fields", "attachment-list"}:
        raise CommandError("--csv is supported only for list commands.")
    if args.cmd == "completion":
        from .completion import script
        print(script(args.shell, prog), end="")
        return
    if args.cmd in {"template-list", "template-show"}:
        from . import templates
        data = templates.list_templates() if args.cmd == "template-list" else templates.load(args.template)
        if args.json:
            ui.dump_json(data)
        else:
            ui.console.print(data, markup=False)
        return
    if args.cmd == "update":
        from . import update
        data = update.handle(args)
        if args.json:
            ui.dump_json(data)
        else:
            ui.console.print(data, markup=False)
        return
    if args.cmd in {"auth-login", "auth-status", "auth-logout", "config-migrate", "profile-list", "profile-use", "profile-remove", "context-use", "config-get", "config-set", "doctor"}:
        from . import auth
        data = auth.handle(args)
        if args.json:
            ui.dump_json(data)
        else:
            ui.console.print(data, markup=False)
        return
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
    if args.cmd in {"issue-unlink", "comment-delete", "attachment-delete"} and not args.yes:
        require_input(args, "Pass --yes to confirm deletion when input is unavailable.")
        if not ui.confirm("Permanently delete the selected item?"):
            raise CommandError("Aborted.")
    if args.cmd == "api":
        # No credential-replacement prompt or retried writes: the request is the caller's.
        from . import api
        if args.spec or args.path == "spec":
            # Discovery is public; no identity or credential store is touched.
            from . import api_spec
            api_spec.run(args)
            return
        if args.spec_action:
            raise api.invalid(f"Unexpected argument {args.spec_action!r}; pass query values with --query KEY=VALUE.")
        api.run(args, config.resolve_config(args))
        return
    if args.cmd == "intake":
        _prepare_intake(args)
    cfg = config.resolve_config(args)
    if not (cfg["site"] and cfg["email"] and cfg["token"]):
        raise CommandError(f"Not configured yet. Run: {prog} config init")
    j = Jira(cfg.get("api_site", cfg["site"]), cfg["email"], cfg["token"])
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
    except JiraError as error:
        if error.status == 401 and cfg.get("profile") and not args.no_input and not args.json and sys.stdin.isatty():
            if ui.confirm("Authentication failed. Replace this profile's API token now?"):
                from . import auth
                from types import SimpleNamespace
                recovery = SimpleNamespace(profile=cfg["profile"], site=None, email=None, token=None,
                                           project=None, json=False, no_input=False)
                auth.login(recovery, replace=True)
                ui.err_console.print("Token replaced. Run the command again after checking the previous operation's outcome.")
        raise
    finally:
        j.close()
