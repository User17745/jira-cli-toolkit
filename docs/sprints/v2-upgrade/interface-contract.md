# Foundation interface and migration contract

Decision date: 6 October 2026

This document records the foundation interface decisions. Current implemented features, migration guidance and validation are documented in the [migration guide](migration.md), [roadmap](roadmap.md), and [acceptance evidence](acceptance.md). Foundation-only descriptions below are historical.

## Product identity and compatibility

The repository/product is **Jira CLI Toolkit**, hosted at [User17745/jira-cli-toolkit](https://github.com/User17745/jira-cli-toolkit). The executable is `jira-cli-toolkit`. Keep the Python distribution/import package `jsup` during the upgrade so existing installations and imports retain their identity. A separate package rename is outside this milestone.

Do not install a `jira` executable: [JiraCLI](https://github.com/ankitpokhrel/jira-cli/wiki/Installation) and [go-jira](https://github.com/go-jira/jira) already use that name. Users may choose their own shell alias. No package-registry publication is part of this change.

The source version is `2.0.0`. Release validation is recorded in the acceptance evidence. Keep the `jsup` executable and all existing command names throughout v2.x. Removal requires a separately announced major release and migration instructions. Both executables accept grouped and legacy command spellings, with shared application operations.

## Product position and initial capability scope

[Atlassian ACLI](https://developer.atlassian.com/cloud/acli/reference/commands/jira-workitem/) and [JiraCLI](https://github.com/ankitpokhrel/jira-cli) already cover common issue operations. This tool's intended value is simple local context, project-aware guided field discovery, reusable team templates, and predictable scripting. Field discovery and templates remain later milestones; the first milestone provides their command/application foundation.

| Jira capability | Foundation behavior | Later work |
| --- | --- | --- |
| Standard Cloud issues | Existing create/view/transition/delete/comments plus general JQL listing | Metadata-aware creation, editing, required custom fields, relationships, attachments |
| Team-managed/company-managed projects | No fixed project keys or status names; API permissions govern access | Acceptance matrix for differing field/workflow configurations |
| Business/non-software projects | Standard issue operations when supported; software features are explicit commands | Capability discovery and clearer unsupported-operation diagnostics |
| Software boards/sprints | Existing operations retained; board viewing added | Complete pagination and richer planning operations |
| Service Management projects | Standard issue operations only; no claim that issue creation creates a customer request | Request types/fields and internal/public comments via JSM APIs |
| Data Center | Outside the initial Cloud release | Separate transport/auth/capability adapter |
| App-defined custom fields/validators | Jira may reject operations; do not fabricate support | Typed field input, metadata, and documented limitations |

There is no hardcoded set of valid project keys, issue statuses, or board IDs. This does not guarantee that every operation is available to every account or project. The existing `Task` creation default remains visible in help until issue-type discovery is implemented; users can override it.

## Command and help grammar

Use `<executable> <resource> <action>`; comments and features use one additional resource level. Implement the grouped equivalents in the roadmap's migration table, including `sprint edit --state` for supported state changes. `issue transition` names a workflow action, not a move to another project.

`--help`, `help`, `help <resource> <action>`, and `--version` require neither credentials nor network access. An incomplete resource group prints its help without contacting Jira. Unknown help paths exit with a usage error.

Inherited global flags work before, between, and after subcommands. If a flag is supplied repeatedly, its last explicit occurrence wins. Subparser defaults must not overwrite an earlier explicit value.

The new root command shows only resolved site/project context and common commands, locally. It excludes email and tokens. `context show` exposes the same local view. `jsup` without arguments retains its dashboard behavior, but the dashboard now uses selected projects rather than the original hardcoded keys.

## Project selection and queries

Schema 2 profiles select one site/account identity atomically. Explicit `--profile` (or `JIRA_PROFILE`) uses that profile and ignores identity environment variables; identity flags cannot be combined with profile selection. Complete identity flags override a complete environment identity, which otherwise overrides the active profile. Partial flag/environment identities are rejected rather than borrowing another profile's token. Project overrides remain independent: flag, environment, selected profile. The legacy file remains usable until `config migrate` succeeds.


`issue list` defaults to the selected project's issues, including Done, ordered by update time. `--open` adds `statusCategory != Done`. `--jql` is a complete query: it ignores the saved/environment default project and cannot be combined with explicit `--project` or `--open`. This avoids silently rewriting user queries. `--limit`/`--max` bounds total fetched results across pages; `--all` retrieves every page. Search uses the supported enhanced POST endpoint and cursor tokens; the deprecated search fallback has been removed.

Legacy `open --jql` keeps its original meaning: append an additional condition to the project's unfinished-issue query. Generated project conditions quote the supplied identifier.

`dashboard` uses `--projects KEY ...`, or the selected default project. It requires explicit selection when no project is configured and deduplicates keys. It uses Jira's [approximate-count API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/) and labels estimates. Authentication/permission failures exit unsuccessfully rather than looking like successful counts.

Grouped `board list` uses the selected project when present. Legacy `board-list` continues to list all accessible boards unless `--jql-project` is supplied.

Generic issue creation injects no callback labels, components, or description patterns. Explicit legacy `intake` retains those assumptions until the callback template milestone.

## Browser operations

Issue `view --web`, board `view --web`, and legacy `browse` require a site URL only. They rely on the user's browser session and do not require or test API credentials. Issue keys are URL-encoded. Board viewing uses the [project-independent board URL](https://support.atlassian.com/migration/kb/issue-source-of-type-board-with-value-board_id-could-not-be-found/) so a default project cannot route users to the wrong board. A failed browser launch reports the URL for manual opening.

## Input and output contract

`--no-input` never prompts. Commands requiring missing interactive values report the needed flags and exit with code 2. Piped/nonterminal input is treated the same way. Complete `intake`, explicit transitions, and confirmed deletion remain usable in scripts. JSON output is independent of confirmation: deletion still requires `--yes` or interactive confirmation.

Successful API output retains the returned payload rather than introducing a new response envelope in this foundation. New local/browser outputs are small objects:

```json
{"site": "https://example.atlassian.net", "project": "ENG"}
```

```json
{"url": "https://example.atlassian.net/browse/ENG-1", "opened": true}
```

New dashboard output contains `site` and `projects`; each result contains its `project`, approximate `count`, and `approximate: true`. Per-project non-auth API failures may instead contain a null count and an error message. Legacy `jsup dashboard --json` and `jsup --json` retain the original project/hint payload and do not fetch counts. New grouped commands under `jira-cli-toolkit --json` report runtime errors as `{"error":{"code":"jira_error","message":"...","status":401}}` (status is present for HTTP errors). Successful API objects retain their payload shape; paged objects add `fetched`. Legacy aliases and the `jsup` executable keep errors on stderr. Argparse usage errors remain on stderr with exit 2.

Progress goes to stderr; JSON stdout contains a result or the documented runtime error object. `config show --json` reports whether a saved token exists without printing it. Human `config show` retains the existing masked token suffix. Interactive `config init` rejects `--json` rather than producing mixed JSON/prompt output.

| Exit code | Meaning |
| --- | --- |
| 0 | Success, including help/version |
| 1 | Jira/API or network failure |
| 2 | Usage, missing configuration/input, declined confirmation, or local file failure |
| 130 | Interrupted input/operation |

## Authentication boundary

`auth login` validates the token through `/myself` before saving a profile. Interactive setup explains token creation and permissions, hides token input, and offers accessible projects. `--token-stdin` and complete environment credentials support scripts. Native macOS Keychain, Windows Credential Manager, Secret Service, or KWallet stores hold tokens; preferences contain credential references only. No implicit plaintext fallback is allowed. Explicit `--storage file` writes a separate POSIX mode-0600 credential file; Windows users use the native store or environment authentication.

`auth status` validates the selected identity and reports its source without printing the token. `auth logout` deletes the selected local credential, does not revoke the upstream token, and does not clear externally provided credentials. Profile removal never silently selects another identity. `context show` and browser routing inspect local preferences without opening the keychain. `doctor` checks identity and configured project access. `config migrate` validates the legacy identity, stores its token, then atomically replaces preferences; failed storage leaves the old file intact.

A 401 from a selected profile offers interactive token replacement when input is available. Recovery checks that site/account stay unchanged, and the original operation is never automatically replayed. Scripts return a deterministic error with an `auth login` instruction. Scoped personal tokens route API requests through `api.atlassian.com/ex/jira/<cloud-id>` while browser links retain the site URL. API-token expiry remains unknown; there is no automatic refresh.

The user selected API-token login instead of OAuth for v2 (6 October 2026). Token setup must explain how to create a personal token, respect its scopes and the account's project permissions, and support the scoped-token API gateway. API tokens cannot be refreshed automatically. A 401 means authentication failed; it does not prove expiration. OAuth application ownership and refresh support are deferred. [Atlassian API-token instructions](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/).

## Verification and next milestones

The foundation is tested using local fixtures and mocked Jira calls, covering grouped/legacy compatibility, flag placement, help, context, project selection, creation metadata isolation, browser routing, input handling, output, and failures. Packaging checks build and install the same source as a wheel with both entry points. No real Jira tickets are created or changed by these checks.

Complete Sprint 2 transport/pagination/output handling next. Then implement the explicit auth/profile/context design and metadata-aware creation. The updater and automated GitHub binary publication remain Sprint 7; no releases are published by this foundation change.
