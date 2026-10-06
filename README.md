# Jira CLI Toolkit

A Jira Cloud CLI with grouped commands, Rich terminal output, and a compatible `jsup` executable. Repository: [User17745/jira-cli-toolkit](https://github.com/User17745/jira-cli-toolkit).

The current source is an unreleased v2 foundation (`0.3.0.dev0`). It adds project-neutral commands and help while preserving existing workflows. Authentication profiles, field discovery, templates, automatic updates, and binary releases are tracked in the [upgrade roadmap](docs/sprints/v2-upgrade/roadmap.md).

## Install from this checkout

Requires Python 3.10 or later:

```bash
pipx install .
# Both executables are installed:
jira-cli-toolkit --version
jsup --version
```

If `jsup` is already installed, use `pipx install --force .` from the desired checkout to replace the installation. No automated upgrade or release publication is provided yet. The Python package remains `jsup` for compatibility.

## Setup and help

```bash
jira-cli-toolkit config init
jira-cli-toolkit user me
jira-cli-toolkit --help
jira-cli-toolkit help issue create
jira-cli-toolkit issue comment --help
```

Help and version commands work without configuration or network access. An incomplete command group displays its help.

`config init` currently asks for a site URL, email, API token, and optional default project. It writes `~/.config/jsup/config.json` with permissions `0600`; the token is plaintext. Flags override `JIRA_SITE`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, and `JIRA_PROJECT`, which override saved settings. Configuration is retained when switching between executables. No OAuth, expiry tracking, refresh, keychain storage, or automatic reauthentication is implemented yet.

## Local context and dashboard

```bash
jira-cli-toolkit                         # Local site/project context and tips
jira-cli-toolkit context show --json     # Local view without email or token
jira-cli-toolkit dashboard -p ENG
jira-cli-toolkit dashboard --projects ENG HR
```

The dashboard requires a selected project or explicit `--projects`; it does not query a fixed list of projects. Counts use Jira's estimate API and are labeled approximate. The legacy `jsup` root still opens the dashboard. Its JSON dashboard retains the original project/hint payload; use the new executable for dashboard results.

## Issue workflows

```bash
jira-cli-toolkit issue list -p ENG
jira-cli-toolkit issue list -p ENG --open
jira-cli-toolkit issue list --jql 'assignee = currentUser()' --json
jira-cli-toolkit issue create -p ENG --type Task --summary "Review onboarding"
jira-cli-toolkit issue view ENG-42
jira-cli-toolkit issue view ENG-42 --web
jira-cli-toolkit issue transitions ENG-42
jira-cli-toolkit issue transition ENG-42 --to "In Progress"
jira-cli-toolkit issue comment add ENG-42 -m "Review started"
jira-cli-toolkit issue comment list ENG-42
```

`issue list` includes Done issues unless `--open` is supplied. Its `--jql` is a complete query: it ignores the configured default project and cannot be combined with explicit `--project` or `--open`. Legacy `open --jql` retains its original extra-filter behavior. Lists currently fetch one page; `--limit` (alias `--max`) controls the requested result/page size. Complete pagination is a later milestone.

Creation accepts type, priority, account-ID assignee, repeated labels/components, descriptions, and description files. `Task` remains the displayed default type; required custom fields are not yet discovered. Generic creation does not add support-specific metadata. The explicit legacy `jsup intake` wizard still creates callback issues with the `callback` label and `ops-runbook` component, pending migration to a template.

## Boards, sprints, and components

```bash
jira-cli-toolkit board list -p ENG
jira-cli-toolkit board create -p ENG --name "Engineering" --type scrum
jira-cli-toolkit board view 123 --web
jira-cli-toolkit board issues 123
jira-cli-toolkit sprint list --board 123
jira-cli-toolkit sprint create --board 123 --name "Planning 1"
jira-cli-toolkit sprint add-issues 456 ENG-42 ENG-43
jira-cli-toolkit sprint start 456
jira-cli-toolkit sprint close 456
jira-cli-toolkit component list -p ENG
jira-cli-toolkit project list
```

Software operations require applicable boards and Jira permissions. Feature toggles are under `board feature enable/disable`. These operations preserve the existing API implementation; full sprint lifecycle requirements and capabilities will be validated in later milestones. `view --web` and legacy `browse` require only a site URL and use the browser's session. Board URLs do not guess a project from local configuration.

## Scripts and compatibility

```bash
jira-cli-toolkit --project ENG --json issue list --open --no-input
jira-cli-toolkit issue transition ENG-42 --to Done --json --no-input
jira-cli-toolkit issue delete ENG-42 --yes --json --no-input
```

Global flags work before, between, or after subcommands; the last explicitly supplied value wins. `--no-input`, or nonterminal input, prevents prompts and reports missing flags. `--json` does not bypass deletion confirmation. JSON results go to stdout; progress and errors go to stderr. Successful API payloads retain their original shape. Exit codes are 0 for success/help, 1 for API/network failures, 2 for usage/configuration/input/file errors, and 130 for interruption.

Both executables accept legacy commands such as `issue-show`, `issue-create`, `comment-add`, `board-list`, and `sprint-add`. Existing names, configuration keys, and environment variables are retained through v2.x. Legacy `board-list` searches all accessible boards unless `--jql-project` is supplied, while grouped `board list` uses the selected project. See the [interface and migration contract](docs/sprints/v2-upgrade/interface-contract.md) for exact behavior and current limitations.

## Development

```bash
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Tests use local fixtures and mocked Jira calls. They do not require real Jira credentials or modify tickets. On Windows use the corresponding `.venv\Scripts\python` executable.
