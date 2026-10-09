# CLI reference

A Jira Cloud CLI with grouped commands, Rich terminal output, and a compatible `jsup` executable. Repository: [User17745/jira-cli-toolkit](https://github.com/User17745/jira-cli-toolkit).

The current release is [v2.1.0](https://github.com/User17745/jira-cli-toolkit/releases/tag/v2.1.0). The command is `jira`; `jira-cli-toolkit` remains the repository name and a compatibility alias, alongside `jsup`. V2 provides guided API-token login, profiles, project/field discovery, issue maintenance, templates, completion, updates, and native releases while retaining `jsup` compatibility. Acceptance evidence and release validation are tracked in the [upgrade roadmap](sprints/v2-upgrade/roadmap.md).

v2.5 adds [authenticated requests to any REST endpoint and endpoint-spec discovery](#calling-any-rest-endpoint) for agents and scripts. See the [v2.5 roadmap](sprints/v2.5-api/roadmap.md) for design decisions.

## Install

Use the [release installation guide](migration/upgrade-to-v2.md) for verified public wheels or native binaries. If `jira` is already provided by another CLI or shell alias, choose the intended installation on PATH; the `jira-cli-toolkit` compatibility alias remains available.

### Install from this checkout

Requires Python 3.10 or later:

```bash
pipx install .
# The short command and both compatibility aliases are installed:
jira --version
jira-cli-toolkit --version
jsup --version
```

If `jsup` is already installed, use `pipx install --force .` from the desired checkout to replace the installation. If an existing uv-backed pipx environment refuses force installation, follow the [migration recovery](sprints/v2-upgrade/migration.md#one-time-bootstrap). The explicit updater and tag-triggered release workflow are described below. The Python package remains `jsup` for compatibility.

## Migrating from old jsup versions

- [Upgrade to v2](migration/upgrade-to-v2.md): verified release downloads, pipx/uv/Python and standalone installation paths, the pipx uv-backend recovery, credential migration and rollback.
- [Developer command migration](migration/legacy-commands.md): every old command mapped to its grouped equivalent, behavior changes, JSON/exit-code handling and unattended script examples.

The package remains `jsup`; all three executables and legacy command names are supported throughout v2.x. Version 0.2 needs a one-time manager upgrade before it gains the updater. Already-migrated RC1 users can upgrade to stable without migrating credentials again.

Invoking `jsup` or `jira-cli-toolkit` prints a startup warning on stderr pointing to `jira`. Legacy names remain supported throughout v2.x and may be deprecated in a future major release. JSON stdout remains unchanged; internal completion/update helpers suppress the notice.

## Setup and help

```bash
jira auth login --profile work
jira user me
jira --help
jira help issue create
jira issue comment --help
```

Help and version commands work without configuration or network access. An incomplete command group displays its help.

New users should use the guided `auth login` flow below. Legacy `config init` remains compatible until credentials are migrated; it writes a plaintext token. `config migrate` moves that identity to a named profile and the selected credential store. API tokens cannot refresh automatically.

## Local context and dashboard

```bash
jira                                     # Local site/project context and tips
jira context show --json     # Local view without email or token
jira dashboard -p ENG
jira dashboard --projects ENG HR
```

The dashboard requires a selected project or explicit `--projects`; it does not query a fixed list of projects. Counts use Jira's estimate API and are labeled approximate. The legacy `jsup` root still opens the dashboard. Its JSON dashboard retains the original project/hint payload; use the new executable for dashboard results.

## Issue workflows

```bash
jira issue list -p ENG
jira issue list -p ENG --open
jira issue list --jql 'assignee = currentUser()' --json
jira issue create -p ENG --type Task --summary "Review onboarding"
jira issue view ENG-42
jira issue view ENG-42 --web
jira issue transitions ENG-42
jira issue transition ENG-42 --to "In Progress"
jira issue comment add ENG-42 -m "Review started"
jira issue comment list ENG-42
```

`issue list` includes Done issues unless `--open` is supplied. Its `--jql` is a complete query: it ignores the configured default project and cannot be combined with explicit `--project` or `--open`. Legacy `open --jql` retains its original extra-filter behavior. `--limit` (alias `--max`) bounds total fetched results across pages; `--all` follows every page.

Creation accepts type, priority, account-ID assignee, repeated labels/components, descriptions, and description files. Grouped creation discovers project/type fields. Pass `--type Bug` in scripts or choose interactively; `project issue-types` and `project fields --type Bug` show available values. Required custom fields accept `--field FIELD=VALUE`, `FIELD:=JSON`, or `--fields-file`. Legacy `issue-create` retains its Task default. Generic creation does not add support-specific metadata. The explicit legacy `jsup intake` wizard still creates callback issues with the `callback` label and `ops-runbook` component, using its explicit callback compatibility template.

## Boards, sprints, and components

```bash
jira board list -p ENG
jira board create -p ENG --name "Engineering" --type scrum
jira board view 123 --web
jira board issues 123
jira sprint list --board 123
jira sprint create --board 123 --name "Planning 1"
jira sprint add-issues 456 ENG-42 ENG-43
jira sprint start 456
jira sprint close 456
jira component list -p ENG
jira project list
```

Software operations require applicable boards and Jira permissions. Feature toggles are under `board feature enable/disable`. Sprint viewing/editing and required start/close inputs are implemented. Operations remain subject to board capabilities and Jira permissions. `view --web` and legacy `browse` require only a site URL and use the browser's session. Board URLs do not guess a project from local configuration.

## Calling any REST endpoint

`jira api` sends a request to a Jira Cloud REST path using the selected identity. The token never appears in the command, so agents and scripts can call endpoints that have no convenience command.

```bash
jira api /rest/api/3/myself --profile work
jira api /rest/api/3/project/search --query maxResults=20 --query expand=lead
jira api /rest/api/3/issue -X POST --data @issue.json
jira api /rest/api/3/search/jql -X POST --data @- < query.json
jira api /rest/api/3/issue/BUG-703/attachments -X POST --form file=@proof.txt -H 'X-Atlassian-Token: no-check'
jira api /rest/api/3/attachment/content/10001 --output proof.png
```

- **Method:** GET by default. Other methods need `-X`. A body never changes the method, so `--data` without `-X POST`, `PUT`, `PATCH` or `DELETE` is an input error.
- **Path:** a relative path starting with `/rest/` on the selected site, or on the scoped-token gateway. Absolute URLs, other hosts, query strings in the path, `.`/`..` segments, encoded slashes and non-ASCII characters are rejected. Pass query values with `--query KEY=VALUE`; the CLI encodes them.
- **Bodies:** `--data` takes JSON inline, from `@file` or from `@-` (stdin). It must parse as JSON and is sent byte for byte. `--raw-data` sends other formats and needs `--content-type`. `--form NAME=VALUE` or `NAME=@FILE` builds a multipart upload. Choose one body option. Data is limited to 10 MiB, uploads to 50 MiB.
- **Headers:** `-H 'Name: value'` adds headers such as `X-Atlassian-Token` or `X-ExperimentalApi`. The CLI manages authentication, cookies, host, content type and length, proxies and connection headers, and rejects attempts to set them.
- **Output:** the response body goes to stdout exactly as Jira returned it, whatever its JSON shape. On a terminal, JSON is indented and binary bodies are not printed; use `--output FILE` to save a body to a new file (it never overwrites). Empty, 204 and HEAD responses print nothing. `--include` prints the status and response headers to stderr, with cookies redacted.
- **Errors:** every failure is a JSON object on stderr, so stdout stays clean for pipes: `{"error": {"code", "message", "status", "method", "path", "body"}}`. HTTP 4xx/5xx and redirects exit 1, as do network errors and unknown write outcomes. Input errors exit 2. Tokens and the derived Basic auth value are redacted from error output.
- **Safety:** redirects are never followed. GET, HEAD and OPTIONS retry briefly on rate limits and transient errors. Other methods are sent once; if the connection drops during a write, the outcome is reported as unknown and is not replayed. An authentication failure never switches identity or prompts to replace the token.

### Fetching every page

Jira splits long results into pages, using three different protocols. `--paginate` follows whichever one the endpoint uses and prints a single merged JSON result.

```bash
jira api /rest/api/3/project/search --paginate
jira api /rest/api/3/search/jql -X POST --data '{"jql":"project = ENG","fields":["summary"]}' --paginate --max-items 500
jira api /rest/servicedeskapi/servicedesk --paginate
```

- **Protocols:** offset pages (`startAt`, `maxResults`, `total` or `isLast`), cursor pages (`nextPageToken`, used by issue search) and Service Management pages (`start`, `limit`, `isLastPage`). The items can be in `values`, `issues`, `comments` or `worklogs`.
- **Result:** the first page's JSON object, with every item in its list, `fetched` set to the item count, and `isLast` (or `isLastPage`) false if `--max-items` stopped it early. Page size still comes from your own `--query maxResults=` (or `limit=`, or `maxResults` in the search body).
- **Methods:** GET, and POST only for `/rest/api/3/search/jql`, where the cursor goes into the JSON body. `--output` and `--include` can't be combined with it.
- **Limits:** `--max-items N` stops after N items. It also stops after 1,000 pages, and if a cursor repeats or the format changes between pages. A failure on any page prints nothing on stdout and names the page in the error.

### Looking up an endpoint before calling it

`--spec` describes an operation from Atlassian's official OpenAPI documents and sends nothing to Jira. It needs no profile and never reads the credential store.

```bash
jira api /rest/api/3/issue -X POST --spec
jira api /rest/api/3/issue/BUG-703 --spec          # concrete paths match /issue/{issueIdOrKey}
jira api /rest/agile/1.0/board/1523/sprint --spec
jira api spec refresh                               # check for newer documents
jira api spec status                                # what is cached, from where, and how old
```

The output is JSON: the matched template and path parameters, operation ID, summary, the permissions Jira documents, OAuth and Connect scopes, deprecated and experimental flags, parameters, the request body schema with its example, the success response schema, error codes, and the source document's version, hash and fetch time.

- **Sources:** the Jira Cloud platform (`/rest/api/…`), Jira Software (`/rest/agile/…` and related) and Jira Service Management (`/rest/servicedeskapi/…`) documents at developer.atlassian.com. Nothing else is fetched; Data Center APIs and other Atlassian products are not covered.
- **Matching:** concrete paths match templates, and literal segments win over parameters, so `/rest/api/3/issue/createmeta` is not read as an issue key. If the path is documented but not for the method, the error lists the documented methods.
- **References:** schema references are expanded only from inside the same document. Recursive schemas are marked once and not repeated, and expansion stops at a fixed depth and size.
- **Cache:** the first lookup downloads the needed document. `jira api spec refresh` checks all three with conditional requests, so unchanged documents cost one small request. The cache lives in `~/.cache/jira-cli-toolkit/api-specs` (`%LOCALAPPDATA%` on Windows, `XDG_CACHE_HOME` if set), each file is checked against its recorded hash, and a failed or invalid refresh keeps the previous copy. Lookups work offline from the cache; documents older than 30 days are marked `stale` with a note to refresh.
- **Advisory only:** a missing or stale spec never blocks a request. If an endpoint isn't in the cached documents, `--spec` says so, and `jira api` can still call it.
- **Your site differs:** a spec describes the API, not your project. Required fields, allowed values, screens, transitions and permissions depend on the project and account, so discover them at runtime with `jira project fields KEY --type TYPE`, `jira issue transitions KEY` or the matching REST endpoints.

### Setting up an agent or script once

Agents and scripts run without a terminal. In that mode the CLI never opens a credential dialog, so a run either reads the saved token silently or fails at once with exit 2 and an `invalid_input` error. It never waits on a prompt nobody will answer. Set it up once, in a terminal:

1. Save the identity: `jira auth login --profile work`. On macOS and Windows the token goes to the OS credential store.
2. **macOS:** run `jira auth status --profile work` in a terminal. If macOS asks whether `jira` may use the `jira-cli-toolkit` keychain item, choose **Always Allow**. Later runs without a terminal read it silently. Approval belongs to the executable, so after an update replaces `jira`, run this step again if a scripted call starts failing with “Could not read the OS credential store without approved access”.
3. **Windows:** Credential Manager needs no approval; nothing more to do.
4. **Linux:** desktop wallets can show an unlock dialog that can't be suppressed, so scripted runs don't use them. Give the agent a complete environment identity (`JIRA_SITE`, `JIRA_EMAIL` and `JIRA_API_TOKEN` together), or create the profile with `jira auth login --profile agent --storage file`, which keeps the token in a mode-600 file.
5. Point the agent at the profile with `--profile work` or `JIRA_PROFILE=work`, and pass `--no-input` so missing values fail instead of prompting:

```bash
JIRA_PROFILE=work jira api /rest/api/3/myself --no-input
```

### What keeping the token out of the command does and doesn't protect

Keeping the token out of the command keeps it out of prompts, shell history, process listings, logs and generated scripts. It is not isolation: any program running as you, including an agent allowed to run commands, can run `jira api` too, and some can read the credential store or the CLI itself. Every request runs with the full permissions of the Jira account behind the profile.

To limit what an agent can do:

- **Least privilege:** give the agent its own Jira account, added only to the projects it needs, with only the permissions those tasks require. Save it as a separate profile (`jira auth login --profile agent`) and point the agent at that profile.
- **Scoped tokens:** an API token with scopes (`jira auth login --profile agent --scoped`) limits which API families the token can use, as listed in each operation's `scopes` in `--spec` output. Jira project permissions still apply on top.
- **Real isolation:** if the agent must not be able to use the token beyond specific calls, run it where it can't reach the credential store, and give it a broker instead: a separate service running under its own OS account that holds the token, allows only approved methods and paths, and forwards those requests. An agent tool policy that only allows specific `jira api` invocations is a lighter version of the same idea; it is enforced by the agent host, not by this CLI.

### Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `invalid_input`: “Could not read the OS credential store without approved access” | macOS hasn't approved keychain access for this `jira` executable. Run `jira auth status --profile work` in a terminal and choose **Always Allow**. Repeat after an update replaces `jira`. |
| `invalid_input`: “PATH must start with /rest/” or rejects `?` | Pass a relative REST path and put query values in `--query KEY=VALUE`. |
| `--data needs an explicit method` | Add `-X POST`, `PUT`, `PATCH` or `DELETE`; a body never changes the method. |
| `jira_error` with status 303 on attachment content | Jira redirects downloads to its file service, which isn't followed. Add `--query redirect=false` and `--output FILE`. |
| `jira_error` 401 | The token is invalid, revoked or expired. Replace it with `jira auth login --profile NAME`; the CLI never switches identity on its own. |
| `jira_error` 403 or 404 on an existing resource | The account lacks project permission, or the scoped token lacks the scope in `--spec` output. |
| `uncertain_outcome` | The connection dropped during a write. Check in Jira whether it happened before sending it again. |
| `spec_not_found` | The cached documents don't describe that path or method. Run `jira api spec refresh`; the request itself can still be sent. |
| Binary response not printed | Bodies that aren't text aren't written to a terminal. Use `--output FILE`, or pipe stdout. |

## Scripts and compatibility

```bash
jira --project ENG --json issue list --open --no-input
jira issue transition ENG-42 --to Done --json --no-input
jira issue delete ENG-42 --yes --json --no-input
```

Global flags work before, between, or after subcommands; the last explicitly supplied value wins. `--no-input`, or nonterminal input, prevents prompts and reports missing flags. `--json` does not bypass deletion confirmation. JSON results and structured runtime errors go to stdout for new commands; progress and argparse usage errors go to stderr. Legacy aliases/jsup keep errors on stderr. Successful API payloads retain their original shape. Exit codes are 0 for success/help, 1 for API/network failures, 2 for usage/configuration/input/file errors, and 130 for interruption.

All three executables accept legacy commands such as `issue-show`, `issue-create`, `comment-add`, `board-list`, and `sprint-add`. Existing names, configuration keys, and environment variables are retained through v2.x. Legacy `board-list` searches all accessible boards unless `--jql-project` is supplied, while grouped `board list` uses the selected project. See the [interface and migration contract](sprints/v2-upgrade/interface-contract.md) for exact behavior and current limitations.

## Development

```bash
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Tests use local fixtures and mocked Jira calls. They do not require real Jira credentials or modify tickets. On Windows use the corresponding `.venv\Scripts\python` executable.

## Guided authentication and profiles

For a new installation, run `jira auth login --profile work`. The guided screen links to [Atlassian token creation](https://id.atlassian.com/manage-profile/security/api-tokens), hides token input, validates your account, and lets you choose a project. A token inherits your account's permissions; scoped tokens also need scopes for the operations you use. For a scoped personal token, add `--scoped` (and `--cloud-id ID` if automatic site discovery is unavailable).

Tokens are stored in your native OS credential store. Preferences remain at `~/.config/jsup/config.json`; the v2 schema contains profile references and no tokens. If no native store is available, supply a complete `JIRA_SITE`, `JIRA_EMAIL`, and `JIRA_API_TOKEN` identity for scripts. Explicit `--storage file` is a POSIX-only plaintext opt-in with a separate mode-0600 credentials file. The CLI never silently falls back to it.

Interactive commands can request OS approval for credential access. Scripted commands (`--json`, `--no-input`, or nonterminal stdin) suppress macOS Keychain dialogs and fail with instructions if access needs approval. Linux wallets are reserved for interactive use because their unlock dialogs cannot be suppressed reliably; scripts use a complete environment identity or explicit POSIX file storage. Windows uses its native credential store without an unlock prompt.

Existing users run `jira config migrate` to validate and migrate their saved identity safely. Then use `profile list`, `profile use work`, `context use --project ENG`, `auth status`, and `doctor`. Local `auth logout` does not revoke the token at Atlassian or clear externally supplied credentials. API tokens cannot refresh; an invalid/expired/revoked token must be replaced with `auth login`. Recovery never replays a write automatically.

A selected `--profile` owns its full site/account identity. Complete identity flags or environment variables can supply another identity when no profile is explicitly selected; partial identities are rejected for schema-2 users. A project override does not change accounts.

## Explicit updates and releases

`jira update --info` shows local installation details. `update --check` checks the latest stable GitHub Release without changing the installation. Select a candidate with `update --version VERSION --prerelease --check`; a downgrade needs `--allow-downgrade`. A standalone update needs `--yes` in scripts, verifies the release manifest and binary SHA-256/size, runs version/help checks, and retains a `.previous` executable for rollback. Windows uses a separate helper after the old process exits; pending updates report a log path. Config and credentials are untouched.

**Updating a 2.1.0 standalone binary:** run `jira update --yes --json`. Without `--json`, 2.1.0 replaces itself successfully but then crashes while printing the result (`zlib.error … incorrect header check`); the update has still completed, and `jira --version` shows the new version. From 2.5, the updater loads everything it needs before replacing the executable.

The repository and release downloads are public. The updater works without GitHub login; an optional `GH_TOKEN` or authenticated `gh` account can raise API rate limits. Jira tokens are never used for GitHub. Homebrew installations (`brew install user17745/tap/jira-cli-toolkit`) are upgraded with `brew upgrade jira-cli-toolkit`; `jira update` says so instead of replacing files Homebrew owns. The tap checks for new GitHub releases daily. Package installations receive an exact-version command for their owning pipx, uv or Python environment, such as `pipx install --force 'jira-cli-toolkit==2.5.1'`; the updater does not overwrite manager shims. From 2.5.1 the package is on PyPI as `jira-cli-toolkit`, so `pipx upgrade jira-cli-toolkit` also works. Installations made before 2.5.1 use the package's old name, `jsup`; the updater says so and gives the one-time switch for pipx, uv or pip (uninstall `jsup`, then install `jira-cli-toolkit`), which keeps configuration and saved credentials. Don't install both side by side: they ship the same module. To install offline, download the release wheel, verify its manifest checksum, and pass its path to the same command. Version 0.2.0 needs this one-time bootstrap before it gains an update command.

If pipx’s uv backend refuses force installation because the venv exists, adding `--backend pip` does not switch that existing environment in pipx 1.14.0. Download and verify the wheel, run `pipx uninstall jsup`, then `pipx install --backend pip /path/to/jsup.whl`. The [migration guide](sprints/v2-upgrade/migration.md) explains this recovery and preservation of saved credentials. Manager detection uses installation receipts, including custom pipx/uv directories.

GitHub Actions builds and smoke-tests Python packages and native binaries. Version tags publish a complete manifest, checksums, wheel/sdist, and macOS arm64/x86_64, Linux x86_64, and Windows x86_64 executables. Prereleases never become latest stable; stable publication additionally requires a commit on main. After the GitHub release is published, the same wheel and sdist are uploaded to PyPI through trusted publishing: PyPI accepts uploads only from this repository's `release.yml` in the protected `pypi` environment, and no PyPI token is stored. Release candidates are uploaded too; pip skips them unless a version is pinned or `--pre` is passed. Native platform requirements are recorded in each release manifest. Checksums detect corruption; publisher trust currently relies on GitHub HTTPS. Optional GitHub attestations can be enabled with repository variable `RELEASE_ATTESTATIONS=true` when the repository’s plan supports them; for private repositories this requires [GitHub Enterprise Cloud](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations). When enabled, publication requires attestation success. Verify each downloaded artifact separately with `gh attestation verify ARTIFACT --repo User17745/jira-cli-toolkit`; the updater does not perform this verification. Attestations are enabled for releases from 2.5.1. Code signing and notarization remain release-hardening tasks.

## Maintaining issues

Use `issue edit ENG-42 --summary "Updated" --add-label triaged --remove-label stale` for incremental changes. `--label`/`--component` replace their collections; use `--field labels:=[]` to clear an optional collection. Edit metadata controls available fields and add/remove operations. `issue assign ENG-42 --user me` selects your account, while `--user id:ACCOUNT_ID` bypasses ambiguous display names; `issue unassign` clears assignment when permitted.

`issue list` supports assignee, repeated statuses/labels, type, board, fields and ordering. A board search uses the board scope and ignores a configured default project unless `--project` is explicit. Complete `--jql` cannot be mixed with generated filters. `issue link ENG-1 ENG-2 --type Blocks --direction outward` makes ENG-1 the API's outward/from issue; inspect the link type's inward/outward labels for its meaning. `issue unlink LINK_ID --yes` removes the link.

Comments support add/edit/delete and `--message-file`/interactive `--editor`. Attachments support list/upload/download/delete; downloads reject existing destinations and remove partial files, and uploads respect site limits with a 50 MiB client limit per request. Link/comment/attachment deletion requires `--yes` for scripts. Metadata does not expose every workflow validator; server validation remains authoritative.

## Templates, completion, and output

`template list` and `template show callback` are local. `template validate callback --project ENG` checks its defaults against the project's metadata. `issue create --template callback --var name=Example --var issue="Login failed"` uses the example workflow; explicit fields/flags override its defaults. The `ops-runbook` component is explicit in this template: replace it with `--component ExistingComponent` or clear it using `--field components:=[]` on a compatible project. Generic creation has no callback metadata.

Share JSON schema-1 templates by path or save them at `~/.config/jsup/templates/NAME.json`. Supported keys are `name`, `type`, `summary`, `description`, `fields`, and `variables`. Patterns use declared `{variable}` names only; hooks, attribute expressions, and format conversions are rejected. Keep credentials out of templates. Legacy `intake` uses the same callback pattern with its compatibility payload; migrate to ordinary template creation for project-aware validation.

Generate completions with `completion bash`, `completion zsh`, or `completion fish` and load the output using your shell's usual completion setup. Completion uses the parser and local profile preferences, never network authentication. Lists accept `--csv --columns key,summary,status,assignee` for scripts; issue tables accept `--columns` for display as well. JSON preserves API field structures.
