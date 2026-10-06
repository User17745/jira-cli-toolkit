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

If `jsup` is already installed, use `pipx install --force .` from the desired checkout to replace the installation. The explicit updater and tag-triggered release workflow are described below. The Python package remains `jsup` for compatibility.

## Setup and help

```bash
jira-cli-toolkit config init
jira-cli-toolkit user me
jira-cli-toolkit --help
jira-cli-toolkit help issue create
jira-cli-toolkit issue comment --help
```

Help and version commands work without configuration or network access. An incomplete command group displays its help.

New users should use the guided `auth login` flow below. Legacy `config init` remains compatible until credentials are migrated; it writes a plaintext token. `config migrate` moves that identity to a named profile and the selected credential store. API tokens cannot refresh automatically.

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

`issue list` includes Done issues unless `--open` is supplied. Its `--jql` is a complete query: it ignores the configured default project and cannot be combined with explicit `--project` or `--open`. Legacy `open --jql` retains its original extra-filter behavior. `--limit` (alias `--max`) bounds total fetched results across pages; `--all` follows every page.

Creation accepts type, priority, account-ID assignee, repeated labels/components, descriptions, and description files. Grouped creation discovers project/type fields. Pass `--type Bug` in scripts or choose interactively; `project issue-types` and `project fields --type Bug` show available values. Required custom fields accept `--field FIELD=VALUE`, `FIELD:=JSON`, or `--fields-file`. Legacy `issue-create` retains its Task default. Generic creation does not add support-specific metadata. The explicit legacy `jsup intake` wizard still creates callback issues with the `callback` label and `ops-runbook` component, pending migration to a template.

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

Global flags work before, between, or after subcommands; the last explicitly supplied value wins. `--no-input`, or nonterminal input, prevents prompts and reports missing flags. `--json` does not bypass deletion confirmation. JSON results and structured runtime errors go to stdout for new commands; progress and argparse usage errors go to stderr. Legacy aliases/jsup keep errors on stderr. Successful API payloads retain their original shape. Exit codes are 0 for success/help, 1 for API/network failures, 2 for usage/configuration/input/file errors, and 130 for interruption.

Both executables accept legacy commands such as `issue-show`, `issue-create`, `comment-add`, `board-list`, and `sprint-add`. Existing names, configuration keys, and environment variables are retained through v2.x. Legacy `board-list` searches all accessible boards unless `--jql-project` is supplied, while grouped `board list` uses the selected project. See the [interface and migration contract](docs/sprints/v2-upgrade/interface-contract.md) for exact behavior and current limitations.

## Development

```bash
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Tests use local fixtures and mocked Jira calls. They do not require real Jira credentials or modify tickets. On Windows use the corresponding `.venv\Scripts\python` executable.

## Guided authentication and profiles

For a new installation, run `jira-cli-toolkit auth login --profile work`. The guided screen links to [Atlassian token creation](https://id.atlassian.com/manage-profile/security/api-tokens), hides token input, validates your account, and lets you choose a project. A token inherits your account's permissions; scoped tokens also need scopes for the operations you use. For a scoped personal token, add `--scoped` (and `--cloud-id ID` if automatic site discovery is unavailable).

Tokens are stored in your native OS credential store. Preferences remain at `~/.config/jsup/config.json`; the v2 schema contains profile references and no tokens. If no native store is available, supply a complete `JIRA_SITE`, `JIRA_EMAIL`, and `JIRA_API_TOKEN` identity for scripts. Explicit `--storage file` is a POSIX-only plaintext opt-in with a separate mode-0600 credentials file. The CLI never silently falls back to it.

Existing users run `jira-cli-toolkit config migrate` to validate and migrate their saved identity safely. Then use `profile list`, `profile use work`, `context use --project ENG`, `auth status`, and `doctor`. Local `auth logout` does not revoke the token at Atlassian or clear externally supplied credentials. API tokens cannot refresh; an invalid/expired/revoked token must be replaced with `auth login`. Recovery never replays a write automatically.

A selected `--profile` owns its full site/account identity. Complete identity flags or environment variables can supply another identity when no profile is explicitly selected; partial identities are rejected for schema-2 users. A project override does not change accounts.

## Explicit updates and releases

`jira-cli-toolkit update --info` shows local installation details. `update --check` checks the latest stable GitHub Release without changing the installation. Select a candidate with `update --version VERSION --prerelease --check`; a downgrade needs `--allow-downgrade`. A standalone update needs `--yes` in scripts, verifies the release manifest and binary SHA-256/size, runs version/help checks, and retains a `.previous` executable for rollback. Windows uses a separate helper after the old process exits; pending updates report a log path. Config and credentials are untouched.

The repository is private. Set a repository-read `GH_TOKEN` or authenticate `gh` with the correct GitHub account for release discovery/downloads. Jira tokens are never used for GitHub. Package installations receive instructions for their owning pipx/uv/Python environment; the updater does not overwrite manager shims. Since the Python package is not published to PyPI, download and verify the wheel from the release and pass its path to that manager (`pipx install --force /path/to/jsup.whl`, `uv tool install --force /path/to/jsup.whl`, or your environment's `python -m pip install --upgrade /path/to/jsup.whl`). Version 0.2.0 needs this one-time bootstrap before it gains an update command.

GitHub Actions builds and smoke-tests Python packages and native binaries. Version tags publish a complete manifest, checksums, wheel/sdist, and macOS arm64/x86_64, Linux x86_64, and Windows x86_64 executables. Prereleases never become latest stable; stable publication additionally requires a commit on main. Native platform requirements are recorded in each release manifest. Checksums detect corruption; publisher verification currently relies on authenticated GitHub HTTPS. Code signing, notarization, and independently verified provenance remain release-hardening tasks.
