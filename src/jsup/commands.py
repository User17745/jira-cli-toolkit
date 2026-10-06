"""Command grammar shared by the new executable and legacy jsup commands."""
from __future__ import annotations

import argparse

from . import __version__


class CLIParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        if namespace is None:
            namespace = argparse.Namespace()
        # Seed the root namespace rather than setting defaults on inherited
        # option actions, which argparse shares between parent/child parsers.
        defaults = dict(project=None, site=None, email=None, token=None,
                        json=False, no_input=False, profile=None)
        for name, value in defaults.items():
            if not hasattr(namespace, name):
                setattr(namespace, name, value)
        return super().parse_args(args, namespace)


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def _options(parser: argparse.ArgumentParser, operation: str) -> None:
    """Define each operation once, including options shared by legacy aliases."""
    lists = {"project-list", "board-list", "sprint-list", "comment-list", "open", "issue-list", "board-issues"}
    if operation in lists:
        parser.add_argument("--all", action="store_true", help="fetch every page; overrides --limit")
        if operation not in {"open", "issue-list", "board-issues"}:
            parser.add_argument("--limit", dest="max", type=positive_int, default=50)
    if operation == "dashboard":
        parser.add_argument("--projects", nargs="+", help="project keys to summarize")
    elif operation in {"project-show", "project-types", "project-fields", "project-statuses"}:
        parser.add_argument("key", nargs="?")
        if operation in {"project-types", "project-fields"}:
            parser.add_argument("--refresh", action="store_true")
        if operation == "project-fields":
            parser.add_argument("--type", required=True)
    elif operation == "issue-create":
        legacy = parser._defaults.get("legacy", False)
        parser.add_argument("--summary", "-s", required=legacy)
        parser.add_argument("--description", "--desc", "-d", dest="desc", default="" if legacy else None)
        parser.add_argument("--description-file", "--desc-file", dest="desc_file")
        parser.add_argument("--type", "-t", default="Task" if legacy else None, help="issue type name or id:<ID>; guided selection when omitted")
        parser.add_argument("--priority")
        parser.add_argument("--assignee", help="Jira account ID")
        parser.add_argument("--label", action="append", default=[])
        parser.add_argument("--component", action="append", default=[])
        if not legacy:
            parser.add_argument("--parent")
            parser.add_argument("--field", action="append", default=[])
            parser.add_argument("--fields-file")
            parser.add_argument("--editor", action="store_true")
            parser.add_argument("--refresh", action="store_true")
    elif operation == "intake":
        parser.add_argument("--name", help="client name")
        parser.add_argument("--issue", help="issue as reported")
        parser.add_argument("--callback", default="not specified")
        parser.add_argument("--type", default="Task")
        parser.add_argument("--priority", default="High")
    elif operation in ("open", "issue-list"):
        parser.add_argument("--jql", default="", help=(
            "extra JQL appended to the open-ticket filter" if operation == "open"
            else "complete JQL query; cannot be combined with --open or --project"))
        parser.add_argument("--limit", "--max", dest="max", type=positive_int, default=50)
        if operation == "issue-list":
            parser.add_argument("--open", action="store_true", help="exclude the Done status category")
    elif operation in ("issue-show", "issue-move", "transitions", "issue-delete", "comment-add", "comment-list"):
        parser.add_argument("key")
        if operation == "issue-show":
            parser.add_argument("--web", action="store_true")
        elif operation == "issue-move":
            parser.add_argument("--to", help="transition name or ID")
            if not parser._defaults.get("legacy", False):
                parser.add_argument("--field", action="append", default=[])
                parser.add_argument("--fields-file")
        elif operation == "issue-delete":
            parser.add_argument("--yes", action="store_true", help="skip confirmation")
        elif operation == "comment-add":
            parser.add_argument("--message", "-m", required=True)
    elif operation == "board-list":
        parser.add_argument("--jql-project", help="legacy project-filter override")
    elif operation == "board-create":
        parser.add_argument("--name", required=True)
        parser.add_argument("--jql")
        parser.add_argument("--filter-id", type=positive_int)
        parser.add_argument("--type", default="scrum", choices=["scrum", "kanban"])
    elif operation in ("board-show", "board-issues", "board-feature"):
        parser.add_argument("board_id", type=positive_int)
        if operation == "board-show":
            parser.add_argument("--web", action="store_true")
        elif operation == "board-issues":
            parser.add_argument("--jql", default="")
            parser.add_argument("--limit", "--max", dest="max", type=positive_int, default=50)
        else:
            parser.add_argument("--feature", required=True)
            if "enable" not in parser._defaults:
                group = parser.add_mutually_exclusive_group(required=True)
                group.add_argument("--enable", action="store_true")
                group.add_argument("--disable", action="store_true")
    elif operation in ("sprint-list", "sprint-create"):
        parser.add_argument("--board", type=positive_int, required=True)
        if operation == "sprint-list":
            parser.add_argument("--state", default="active,future")
        else:
            parser.add_argument("--name", required=True)
            parser.add_argument("--goal", default="")
    elif operation in ("sprint-state", "sprint-add"):
        parser.add_argument("sprint_id", type=positive_int)
        if operation == "sprint-add":
            parser.add_argument("keys", nargs="+")
        elif "state" not in parser._defaults:
            parser.add_argument("state", choices=["active", "closed", "future"])
    elif operation == "component-create":
        parser.add_argument("--name", required=True)
        parser.add_argument("--description", "--desc", dest="desc", default="")
    elif operation == "browse":
        parser.add_argument("target", help="issue key or board:<id>")


