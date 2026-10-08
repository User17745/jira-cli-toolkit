<a href="https://user17745.github.io/jira-cli-toolkit/"><img src="https://raw.githubusercontent.com/User17745/jira-cli-toolkit/main/docs/assets/cli-toolkit-cover-illustrated.png" alt="CLI Toolkit for Jira — independent terminal tools for Jira Cloud, with current issue, project and sprint command examples" width="100%" /></a>

<p align="center">
  <a href="https://github.com/User17745/jira-cli-toolkit/blob/main/LICENSE"><img alt="License: AGPL v3 only" src="https://img.shields.io/badge/license-AGPL%20v3%20only-087f75?style=flat-square" /></a>
  <a href="https://github.com/User17745/jira-cli-toolkit/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/User17745/jira-cli-toolkit?style=flat-square&color=087f75" /></a>
  <a href="https://github.com/User17745/jira-cli-toolkit/actions/workflows/ci.yml"><img alt="CLI tests" src="https://img.shields.io/github/actions/workflow/status/User17745/jira-cli-toolkit/ci.yml?branch=main&style=flat-square&label=tests" /></a>
  <a href="https://github.com/User17745/jira-cli-toolkit/actions/workflows/release.yml"><img alt="Native builds" src="https://img.shields.io/github/actions/workflow/status/User17745/jira-cli-toolkit/release.yml?branch=main&style=flat-square&label=native%20builds" /></a>
  <img alt="Python 3.10 and later" src="https://img.shields.io/badge/python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white" />
  <img alt="macOS, Linux and Windows" src="https://img.shields.io/badge/platforms-macOS%20%7C%20Linux%20%7C%20Windows-526581?style=flat-square" />
  <a href="https://github.com/User17745/jira-cli-toolkit/releases"><img alt="Release downloads" src="https://img.shields.io/github/downloads/User17745/jira-cli-toolkit/total?style=flat-square&color=087f75" /></a>
</p>

# CLI Toolkit for Jira

**Independent terminal tools for Jira Cloud, using the `jira` command.** Find issues, create and edit work, manage sprints, and automate repeatable workflows using your existing account and project permissions.

Independent project. Not affiliated with, endorsed by, or sponsored by Atlassian. Jira is a trademark of Atlassian.

