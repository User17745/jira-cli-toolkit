"""Export the grouped `jira` command tree for the website.

The landing page completes and documents commands from this file, so it is
generated from the real parser. Run after changing commands:

    python scripts/command_tree.py > web/src/data/commands.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jsup import __version__  # noqa: E402
from jsup.commands import LEGACY_COMMANDS, build_parser  # noqa: E402

GLOBAL = {"help", "site", "email", "token", "project", "profile", "json", "csv", "columns", "no_input"}


def _subparsers(parser):
    return next((a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None)


def _option(action):
    if not action.option_strings:
        return {"positional": action.dest, "metavar": action.metavar, "nargs": action.nargs,
                "choices": list(action.choices or []),
                "type": getattr(action.type, "__name__", None), "help": action.help or ""}
    return {"flag": max(action.option_strings, key=len), "names": list(action.option_strings),
            "takesValue": action.nargs != 0, "nargs": action.nargs,
            "metavar": action.metavar or action.dest.upper(),
            "required": bool(action.required), "choices": list(action.choices or []),
            "repeat": isinstance(action, argparse._AppendAction),
            "type": getattr(action.type, "__name__", None), "help": action.help or ""}


def _options(parser):
    return [_option(action) for action in parser._actions
            if action.dest not in GLOBAL and not isinstance(action, (argparse._SubParsersAction, argparse._VersionAction))]


def _node(parser, name, help_text, root=False):
    node = {"name": name, "help": help_text or "", "description": parser.description,
            # A few parsers, such as `help`, do not inherit the shared identity/output options.
            "shared": any(a.dest == "site" for a in parser._actions)}
    sub = _subparsers(parser)
    if sub is None:
        node["options"] = _options(parser)
        return node
    helps = {a.dest: a.help for a in sub._choices_actions}
    # argparse names the subcommand slot after its dest in invalid-choice errors.
    node["dest"] = sub.dest
    node["title"] = next(g.title for g in parser._action_groups if sub in g._group_actions)
    # Legacy jsup aliases live only at the root; nested names such as
    # `issue transitions` are grouped commands.
    node["commands"] = [_node(child, child_name, helps.get(child_name))
                        for child_name, child in sub.choices.items()
                        if not (root and child_name in LEGACY_COMMANDS)]
    return node


def tree() -> dict:
    parser = build_parser("jira")
    root = _node(parser, "jira", parser.description, root=True)
    root["version"] = __version__
    root["epilog"] = parser.epilog
    # Hidden from the site, but argparse still lists them in root help and errors.
    root["legacy"] = [{"name": a.dest, "help": a.help} for a in _subparsers(parser)._choices_actions
                      if a.dest in LEGACY_COMMANDS]
    root["globals"] = [_option(a) for a in parser._actions if a.dest in GLOBAL]
    # Only --json and --csv are mutually exclusive.
    root["exclusive"] = [[a.option_strings[0] for a in group._group_actions]
                         for group in parser._mutually_exclusive_groups]
    return root


if __name__ == "__main__":
    print(json.dumps(tree(), indent=1, ensure_ascii=False))