LEGACY_COMMANDS = {
    "me": "show authenticated user",
    "project-list": "list projects",
    "project-show": "show project details",
    "issue-create": "create an issue",
    "intake": "explicit legacy callback/support wizard",
    "open": "list unfinished issues",
    "issue-show": "show an issue",
    "issue-move": "transition an issue",
    "transitions": "list available transitions",
    "issue-delete": "delete an issue",
    "comment-add": "add a comment",
    "comment-list": "list comments",
    "board-list": "list boards",
    "board-create": "create a board",
    "board-issues": "list board issues",
    "board-feature": "toggle a board feature",
    "sprint-list": "list sprints",
    "sprint-create": "create a sprint",
    "sprint-state": "change sprint state",
    "sprint-add": "add issues to a sprint",
    "component-list": "list components",
    "component-create": "create a component",
    "browse": "open an issue or board in a browser",
}


def build_parser(prog: str = "jsup") -> argparse.ArgumentParser:
    # Suppressed defaults on inherited options prevent a child parser from
    # overwriting flags supplied earlier in the command line.
    common = argparse.ArgumentParser(add_help=False, argument_default=argparse.SUPPRESS)
    common.add_argument("--site")
    common.add_argument("--email")
    common.add_argument("--token")
    common.add_argument("--project", "-p", help="project key")
    common.add_argument("--profile", help="named identity; never mixed with identity flags")
    common.add_argument("--json", action="store_true", help="JSON output")
    common.add_argument("--no-input", action="store_true", help="never prompt")
    parser = CLIParser(
        prog=prog, parents=[common], description="Jira CLI Toolkit — Jira Cloud from your terminal",
        epilog=f"Examples: {prog} issue list -p ENG --open; {prog} help issue create",
    )
    parser.add_argument("--version", action="version", version=f"{prog} {__version__}")
    parser.set_defaults(cmd=None, legacy=False, selected_parser=parser)
    root = parser.add_subparsers(dest="command", title="commands")

    def group(subparsers, name, help_text):
        child = subparsers.add_parser(name, parents=[common], help=help_text)
        child.set_defaults(selected_parser=child)
        return child, child.add_subparsers(dest=f"{name}_action")

    def command(subparsers, name, operation, help_text, **defaults):
        child = subparsers.add_parser(name, parents=[common], help=help_text)
        child.set_defaults(cmd=operation, selected_parser=child, **defaults)
        _options(child, operation)
        return child

    helper = root.add_parser("help", help="show help for any command")
    helper.add_argument("path", nargs="*", help="for example: issue comment add")
    helper.set_defaults(cmd="help")
    command(root, "dashboard", "dashboard", "summarize selected projects")
    updater = command(root, "update", "update", "check GitHub Releases or explicitly upgrade")
    updater.add_argument("--check", action="store_true")
    updater.add_argument("--info", action="store_true", help="local installation details, without network")
    updater.add_argument("--version", help="requested release version")
    updater.add_argument("--prerelease", action="store_true")
    updater.add_argument("--allow-downgrade", action="store_true")
    updater.add_argument("--yes", action="store_true")
    _, config = group(root, "config", "set up and inspect local configuration")
    command(config, "init", "config-init", "legacy credential setup")
    command(config, "show", "config-show", "show saved configuration with token masked")
    migrate = command(config, "migrate", "config-migrate", "migrate legacy credentials to a named profile")
    migrate.add_argument("--storage", choices=["keyring", "file"], default="keyring")
    for action in ("get", "set"):
        pref = command(config, action, "config-"+action, "inspect or change a nonsecret preference")
        pref.add_argument("key", choices=["project", "board"])
        if action == "set":
            pref.add_argument("value")
    _, auth = group(root, "auth", "guided API-token login and credential health")
    login = command(auth, "login", "auth-login", "validate and store an API token")
    login.add_argument("--storage", choices=["keyring", "file"], default="keyring")
    login.add_argument("--token-stdin", action="store_true")
    login.add_argument("--scoped", action="store_true", help="token uses API scopes and the Atlassian gateway")
    login.add_argument("--cloud-id", help="cloud ID for a scoped token")
    command(auth, "status", "auth-status", "validate the selected identity with Jira")
    command(auth, "logout", "auth-logout", "delete selected local credential; upstream tokens are not revoked")
    _, profiles = group(root, "profile", "named site/account identities")
    command(profiles, "list", "profile-list", "list saved profiles without reading secrets")
    for action in ("use", "remove"):
        item = command(profiles, action, "profile-"+action, "select or remove a profile")
        item.add_argument("name")
    command(root, "doctor", "doctor", "redacted connectivity, identity and project diagnostics")
    _, context = group(root, "context", "inspect resolved local context")
    command(context, "show", "context-show", "show site and project without contacting Jira")
    use = command(context, "use", "context-use", "select a profile/project/board after checking access")
    use.add_argument("--board", type=positive_int)
    _, user = group(root, "user", "user identity")
    command(user, "me", "me", "show authenticated user")
    _, projects = group(root, "project", "projects")
    command(projects, "list", "project-list", "list accessible projects")
    command(projects, "view", "project-show", "view a project")
    command(projects, "issue-types", "project-types", "discover available issue types")
    command(projects, "fields", "project-fields", "discover creation fields and required values")
    command(projects, "statuses", "project-statuses", "show workflow statuses by issue type")
    _, issues = group(root, "issue", "issue operations")
    command(issues, "list", "issue-list", "search issues, optionally excluding Done")
    command(issues, "create", "issue-create", "create an issue")
    command(issues, "view", "issue-show", "view an issue or open it with --web")
    command(issues, "transition", "issue-move", "choose or apply an available transition")
    command(issues, "transitions", "transitions", "list available transitions")
    command(issues, "delete", "issue-delete", "delete an issue after confirmation")
    _, comments = group(issues, "comment", "issue comments")
    command(comments, "add", "comment-add", "add a comment")
    command(comments, "list", "comment-list", "list comments")
    _, boards = group(root, "board", "board operations")
    command(boards, "list", "board-list", "list boards")
    command(boards, "create", "board-create", "create a filter and board")
    command(boards, "view", "board-show", "view a board or open it with --web")
    command(boards, "issues", "board-issues", "list issues on a board")
    _, features = group(boards, "feature", "toggle board features")
    command(features, "enable", "board-feature", "enable a feature", enable=True)
    command(features, "disable", "board-feature", "disable a feature", enable=False)
    _, sprints = group(root, "sprint", "sprint operations")
    command(sprints, "list", "sprint-list", "list board sprints")
    command(sprints, "create", "sprint-create", "create a sprint")
    command(sprints, "start", "sprint-state", "start a sprint", state="active")
    command(sprints, "close", "sprint-state", "close a sprint", state="closed")
    edit = command(sprints, "edit", "sprint-state", "change sprint state", state=None)
    edit.add_argument("--state", required=True, choices=["active", "closed", "future"])
    command(sprints, "add-issues", "sprint-add", "add issues to a sprint")
    _, components = group(root, "component", "project components")
    command(components, "list", "component-list", "list components")
    command(components, "create", "component-create", "create a component")

    for name, help_text in LEGACY_COMMANDS.items():
        command(root, name, name, f"legacy: {help_text}", legacy=True)
    return parser


def help_parser(parser: argparse.ArgumentParser, path: list[str]) -> argparse.ArgumentParser:
    """Resolve help paths through actual parser choices, including legacy names."""
    current = parser
    for part in path:
        subparsers = next((action for action in current._actions
                          if isinstance(action, argparse._SubParsersAction)), None)
        if subparsers is None or part not in subparsers.choices:
            parser.error(f"unknown help command: {' '.join(path)}")
        current = subparsers.choices[part]
    return current