[Website](https://user17745.github.io/jira-cli-toolkit/) · [Command reference](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/usage.md) · [Latest release](https://github.com/User17745/jira-cli-toolkit/releases/latest) · [Migration guides](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/migration/upgrade-to-v2.md)

## Get started

Install the latest stable native binary. The installers verify release checksums and run version/help checks before installing. No Python runtime, administrator access, or Jira credentials are needed for native installation.

### macOS

```bash
curl -fsSL https://raw.githubusercontent.com/User17745/jira-cli-toolkit/main/scripts/install.sh | bash
export PATH="$HOME/.local/bin:$PATH"
```

macOS **15+**, Apple Silicon or Intel. Installs to `~/.local/bin/jira`.

Or with [Homebrew](https://brew.sh), which also handles upgrades:

```bash
brew install user17745/tap/jira-cli-toolkit
brew upgrade jira-cli-toolkit
```

### Linux

```bash
curl -fsSL https://raw.githubusercontent.com/User17745/jira-cli-toolkit/main/scripts/install.sh | bash
export PATH="$HOME/.local/bin:$PATH"
```

Linux **x86_64, glibc 2.39+** (for example Ubuntu 24.04+). Installs to `~/.local/bin/jira`. `curl` and `sha256sum` or `shasum` are required. Homebrew on Linux x86_64 works too (`brew install user17745/tap/jira-cli-toolkit`). On older systems, musl or unsupported native architectures, use the Python package instead: `pipx install jira-cli-toolkit`.

### Windows

Run in PowerShell:

```powershell
irm https://raw.githubusercontent.com/User17745/jira-cli-toolkit/main/scripts/install.ps1 | iex
```

Windows **10+ x86_64**, PowerShell **5.1+**. Installs to `%LOCALAPPDATA%\JiraCLI\bin\jira.exe` and adds that directory to your user PATH. Open a new terminal if needed.

**Prefer manual installation?** [Open the latest release](https://github.com/User17745/jira-cli-toolkit/releases/latest) and choose a matching binary or Python wheel. The [installation guide](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/migration/upgrade-to-v2.md) explains verification and pipx/uv/Python installation. From 2.5.1 the Python package is also on PyPI as `jira-cli-toolkit`: `pipx install jira-cli-toolkit`, then `pipx upgrade jira-cli-toolkit`. Installations made before 2.5.1 are tracked as `jsup`; switch once with `pipx uninstall jsup` and `pipx install jira-cli-toolkit` (configuration and saved credentials are kept).

**Already installed?** Use [the migration guide](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/migration/upgrade-to-v2.md). Installers refuse to replace existing CLI commands or managed shims. Custom paths and pinned versions are documented in [installer options](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/install.md).

### Connect your account

```bash
jira --version
jira auth login --profile work
jira context use --project ENG
jira issue list --open
```

Replace `ENG` with your project key. Guided login explains how to [create an Atlassian API token](https://id.atlassian.com/manage-profile/security/api-tokens), hides token input, validates your identity, and helps you select a project.

## Everyday workflows

| Do this | Run this |
| --- | --- |
| Find unfinished work | `jira issue list -p ENG --open` |
| Run your own JQL | `jira issue list --jql 'assignee = currentUser()'` |
| Inspect an issue | `jira issue view ENG-42` |
| Create an issue | `jira issue create -p ENG --type Bug --summary "Fix login"` |
| Edit an issue | `jira issue edit ENG-42 --summary "Fix keyboard navigation"` |
| Discover transitions | `jira issue transitions ENG-42` |
| Change its state | `jira issue transition ENG-42 --to "In Progress"` |
| Add a comment | `jira issue comment add ENG-42 -m "Review started"` |
| List boards and sprints | `jira board list -p ENG` · `jira sprint list --board 123` |
| Inspect project fields | `jira project fields -p ENG --type Bug` |

Issue types, fields, transitions and board operations follow your project’s metadata and permissions. The CLI also supports assignment, relationships, attachments, comment maintenance, components, templates, CSV and shell completion. [Explore the full reference](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/usage.md).

Help works without credentials or a network connection:

```bash
jira --help
jira help issue create
jira issue comment --help
```

## Authentication and profiles

- **Native credentials:** tokens use macOS Keychain, Windows Credential Manager, or a supported Linux wallet. Preferences at `~/.config/jsup/config.json` hold profile references, not tokens.
- **Multiple contexts:** use `profile list/use`, `--profile NAME`, and `context use --project KEY` to choose an account and project.
- **Scoped tokens:** guided login supports `--scoped` and cloud-ID discovery. Tokens inherit account permissions and must have the scopes needed for each operation.
- **Explicit alternatives:** scripts can supply a complete environment identity. POSIX `--storage file` is a separate mode-0600 plaintext opt-in, never an automatic fallback.
- **Recovery:** API tokens cannot refresh automatically. Replace an invalid/revoked/expired token with `auth login`; the CLI never replays a write automatically after recovery.

Native stores can require interactive approval. Linux wallets are interactive-only; scripted macOS access suppresses approval dialogs and fails with recovery instructions if approval is needed. [Read the authentication details](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/usage.md#guided-authentication-and-profiles).

## Automation and agents

```bash
jira issue list -p ENG --open --json --no-input
jira issue list -p ENG --open --csv --columns key,summary,status
jira issue create --template callback --var name=Example --var issue="Login failed"
jira completion zsh
```

JSON preserves API field structures, CSV supports selected columns, and `--no-input` makes missing input explicit. Destructive commands still need `--yes` in scripts. Runtime errors are structured on stdout for grouped commands; diagnostics and usage errors use stderr. Exit codes: **0** success/help, **1** API/network failure, **2** input/config/file errors, **130** interruption.

Templates are declarative JSON with declared variables, not executable hooks. The example callback template has explicit defaults that must fit your project; ordinary creation adds no support-specific fields. [Read scripting and template details](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/usage.md).

### Any REST endpoint, without a token in the command

`jira api` calls any Jira Cloud REST path with your saved profile, so agents and scripts can use endpoints that have no convenience command. `--spec` looks the endpoint up in Atlassian's official OpenAPI documents first, without contacting your site.

```bash
jira api /rest/api/3/issue -X POST --spec              # permissions, scopes, body schema
jira api /rest/api/3/issue -X POST --data @issue.json  # then call it
jira api /rest/api/3/project/search --query maxResults=20
jira api /rest/agile/1.0/board/12/sprint --profile work | jq '.values[].name'
```

Response bodies go to stdout exactly as Jira returns them; failures are a JSON object on stderr. Requests stay on your site: no absolute URLs, no redirects, and auth headers can't be overridden. Writes are never retried. For unattended agents, approve keychain access once and give the agent a least-privilege account. [Read the API, discovery and agent setup guide](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/usage.md#calling-any-rest-endpoint).

## Explicit updates and releases

```bash
jira update --info
jira update --check
jira update --yes
```

Standalone updates select a compatible GitHub Release binary, verify its manifest/hash/size, validate version/help, and retain a `.previous` backup. Windows completes replacement through a separate helper. Config and credentials stay untouched; ordinary commands never auto-update.

For pipx/uv/Python installations, `update` gives instructions for the owning manager. Public downloads need no Jira token; an optional GitHub token can increase API rate limits. [Update, verification and rollback details](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/migration/upgrade-to-v2.md).

Releases contain wheel/sdist, macOS arm64/x86_64, Linux x86_64 and Windows x86_64 binaries, manifest and checksums. Current native OS requirements are listed above and in the manifest. Independent attestation verification, signing and notarization remain [release-hardening work](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/sprints/v2-upgrade/roadmap.md#remaining-work-after-v21).

## Migrating from old commands

`jira` is the primary command from v2.1. Python-package installations retain **`jsup` and `jira-cli-toolkit` throughout v2.x**. Invoking either prints a startup notice on stderr; JSON stdout and internal completion/update protocols stay intact. Native installers supply the `jira` executable.

| Earlier command | Current command |
| --- | --- |
| `jsup open -p ENG` | `jira issue list -p ENG --open` |
| `jsup issue-show ENG-42` | `jira issue view ENG-42` |
| `jsup issue-move ENG-42 --to Done` | `jira issue transition ENG-42 --to Done` |

Read the [installation/credential migration guide](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/migration/upgrade-to-v2.md) and the [complete developer command migration](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/migration/legacy-commands.md). Existing migrated profiles need no second credential migration when updating from v2.0.

## Development

```bash
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

On Windows use `.venv\Scripts\python`. Tests use local fixtures and mocked Jira calls; they do not need credentials or change issues.

The landing page uses React, TypeScript, Vite, Tailwind and shadcn/ui:

```bash
cd web
npm ci
npm run dev
npm run build
npm test
```

[Website development and browser checks](https://github.com/User17745/jira-cli-toolkit/blob/main/web/README.md) · [Installer development](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/install.md) · [Release acceptance](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/sprints/v2-upgrade/acceptance.md)

## Scope and next steps

The current release supports standard **Jira Cloud** issues and applicable Software boards/sprints, and any Jira Cloud REST endpoint through `jira api`, including Service Management. Service Management convenience commands and Data Center remain future work. Required-field discovery cannot describe every app-specific workflow validator; Jira remains authoritative.

Original project code is licensed under **AGPL-3.0-only**. [See completed milestones and remaining work](https://github.com/User17745/jira-cli-toolkit/blob/main/docs/sprints/v2-upgrade/roadmap.md).

## Independent project and intellectual property notice

CLI Toolkit for Jira is independently developed and maintained. It is not affiliated with, sponsored by, endorsed by, or otherwise associated with Atlassian or any of its affiliated business entities. It is not an official Jira product.

References to Jira and Atlassian, including the `jira` command name, identify the external service and describe compatibility and usage. They do not claim ownership of those names or imply an official relationship. Jira and Atlassian are trademarks of Atlassian.

No infringement of third-party trademarks, copyrights, patents, or other intellectual property rights is intended. This statement does not establish that a particular use is non-infringing or replace any permission that may be required.

## License

Copyright © 2026 Abhishek Aggarwal. Original project code is licensed under the **GNU Affero General Public License, version 3 only (AGPL-3.0-only)**. You may redistribute and modify it under that license. It is provided **without warranty**, including any implied warranty of merchantability or fitness for a particular purpose. See [LICENSE](https://github.com/User17745/jira-cli-toolkit/blob/main/LICENSE) for the complete terms and [NOTICE](https://github.com/User17745/jira-cli-toolkit/blob/main/NOTICE) for the project notice.

Third-party components and assets retain their own copyright notices and applicable license terms; preserve those notices when redistributing them. This does not remove applicable AGPL obligations for covered combined works. The project license does not grant rights to third-party trademarks. [Website third-party notices](https://github.com/User17745/jira-cli-toolkit/blob/main/web/public/third-party-notices.txt) are included separately.
