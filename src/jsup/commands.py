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
                        json=False, no_input=False, profile=None, csv=False, columns=None)
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
    if operation.startswith(("desk-", "request-")):
        if operation in {"desk-list", "desk-queues", "desk-queue", "request-list"}:
            parser.add_argument("--all", action="store_true", help="fetch every page; overrides --limit")
            parser.add_argument("--limit", "--max", dest="max", type=positive_int, default=50)
        if operation in {"desk-queues", "desk-queue"}:
            parser.add_argument("desk", help="service desk ID, project key or name")
        if operation == "desk-queue":
            parser.add_argument("queue", help="queue ID or name")
        if operation == "request-list":
            parser.add_argument("--desk", help="only this service desk (ID, project key or name)")
            parser.add_argument("--status", choices=["open", "closed", "all"], default="open")
        if operation in {"request-view", "request-comment", "request-transitions", "request-transition"}:
            parser.add_argument("key", help="request key, for example HELP-12")
        if operation == "request-comment":
            parser.add_argument("--message", "-m", required=True)
            parser.add_argument("--internal", action="store_true",
                                help="visible to agents only; without it the customer sees the comment")
        if operation == "request-transition":
            parser.add_argument("--to", help="transition name or ID")
            parser.add_argument("--message", "-m", help="comment added with the transition, visible to the customer")
        return
    if operation == "skill-install":
        parser.add_argument("--path", metavar="DIR", help="folder to write SKILL.md into (default ~/.claude/skills/jira)")
        parser.add_argument("--force", action="store_true", help="replace a SKILL.md that has been changed")
        return
    if operation == "api":
        parser.add_argument("path", metavar="PATH", help="Jira REST path, for example /rest/api/3/myself; or spec")
        parser.add_argument("spec_action", metavar="ACTION", nargs="?", help="after spec: refresh or status")
        parser.add_argument("-X", "--method", type=str.upper, default="GET",
                            choices=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
        parser.add_argument("--query", "-q", action="append", default=[], metavar="KEY=VALUE",
                            help="query parameter; repeat for more, values are URL-encoded")
        parser.add_argument("--header", "-H", action="append", default=[], metavar="'NAME: VALUE'",
                            help="extra request header; auth, host and framing headers are managed")
        parser.add_argument("--data", "-d", metavar="JSON|@FILE|@-", help="JSON body, sent unchanged")
        parser.add_argument("--raw-data", metavar="TEXT|@FILE|@-", help="non-JSON body; needs --content-type")
        parser.add_argument("--content-type", help="body media type for --data or --raw-data")
        parser.add_argument("--form", "-F", action="append", default=[], metavar="NAME=VALUE|NAME=@FILE",
                            help="multipart field or file; repeat for more")
        parser.add_argument("--include", "-i", action="store_true", help="print response status and headers to stderr")
        parser.add_argument("--output", "-o", metavar="FILE", help="save the response body to a new file")
        parser.add_argument("--paginate", action="store_true",
                            help="follow every page and print one merged JSON result")
        parser.add_argument("--max-items", type=positive_int, metavar="N", help="stop --paginate after N items")
        parser.add_argument("--spec", action="store_true",
                            help="describe the operation from cached official specs; sends no request")
        return
    if operation == "issue-edit":
        parser.add_argument("key")
        for name in ("summary", "priority", "due-date", "parent"):
            parser.add_argument("--" + name)
        parser.add_argument("--description", "--desc", dest="desc")
        parser.add_argument("--description-file", dest="desc_file")
        parser.add_argument("--editor", action="store_true")
        parser.add_argument("--field", action="append", default=[])
        parser.add_argument("--fields-file")
        for collection in ("label", "component"):
            for prefix in ("", "add-", "remove-"):
                parser.add_argument("--" + prefix + collection, action="append", default=[])
        return
    if operation in {"issue-assign", "issue-unassign", "issue-link", "issue-unlink", "attachment-list", "attachment-upload", "attachment-download", "attachment-delete", "comment-edit", "comment-delete"}:
        if operation in {"issue-unlink", "attachment-download", "attachment-delete"}:
            parser.add_argument("id", type=positive_int)
        else:
            parser.add_argument("key")
        if operation == "issue-assign":
            parser.add_argument("--user", required=True, help="me, id:<account ID>, or unambiguous display name/email")
        if operation == "issue-link":
            parser.add_argument("other")
            parser.add_argument("--type", required=True)
            parser.add_argument("--direction", choices=["inward", "outward"], required=True)
        if operation == "attachment-upload":
            parser.add_argument("files", nargs="+")
        if operation == "attachment-download":
            parser.add_argument("--output", required=True, help="new file path or existing directory")
        if operation in {"comment-edit", "comment-delete"}:
            parser.add_argument("comment_id", type=positive_int)
        if operation == "comment-edit":
            parser.add_argument("--message", "-m")
            parser.add_argument("--message-file")
            parser.add_argument("--editor", action="store_true")
        if operation in {"issue-unlink", "attachment-delete", "comment-delete"}:
            parser.add_argument("--yes", action="store_true")
        return
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
            parser.add_argument("--template", help="built-in/local template name or JSON path")
            parser.add_argument("--var", action="append", default=[], help="template variable NAME=VALUE")
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
            parser.add_argument("--assignee", help="account ID or me")
            parser.add_argument("--status", action="append", default=[])
            parser.add_argument("--type")
            parser.add_argument("--label", action="append", default=[])
            parser.add_argument("--board", type=positive_int)
            parser.add_argument("--order-by", choices=["updated", "created", "priority", "key"], default="updated")
            parser.add_argument("--order", choices=["asc", "desc"], default="desc")
            parser.add_argument("--fields", help="comma-separated Jira field IDs")
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
            parser.add_argument("--message", "-m", required=parser._defaults.get("legacy", False))
            parser.add_argument("--message-file")
            parser.add_argument("--editor", action="store_true")
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
        parser.add_argument("--board", type=positive_int, required=parser._defaults.get("legacy", False))
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
    output = common.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="JSON output")
    output.add_argument("--csv", action="store_true", help="CSV output for lists")
    common.add_argument("--columns", help="comma-separated list columns")
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
    completion = command(root, "completion", "completion", "generate local shell completion")
    completion.add_argument("shell", choices=["bash", "zsh", "fish"])
    _, templates = group(root, "template", "inspect and validate reusable JSON templates")
    command(templates, "list", "template-list", "list built-in and local templates")
    for action in ("show", "validate"):
        item = command(templates, action, "template-" + action, action + " a declarative template")
        item.add_argument("template")
        if action == "validate":
            item.add_argument("--type")
            item.add_argument("--var", action="append", default=[])
            item.add_argument("--refresh", action="store_true")
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
    use.add_argument("--select", action="store_true", help="choose accessible projects and boards interactively")
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
    command(issues, "edit", "issue-edit", "update editable fields and collection values")
    command(issues, "assign", "issue-assign", "assign an issue")
    command(issues, "unassign", "issue-unassign", "clear the assignee")
    command(issues, "link", "issue-link", "link two issues with explicit direction")
    command(issues, "unlink", "issue-unlink", "delete a link after confirmation")
    _, comments = group(issues, "comment", "issue comments")
    command(comments, "add", "comment-add", "add a comment")
    command(comments, "list", "comment-list", "list comments")
    command(comments, "edit", "comment-edit", "edit a comment")
    command(comments, "delete", "comment-delete", "delete a comment after confirmation")
    _, attachments = group(issues, "attachment", "issue attachments")
    for action in ("list", "upload", "download", "delete"):
        command(attachments, action, "attachment-" + action, action + " attachments")
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
    command(root, "api", "api", "call any Jira REST path with the selected identity")
    _, skills = group(root, "skill", "agent skill that teaches coding agents to use jira")
    command(skills, "show", "skill-show", "print the bundled SKILL.md")
    command(skills, "install", "skill-install", "write SKILL.md where an agent loads skills")
    _, desks = group(root, "desk", "Jira Service Management desks and queues")
    command(desks, "list", "desk-list", "list service desks you can see")
    command(desks, "queues", "desk-queues", "list a desk's queues with issue counts")
    command(desks, "queue", "desk-queue", "list the issues in a queue")
    _, requests_ = group(root, "request", "Jira Service Management customer requests")
    command(requests_, "list", "request-list", "list requests you can see, open by default")
    command(requests_, "view", "request-view", "show a request with status, participants and SLAs")
    command(requests_, "comment", "request-comment", "reply to the customer, or add an internal note")
    command(requests_, "transitions", "request-transitions", "list a request's available transitions")
    command(requests_, "transition", "request-transition", "move a request, optionally with a comment")

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
