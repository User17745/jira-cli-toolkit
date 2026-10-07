# Jira CLI v2 upgrade roadmap

Created: 6 October 2026

Status: [stable v2.1.0](https://github.com/User17745/jira-cli-toolkit/releases/tag/v2.1.0) is published and verified as latest stable; it adds the short `jira` command and public distribution to the completed v2.0 foundation. Initial v2 Sprints 0–8 are complete, including live BUG acceptance, package bootstrap, user-verified macOS Keychain migration/status, CI/native builds and actual RC-to-stable update checks. See [acceptance evidence](acceptance.md). Optional extensions and the separately planned v2.5 remain future work.

## Goal

Turn the current support-oriented CLI into a general-purpose Jira Cloud tool. A user should be able to authenticate, select an unfamiliar project, discover its requirements, and create, update, and transition issues without changing Python code or knowing the original project's conventions.

Jira defines the available fields, issue types, workflows, and permissions. The CLI discovers those capabilities, offers useful defaults, and lets teams add optional templates.

## Tracking and scope

Every actionable item has a checkbox. Check implementation tasks after the change and its required verification are complete. Check a sprint's completion criteria only when the described user behavior has been demonstrated. Record decisions and evidence alongside the relevant item as work proceeds.

The initial release targets standard issue operations across Jira Cloud project types, within the capabilities and permissions exposed by Jira. Service Management customer requests and Data Center support are separate extensions. Arbitrary app-defined fields and validators cannot be assumed to be fully discoverable.

The repository is [User17745/jira-cli-toolkit](https://github.com/User17745/jira-cli-toolkit), renamed from `jira-support-cli` to reflect the broader product scope. The user authorized public visibility on 7 October 2026. V2.1 installs `jira` as the primary command, retaining `jira-cli-toolkit` and `jsup` compatibility aliases throughout v2.x. Public release downloads require no Jira or GitHub token. The Python package remains `jsup`. See the [interface contract](interface-contract.md) for implemented behavior and migration decisions.

## Tested delivery checkpoints

Before every push: run the complete regression suite plus tests for the changed behavior, build the wheel/sdist, and smoke both installed entry points in an empty home. Push each substantial, reviewable milestone; record its commit and GitHub Actions result here. Failed checks must be fixed before the next milestone is marked complete. CI supplements local testing and does not replace it.

- [x] Foundation: regression tests and isolated package smoke checks; commit `8e0d8e6` pushed to `codex/v2-foundation` (draft PR #1).
- [x] CI foundation: test/build/install smoke jobs pass locally and on GitHub; push and record the run.
- [x] Sprint 2 reliability: new transport/pagination/output tests plus regressions and installed smoke checks; commit/push and verify CI.
- [x] Sprint 3 authentication: credential/config/recovery tests plus regressions and installed smoke checks; commit/push and verify CI.
- [x] Sprint 4 discovery: required-field/metadata tests plus regressions and installed smoke checks; commit/push and verify CI.
- [x] Sprint 5 maintenance: issue-operation tests plus regressions and installed smoke checks; commit/push and verify CI.
- [x] Sprint 6 workflows: template/completion/output tests plus regressions and installed smoke checks; commit/push and verify CI.
- [x] Sprint 7 distribution: release/updater tests plus regressions, native binary smoke checks, and GitHub release-candidate validation; commit/push and record evidence.
- [x] Sprint 8 RC evidence: regression/package checks and migration/live acceptance evidence; commit/push verified documentation and record CI results. Stable promotion remains a separate unchecked gate below.

## Repository housekeeping

- [x] Rename `User17745/jira-support-cli` to `User17745/jira-cli-toolkit` on GitHub and verify the canonical repository URL.
- [x] Update this checkout's `origin` after the rename succeeds; preserve GitHub's old-name redirect and verify repository access. Leave other local clones to their owners.
- [x] Review links, badges, installer URLs, release/updater endpoints, package metadata, and repository integrations for references to the old name as the related features are built; retain intentional legacy references in migration documentation.

Verification on 6 October 2026: canonical and old-name API URLs resolve to repository ID `1372895342`; visibility and default branch are unchanged. This checkout's origin is `git@github.com:User17745/jira-cli-toolkit.git`. Authenticated HTTPS Git access succeeds; the current execution environment's SSH key is not accepted, so SSH access was not verified. The intermediate `jira-toolkit` name also redirects to the final repository name. No updater implementation, workflow files, or release publication is included in the foundation milestone.

## Current baseline

At planning time the package was `jsup` version `0.2.0`, with an argparse command handler, a requests-based Jira client, Rich output, and no test suite. The table below records that historical baseline; implementation progress is tracked in the checklist and evidence below.

| Area | Current behavior | Target behavior |
| --- | --- | --- |
| Project defaults | Dashboard queries `RP`, `RD`, and `BUG` | Selected or explicitly configured projects |
| Intake | Fixed callback description, `callback` label, and `ops-runbook` component | Optional, validated callback template |
| Command structure | Flat commands such as `issue-create` | Resource/action groups with legacy aliases |
| Help | Root and per-command `--help` | Retain `--help`; add `help` and completion |
| Credentials | Plaintext token in `~/.config/jsup/config.json`, mode `0600` | Named identities and OS credential storage |
| Auth fallback | Flags, then environment, then config; checks presence | Explicit credential selection, validation, and recovery |
| Auth lifecycle | Manual `me` check; no refresh or login recovery | Login/status/logout, guided token replacement, clear failure handling |
| Issue fields | Fixed flags; no creation metadata discovery | Project/type metadata, typed values, required-field prompts |
| Issue maintenance | Create, view, transition, delete, comments | Editing, assignment, relationships, attachments |
| Lists | One response page | Explicit limits and complete pagination |
| Scripts | JSON on many paths; prompts can still occur | Consistent JSON, exit codes, and strict noninteractive mode |
| Updates | No update command or release discovery | Installation-aware updates from GitHub Releases |
| Distribution | Install from source; no checked-in CI/CD | Tested, versioned binaries and Python packages on GitHub Releases |

Implementation references: [commands](../../../src/jsup/cli.py), [client](../../../src/jsup/client.py), [configuration](../../../src/jsup/config.py), [UI](../../../src/jsup/ui.py), [packaging](../../../pyproject.toml), and [README](../../../README.md).

## Implementation evidence — foundation milestone

- Product/repository: `jira-cli-toolkit`; new executable: `jira-cli-toolkit`; compatible package/executable: `jsup`. Unreleased version: `0.3.0.dev0`. Repository visibility and default branch are unchanged.
- [Interface and migration decisions](interface-contract.md) cover Cloud scope, command grammar, legacy compatibility through v2.x, local root/context behavior, JQL precedence, current output, and auth boundaries.
- Parsing lives in `commands.py`, application operations in `application.py`, configuration in `config.py`, transport in `client.py`, rendering in `ui.py`, and entry points in `cli.py`.
- Verification on 6 October 2026: 35 unit tests pass on Python 3.14.5, using mocked Jira calls. They cover nested flag placement, grouped/legacy commands and payloads, local help/context, project-neutral creation/dashboard, explicit callback intake, browser routing, no-input behavior, setup compatibility, and failures.
- Wheel and source distribution build successfully. Both wheel-installed executables pass help/version checks from an isolated home/directory; new root/context JSON works without credentials. Source syntax was checked for Python 3.10 compatibility; runtime checks across the full advertised Python/OS matrix remain a release task.
- Early Sprint 2 improvements include bounded request timeouts, quoted generated project JQL, session cleanup, consistent network/follow-up error handling, and stderr progress. Full pagination, retries, structured errors, and comprehensive transport verification remain unchecked.
- The historical foundation did not include profiles, discovery, templates, CI/CD, updater, or release publication. Current progress is recorded in the milestone evidence and checklist; OAuth is deferred by user decision. No real Jira issues were created or changed.

## Delivery sequence

These are ordered work packages, not calendar or effort commitments. Each sprint includes verification for its own changes; the release sprint adds cross-feature acceptance checks.

| Sprint | Outcome | Dependencies |
| --- | --- | --- |
| 0 | Product scope and interface contracts | None |
| 1 | Project-neutral CLI and compatibility layer | 0 |
| 2 | Reliable API transport, pagination, and script output | 0–1 |
| 3 | Authentication, profiles, contexts, credential migration | 0–2 |
| 4 | Project discovery and metadata-aware fields | 2–3 |
| 5 | Essential issue maintenance and collaboration | 1–4 |
| 6 | Reusable workflows and daily-use polish | 3–5 |
| 7 | CI/CD, GitHub Releases, and update command | 0–3; v2 promotion also requires 4–6 |
| 8 | Release validation, documentation, and distribution | 0–7 |

## Sprint 0 — Product scope and contracts

- [x] Compare the intended experience with Atlassian ACLI and existing Jira CLIs; record the value of guided field discovery, simple contexts, reusable templates, and dependable scripting.
- [x] Define the initial Jira Cloud support matrix, including team-managed/company-managed projects, project capabilities, permissions, and known field limitations.
- [x] Choose the public product, package, and executable names after checking relevant registries and executable collisions; decide whether `jira` is an optional alias. Keep `jsup` available during migration.
- [x] Finalize the resource/action command grammar and flag conventions; use `view`, `edit`, `list`, and `transition` consistently. Reserve `move` for a future cross-project operation.
- [x] Define the compatibility window for old commands, config keys, environment variables, argument names, and JSON behavior. Record how users opt into the new defaults.
- [x] Define credential and context precedence, distinguishing an explicitly selected identity from per-command project/board overrides; reject ambiguous identity combinations.
- [x] Define interactive behavior, root-command behavior, noninteractive behavior, output schemas, pagination controls, and exit codes.
- [x] Select API-token login for v2 per user direction on 6 October 2026. Provide guided token creation, permission guidance, secure storage, status checks, and explicit replacement. OAuth is deferred; no app is available.

Completion criteria:

- [x] Record the chosen scope, naming decision, command contract, auth design, and migration policy in this directory before implementation depends on them.

## Sprint 1 — Command structure and project-neutral defaults

- [x] Separate command parsing, application operations, credential/config resolution, Jira transport, and output rendering so interactive prompts are outside API code.
- [x] Introduce grouped equivalents for existing operations in the command migration table below; route old and new names through the same operations. Auth, templates, and update commands remain in their later sprints.
- [x] Retain root/per-command `--help` and add `help` plus `help <resource> <action>`, all available without credentials or network access.
- [x] Make global flags work before and after subcommands without parser defaults overwriting supplied values; define precedence for repeated options.
- [x] Make the new root command show local context and common commands without fetching Jira data; preserve or explicitly migrate the legacy no-argument dashboard behavior.
- [x] Remove hardcoded project keys from the default dashboard; support selected projects and make count semantics explicit. Remove project-specific tips from general help.
- [x] Introduce general `issue list`, keeping unfinished-issue filtering as an explicit `--open` convenience and preserving legacy `open` behavior.
- [x] Remove support-specific labels, components, and summary patterns from general creation. Preserve legacy intake behavior through an explicit compatibility path until the callback template is available.
- [x] Standardize `--web` viewing for issues and boards, resolve the actual board location where needed, and allow help/local config/browser operations without unnecessary credential validation.
- [x] Verify command dispatch, help, flag placement, aliases, and project-neutral behavior with mocked API calls.

Completion criteria:

- [x] Selecting a project unrelated to `RP`, `RD`, or `BUG` does not query those projects or inject support-specific metadata into new generic commands.
- [x] Existing documented commands continue to work through the compatibility layer, and deprecation messages do not corrupt JSON stdout.

## Sprint 2 — Reliable client and scripting contract

- [x] Add explicit connection/read timeouts and consistent handling for HTTP, network, malformed-response, and interruption errors across initial calls and interactive follow-ups.
- [x] Add bounded retries for safe operations, honoring rate-limit guidance. Do not blindly retry mutations such as issue creation when the outcome is unknown.
- [x] Support the current enhanced search API and cursor pagination; review the deprecated search fallback and document any retained compatibility path.
- [x] Implement endpoint-appropriate pagination for issue searches, projects, boards, sprints, comments, and metadata. Define a limit on total results separately from page size; add `--all`.
- [x] Use POST search for long JQL where appropriate, safely construct generated JQL, and distinguish complete user JQL from additional filters.
- [x] Stop assuming enhanced search returns `total`; show fetched counts, remaining-page information, and clearly labeled approximate counts where used.
- [x] Make `--json` consistent for every applicable new command; define stable result/error shapes while preserving legacy JSON as agreed in Sprint 0.
- [x] Send progress, warnings, and diagnostics to stderr; keep stdout machine-readable and redact credentials from all diagnostic output.
- [x] Add strict `--no-input`; never prompt in that mode or on unavailable input, and report missing values. Keep destructive-operation confirmation separate from output format.
- [x] Verify pagination, rate limits, timeouts, malformed responses, uncertain mutation outcomes, JSON output, and exit codes using controlled responses.

Completion criteria:

- [x] A scripted list operation can retrieve more than one page without prompts or non-JSON stdout.
- [x] A timed-out create operation reports an uncertain outcome instead of silently creating a second issue.

CI evidence: commit `92c8e04`; [GitHub run 37486855132](https://github.com/User17745/jira-cli-toolkit/actions/runs/37486855132) passed all four Python/OS jobs, builds, and installed command smoke tests.


Reliability evidence: 51 deterministic tests pass locally, including cursor/offset pages, total limits, malformed JSON, bounded read retries, Retry-After, uncertain mutation timeouts, structured JSON errors, legacy error behavior, and redaction. Wheel/sdist and both clean-home installed entry points pass. Pagination of metadata is tracked in Sprint 4.

## Sprint 3 — Authentication, profiles, and contexts

- [x] Add `auth login`, `auth status`, `auth logout`, and `user me`; validate authentication before persisting a new credential set.
- [x] Implement guided API-token login, supporting unscoped tokens at the site URL and scoped tokens through the Atlassian API gateway with a cloud ID. Explain token creation, scopes, project permissions, expiration, and replacement.
- [x] Store credentials through an OS credential-store abstraction; keep profile/context preferences separate from secrets. Define an explicit fallback for headless environments or unavailable credential stores without silently writing plaintext tokens.
- [x] Add named profiles and `profile list`, `profile use`, and `profile remove`; keep credentials scoped to the intended site and account.
- [x] Add `context show` and `context use` for active profile/project/board; let setup select from accessible projects and boards rather than requiring memorized keys or IDs.
- [x] Inspect existing credentials from this CLI's supported sources and report the selected source without exposing secrets; do not assume or import another tool's credentials automatically.
- [x] Validate selected credentials through an authenticated endpoint. Treat `401` as authentication failure, without claiming expiry is known; report token expiry as unknown unless independently provided and keep `403` permission failures separate.
- [x] Offer explicit token replacement on interactive authentication failure; never replay uncertain writes. API tokens have no refresh mechanism; retain the selected identity and distinguish 401 from permission failures.
- [x] Make noninteractive auth failures actionable and deterministic. Do not switch to a different saved identity after an explicitly supplied credential fails, and do not automatically replay an uncertain mutation.
- [x] Migrate `~/.config/jsup/config.json` into the agreed profile/config format and credential store; make migration repeatable and preserve usable legacy credentials until the new storage succeeds.
- [x] Define logout behavior for local credentials, upstream revocation where supported, and externally supplied environment/flag credentials; make those effects visible to the user.
- [x] Add `config show/get/set` for nonsecret preferences and `doctor` for redacted diagnostics covering credential source, connectivity, current identity, and project access.
- [x] Verify missing, valid, invalid, expired, and revoked credentials; token replacement success/failure; profile isolation; migration failure; permission denial; and noninteractive recovery.

Completion criteria:

- [x] A new user can authenticate, choose an accessible project, inspect auth status, and sign out without manually editing files.
- [x] An existing user can migrate safely and continue operating under the same site/account; auth recovery never silently changes that identity.
- [x] Invalid, expired, or revoked API tokens produce a clear replacement path; scripts never block on prompts and credentials are never silently changed.


Authentication evidence: 71 deterministic tests pass. Native-store calls are mocked; actual OS credential-store/live Jira acceptance remains Sprint 8. Explicit file storage is verified on POSIX; Windows rejects it until ACL protection is implemented. No OAuth app or refresh mechanism is assumed.

## Sprint 4 — Project discovery and field handling

- [x] Add `project list/view`, `project issue-types`, `project fields --type <type>`, and `project statuses` using current supported metadata APIs.
- [x] Discover creation fields and edit/transition metadata in their appropriate contexts; inspect required values and available options without assuming every validator is discoverable.
- [x] Resolve issue types, priorities, components, users, transitions, and field names to identifiers; offer unambiguous selection and an ID escape hatch for duplicate names.
- [x] Support repeatable `--field` values and structured JSON input for complex fields; handle supported text, rich text, number, date, selection, array, and user-reference formats correctly.
- [x] In guided creation, select a valid issue type and prompt for missing required fields; apply only valid explicit/configured defaults. Respect editor-based description entry and description files.
- [x] In script mode, reject missing or invalid required values with field-level diagnostics; accept complete input without prompting.
- [x] Support fields required during transitions and editable fields during updates; translate server validation errors into useful diagnostics instead of assuming metadata guarantees success.
- [x] Cache metadata with a TTL and explicit refresh, scoped to site/account/project/issue type and operation; invalidate affected entries when validation exposes stale configuration.
- [x] Document supported field formats and the structured-input escape hatch; identify unsupported app-specific field behavior explicitly rather than dropping supplied values.
- [x] Verify projects with different issue types, duplicate field names, required custom fields, rich-text requirements, stale metadata, and transition validators.

Completion criteria:

- [x] An unfamiliar project's Bug issue can be created with its required custom fields in both interactive and scripted modes.
- [x] Available transitions come from Jira, and a transition requiring additional fields can be completed when its requirements are supported.


Discovery evidence: 98 deterministic tests cover project-specific required fields, custom options, typed/ADF/structured input, ambiguous names/IDs, cache scoping/refresh/invalidation, scripted guards and transition requirements. Live project validation remains Sprint 8.

## Sprint 5 — Essential issue maintenance and collaboration

- [x] Add `issue edit` for supported editable fields, including summary, description, priority, due date, labels, and components; distinguish replace/add/remove behavior for collection fields.
- [x] Add `issue assign` and `issue unassign`, including current-user selection and permission-aware user resolution.
- [x] Extend `issue list` with assignee, status, issue-type, label, board, full JQL, ordering, field selection, and pagination controls; document filter precedence.
- [x] Add `issue create --parent` and supported parent edits, using project metadata and capabilities rather than a fixed Epic/Story hierarchy.
- [x] Add `issue link` and `issue unlink` with available link-type discovery and explicit direction.
- [x] Add attachment upload/list/download/delete, including multipart transport, safe download filenames, and file/size errors.
- [x] Add comment edit/delete and editor/file input for comments; preserve permission and visibility behavior supported by the API.
- [x] Verify maintenance operations against field restrictions, unresolved identities, disallowed parents, link direction, attachment failures, and comment ownership/permissions.

Completion criteria:

- [x] A user can find, view, assign, update, transition, comment on, link, and attach evidence to an issue through the CLI.
- [x] Unsupported or unauthorized updates fail with actionable errors and do not imply success.


Maintenance evidence: 111 deterministic tests pass, covering edit restrictions/collections, assignment ambiguity, explicit link direction, comment file input, multipart uploads, safe downloads/partial cleanup, quoted filters, and confirmation guards. Live permission/ownership acceptance remains Sprint 8.

## Sprint 6 — Templates and daily-use polish

- [x] Define a versioned declarative template format for prompts, summary/description patterns, defaults, and field mappings; keep secrets and executable hooks out of templates.
- [x] Add `template list/show/validate` and `issue create --template`; validate against the selected project/type and let explicit CLI input override template defaults.
- [x] Ship the current callback workflow as an optional example template. Keep `ops-runbook` explicit and validated, with a documented way to remove or replace it.
- [x] Route legacy `intake` through the callback compatibility template; retain its documented arguments and explain migration to ordinary template creation.
- [x] Add shell completion for the supported shells, using local/cached metadata where possible and avoiding unnecessary network calls.
- [x] Add configurable list columns and optional CSV output; keep JSON and readable terminal output consistent with their contracts.
- [x] Improve project/board/sprint selection and the dashboard based on selected context; handle projects without applicable board or sprint capabilities.
- [x] Verify template validation, override precedence, missing components, cross-project reuse, completion, and piped output.

Completion criteria:

- [x] A team can share a template and use it on a compatible project without changing Python code; incompatible defaults are identified before submission.
- [x] The original support workflow remains available explicitly, while generic operations retain project-neutral behavior.


Workflow evidence: 119 deterministic tests pass, covering template schema/expression restrictions, required variables, override precedence, incompatible components, local completion and parseable CSV. Package and binary smoke scripts verify bundled template resources.

## Sprint 7 — CI/CD, GitHub Releases, and update command

GitHub Releases is the shared distribution source for installers and the update command. CI runs on pull requests and pushes; versioned tags trigger automated release publication after validation. Builds from every commit must not silently become the latest stable version. Release/updater work can begin before later feature sprints, but a stable v2 release requires their completion.

### Release contract and CI

- [x] Define the release manifest shared by the pipeline and updater: version, tag, commit, channel, artifact names, OS/architecture, supported runtime/platform requirements, size, checksum, and manifest schema version.
- [x] Select and pin the standalone-binary packaging tool and build dependencies; keep Python wheel/sdist distribution for existing pipx/uv/pip users. Make the packaged runtime report its version and installation method.
- [x] Define the supported binary matrix, starting with macOS arm64/x86_64, Linux x86_64, and Windows x86_64; validate runner availability and minimum OS requirements before promising additional architectures.
- [x] Add GitHub Actions CI on pull requests and default-branch pushes for meaningful tests, lint/static checks selected for the project, Python package builds, and installed-package smoke tests. Run PR checks without publishing privileges or production Jira credentials.
- [x] Add native binary build and smoke-test jobs for each supported platform, including `--version`, `--help`, and updater discovery without Jira configuration.
- [x] Pin workflow actions and build inputs, use minimal job-specific permissions, and configure concurrency so overlapping runs cannot publish inconsistent assets for the same version.

### Automated publication

- [x] Add a tag-triggered release workflow for versioned tags such as `v2.0.0`; confirm tag/package/runtime versions agree and release only tested commits under the agreed release policy.
- [x] Build wheel/sdist and all supported binaries, assemble the manifest and SHA-256 checksums, and upload the complete asset set to a draft GitHub Release. Reuse the same built artifacts for testing and publication.
- [x] Generate release notes and migration links; publish the release only after every required artifact and smoke check succeeds. Make retries idempotent and preserve already published versioned assets.
- [x] Mark prerelease tags as prereleases and exclude them from stable updates; set the latest stable release explicitly so an older maintenance release or failed run cannot displace it.
- [x] Produce artifact provenance/attestations where repository capabilities support them and define client verification separately from checksum validation; checksums alone detect corruption, not publisher identity.
- [x] Decide whether release downloads are public or require GitHub authentication based on actual repository visibility; support private-release access if needed without changing repository visibility or reusing Jira credentials.
- [x] Verify an end-to-end release-candidate run on GitHub, including asset download, manifest consistency, failed-matrix handling, publication permissions, and stable/prerelease selection.

### Update command

- [x] Add `update`, `update --check`, and `update --version <version>`, keeping a legacy `jsup update` entry point. Support `--json`, `--no-input`, and explicit confirmation controls consistently with the CLI contract.
- [x] Discover the latest published stable release from the renamed repository's GitHub Releases API, or resolve a requested version. Compare semantic versions correctly; avoid accidental downgrades and require explicit opt-in to prereleases or rollback.
- [x] Detect the installed platform, architecture, version, and installation method. Select only compatible assets and explain unsupported platforms without changing the installation.
- [x] For standalone installations, download from the canonical GitHub release, verify manifest/size/checksum and any required provenance, and validate the candidate executable before installation.
- [x] Stage replacements beside the target where possible, preserve executable permissions, handle Windows running-executable replacement with an appropriate helper, and restore the previous executable if replacement or post-update validation fails.
- [x] For package-manager installations, upgrade through the owning manager/environment using the verified release wheel or its documented distribution channel; never overwrite pipx/uv/Homebrew shims or use an unrelated Python environment. Provide exact instructions when automated delegation is unsupported.
- [x] Preserve credentials, profiles, and contexts during binary/package replacement. Invoke versioned config migrations through the application and distinguish executable rollback from potentially irreversible config migration.
- [x] Handle offline operation, GitHub API rate limits, private-release authentication, missing/incomplete assets, unsupported manifests, unwritable destinations, and concurrent updates with actionable errors. `--check` must never modify the installation.
- [x] Verify update behavior for stable/prerelease/version selection, no-op updates, installation methods, platform matching, checksum mismatch, interrupted downloads, failed replacement, rollback, config preservation, and JSON/noninteractive operation.

### Existing-user bridge to v2

Version `0.2.0` does not contain an update command. A future command cannot appear in already installed copies without an initial upgrade.

- [x] Choose and document a bootstrap path: publish a small compatible pre-v2 release containing the updater, or give current users a one-time package-manager reinstall/upgrade command. Once bootstrap succeeds, `jsup update` can use GitHub Releases for subsequent upgrades.
- [x] Preserve the old executable and package identity through the bridge or provide an explicit migration mapping if the package name changes; test upgrades from the actual `0.2.0` distribution.
- [x] Document release channels, update checks, pinned-version installation, package-manager handling, GitHub authentication when necessary, and rollback limitations. Avoid hidden auto-updates during ordinary Jira commands.

Completion criteria:

- [x] A validated version tag automatically publishes complete, downloadable release assets on GitHub; failed builds and prereleases never replace latest stable.
- [x] A supported standalone installation can check for and install that exact published release, verifies the candidate, and retains credentials/configuration.
- [x] Existing pipx/uv/pip users have a tested bootstrap and upgrade path without breaking their managed environments; unsupported methods receive usable instructions.

## Sprint 8 — Validation, documentation, and release

- [x] Run a representative acceptance matrix covering team-managed/company-managed Cloud projects, non-software project capabilities, required custom fields, differing workflows, restricted permissions, and headless operation.
- [x] Exercise live integration smoke checks in a designated test project with authorized credentials; keep normal automated tests deterministic and independent of production Jira.
- [x] Verify packaged installation in a clean environment, advertised Python versions, supported operating-system build/smoke matrix, macOS Keychain migration/read behavior, completion, and uninstallation; record untested interactive Linux/Windows wallet behavior as a limitation.
- [x] Extend Sprint 7 CI with the complete parser/config/client/operation acceptance suite; include checks that prevent reintroducing original-project defaults into the generic paths.
- [x] Rewrite the README and help examples around onboarding and common generic workflows; document field formats, profiles, credential storage, auth recovery, scripting, limitations, and troubleshooting.
- [x] Publish a migration guide with old/new command mappings, config migration, default-behavior changes, JSON compatibility, alias duration, and rollback steps.
- [x] Finalize package metadata, release version, installation channels, changelog, and executable names; publish a release candidate and record validation evidence before the stable release.
- [x] Confirm credential/token redaction across status/config/doctor/errors and confirm no secrets are included in shipped fixtures, templates, examples, or diagnostic reports.

Completion criteria:

- [x] A fresh user can install, authenticate, select a project, create an issue with required fields, update it, and transition it using only public documentation.
- [x] An existing user can migrate and run the legacy examples without undocumented breakage.
- [x] Scripts receive documented JSON and exit codes and never unexpectedly request input.
- [x] Record release acceptance evidence and remaining limitations, then publish the stable release.

## Command migration reference

The implemented old/new command mapping now lives in the [developer migration guide](../../migration/legacy-commands.md#old-to-new-command-reference), alongside behavioral differences for queries, creation, JSON, pagination and scripted identity selection. The [upgrade guide](../../migration/upgrade-to-v2.md) covers installation, verified downloads, credential migration and rollback. Both guides now use the installed `jira` command (v2.1), with explicit bootstrap instructions for previous installations and supported legacy aliases.

## Later extensions — outside the initial release gate

After the v2.1 naming/public-distribution release, the next planned feature release is [v2.5 authenticated API access and spec discovery](../v2.5-api/roadmap.md), prioritized by the user on 7 October 2026. V2 stable publication and verification are complete. V2.5 will provide generic endpoint coverage; the commands below become optional conveniences rather than prerequisites for calling each API. The v2.5 interface is planned, not implemented in v2.0.0.

These are candidate work packages. Prioritize them after the foundation is released and user demand is known.

- [ ] Add `filter list/view/create/update` and saved-filter selection in issue searches.
- [x] Add `board view` (implemented in v2).
- [ ] Add `board backlog` and richer board configuration inspection where supported.
- [x] Add `sprint view/edit` and required start/close inputs (implemented in v2).
- [ ] Add `sprint remove-issues` and richer capability-aware planning operations.
- [ ] Add `issue clone`, documenting copied fields and excluding comments/attachments unless explicitly supported and selected.
- [ ] Add `issue watch/unwatch`, `issue history`, and `issue worklog add/list/edit/delete`.
- [ ] Add `version list/create/edit/release` for applicable project release workflows.
- [ ] Add explicit bulk operations with previews, per-item results, and handling for partial failures.
- [ ] Add Jira Service Management customer-request support, including service desks, request types/fields, and internal/public comments through the appropriate APIs.
- [ ] Add Data Center support through a separate transport/auth/capability adapter and its own acceptance matrix.
- [ ] Evaluate cross-project issue moves and administrative project/component operations separately; document API and permission limits before adding commands.

## Reference material

Use the current supported APIs during implementation; these links informed the plan and should be checked when each feature is built.

- [Jira Cloud issue operations and field metadata](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/)
- [Jira Cloud search and pagination](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/)
- [Authentication guidance for integrations](https://developer.atlassian.com/cloud/jira/platform/security-for-other-integrations/)
- [OAuth 2.0 (3LO) applications](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/)
- [Jira Service Management customer requests](https://developer.atlassian.com/cloud/jira/service-desk/rest/api-group-request/)
- [Atlassian CLI work-item commands](https://developer.atlassian.com/cloud/acli/reference/commands/jira-workitem/)
- [Existing JiraCLI installation and executable naming](https://github.com/ankitpokhrel/jira-cli/wiki/Installation)
- [Existing go-jira executable naming](https://github.com/go-jira/jira)
- [GitHub Releases API and latest-release discovery](https://docs.github.com/en/rest/releases/releases)
- [GitHub Actions workflow artifacts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts)
- [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations)
- [GitHub repository rename behavior](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository)

Reliability CI evidence: commit `fdc86ad`; [run 37487449923](https://github.com/User17745/jira-cli-toolkit/actions/runs/37487449923) passed every configured job.

Distribution CI evidence: commit `364ba76`; [run 37489313815](https://github.com/User17745/jira-cli-toolkit/actions/runs/37489313815) passed Python packaging and all four native builds/smoke checks, including the real Windows deferred update helper. This historical run did not publish a release; the RC tag/publication evidence is recorded below.

Authentication CI evidence: commit `5bbde12`; [run 37488337845](https://github.com/User17745/jira-cli-toolkit/actions/runs/37488337845) passed the full Python/OS matrix.

Release preparation evidence: 124 tests pass locally with locked dependencies. The original `origin/main` 0.2.0 source was built as a wheel, installed in an isolated environment, and upgraded to the candidate wheel: both entry points and legacy help/update discovery work, with the legacy config byte-identical. [Migration guide](migration.md) and root changelog describe bootstrap, profile migration, command/output changes and rollback.

Windows repair evidence: commit `60a3a6b`; [CI run 37491800987](https://github.com/User17745/jira-cli-toolkit/actions/runs/37491800987) and [native run 37491801158](https://github.com/User17745/jira-cli-toolkit/actions/runs/37491801158) pass on all configured platforms. The prior failed template run published no assets.

Live acceptance on 6 October 2026: authorized team-managed software project BUG passed create/view/edit, typed Start date, assignment/unassignment, comment add/list/edit/delete, transition, link/unlink, attachment upload/list/download/delete with byte comparison, paginated JSON search and CSV parsing. BUG-703 and BUG-704 remain labeled `jira-cli-v2-acceptance` for user-authorized manual cleanup because Delete Issues permission is absent; no other issues were modified.

Live authentication: isolated explicit POSIX file storage passed login/status/context/doctor/logout and legacy migration; original user config was preserved. Native macOS storage required OS approval; scripted login now returns a redacted actionable error instead of blocking. Interactive native-store approval/happy-path validation remains a manual release gate. Linux native wallets are interactive only; scripted use requires environment authentication or explicit file storage. The regression suite now has 127 tests, including OS interaction suppression/restoration.

Provenance: the workflow includes optional, pinned GitHub attestations gated by `RELEASE_ATTESTATIONS=true`; publication waits for successful attestation when enabled. This private repository’s plan eligibility is not confirmed, so attestations are disabled. The manifest declares availability; manual `gh attestation verify` is separate from the updater’s hash validation. No signature/notarization claim is made.

Read-only live capability matrix: BUG (team-managed software), PRD (company-managed software), TEST (team-managed business), and LDSUP (company-managed service desk) returned their own issue-type catalogs. Write acceptance was limited to authorized BUG. Required-field/validator variations and denied operations are additionally covered by deterministic fixtures; customer request APIs remain outside this release.

Manager acceptance: the actual 0.2.0 wheel was installed and upgraded to the candidate in isolated pipx 1.14.0 (pip backend) and uv environments; both executables, receipt-based manager discovery (including a custom uv directory), config preservation, and manager uninstall passed. Bash/zsh completion scripts pass shell syntax checks. The suite has 128 passing tests. [Auth/native CI run 37495926075](https://github.com/User17745/jira-cli-toolkit/actions/runs/37495926075) passed all package/native jobs at `2fd8541`.

User acceptance exposed that pipx’s `install --force --backend pip` ignores the requested backend for an existing uv environment. The earlier pip-backed baseline did not establish that backend-switch recovery. Follow-up checks now reproduce the exact failure from a uv-backed 0.2.0 installation, then verify `pipx uninstall jsup` followed by a fresh pip-backed install of the published RC wheel, both entry points, manager detection, and unchanged config bytes/permissions. Current-branch migration docs and updater guidance are corrected; the published RC remains immutable.

- [x] Correct and verify the pipx recovery from an existing uv-backed 0.2.0 installation; run full regression and installed-wheel smoke checks before pushing the correction.

Release-candidate validation on 7 October 2026: tag `v2.0.0rc1` points to tested commit `d064060`. [Tag run 37497037819](https://github.com/User17745/jira-cli-toolkit/actions/runs/37497037819) passed four compatibility jobs, four native builds, packaging and publication. Authenticated downloads verified all eight assets (four binaries, wheel/sdist, manifest and checksums), manifest commit/version, sizes and SHA-256 hashes. An actual earlier `0.3.0.dev0` standalone CI binary updated to the published candidate; the prior executable remained available, config was byte-identical, and a repeated check was a no-op. The published wheel passed isolated smoke checks. The RC is excluded from latest stable.

Native acceptance on 7 October 2026: the user successfully installs the published RC wheel, migrates legacy credentials with `--storage keyring`, and runs a separate live status command reporting `source: keyring` and `authenticated: True`. This closes the macOS interactive native-store gate. No additional Jira issues were created. The pipx recovery correction at `291ec14` passes [CI](https://github.com/User17745/jira-cli-toolkit/actions/runs/37567939789) and [all four native builds](https://github.com/User17745/jira-cli-toolkit/actions/runs/37567940018).

Stable preparation gates required final review/checks, merge into main, and tagging the tested 2.0.0 main commit before verification as latest stable. Source package/runtime/lock versions agree on 2.0.0. [PR #1](https://github.com/User17745/jira-cli-toolkit/pull/1) is merged. Later extensions remain outside the initial release gate.

- [x] Stable promotion milestone: rerun full regression, build and installed-CLI smoke checks; commit/push version and acceptance updates; verify CI/native builds before merge/tag; record stable release/update verification.

Stable preparation: package/runtime/lock agree on 2.0.0; the offline lock check, all 128 regression tests, wheel/sdist builds, both installed CLI smoke checks, and local macOS arm64 native build/smoke pass before push. Updater tests now simulate an older installed version explicitly, so a source-version bump cannot silently turn upgrade-path checks into no-ops.

Stable completion on 7 October 2026: preparation commit `2222537` passes [CI](https://github.com/User17745/jira-cli-toolkit/actions/runs/37568701502) and [all native builds](https://github.com/User17745/jira-cli-toolkit/actions/runs/37568701917). Merge commit `cdb0c0f` has an identical tree and passes [main CI](https://github.com/User17745/jira-cli-toolkit/actions/runs/37568928087) and [main native builds](https://github.com/User17745/jira-cli-toolkit/actions/runs/37568928341) before tag `v2.0.0`. [Stable tag pipeline](https://github.com/User17745/jira-cli-toolkit/actions/runs/37569094482) passes all ten required jobs and publishes eight assets. Authenticated downloads match all manifest/checksum entries and latest stable resolves to v2.0.0. An actual published RC1 standalone binary updates through default stable discovery, retains its backup and byte-identical schema-2 config/mode, and reports a no-op on a repeat check. The downloaded stable wheel passes installed CLI smoke checks; an isolated pipx/pip RC1 installation upgrades with both commands, receipt detection and config preservation. The user's actual RC installation and Keychain profile are unchanged by these checks.

- [x] Final release evidence milestone: run regression/package/installed-CLI checks and documentation link checks, then commit/push the completed v2 acceptance and roadmap checkboxes.

- [x] Migration documentation milestone: publish separate user-upgrade and developer-command guides, verify all command examples/old-command coverage and local links, run regression/package/installed-CLI checks, then commit/push and verify CI.

Migration documentation preparation: all 25 original command names are covered; 85 documented invocations parse against the implemented v2 parser, 16 shell blocks pass Bash syntax checks, and local links/anchors resolve. The documented verifier accepts the published wheel/manifest and rejects a corrupted wheel. A temporary CLI fixture exercises the JSON consumer's success path and preserves exit codes 1, 2 and 130 on failure, without contacting Jira. Full regression remains 128 passing tests; wheel/sdist and both installed CLI smoke checks pass before push.

Migration documentation evidence: initial guide commit `e07e994` passes [CI](https://github.com/User17745/jira-cli-toolkit/actions/runs/37573028179) and [all four native builds](https://github.com/User17745/jira-cli-toolkit/actions/runs/37573028457). [PR #2](https://github.com/User17745/jira-cli-toolkit/pull/2) contains the requested guides and follow-up canonical-link corrections; its checks track the final head before merge.

Publication retry check: rerunning the publisher against the verified existing RC recognized the matching complete release and exited without replacing any published asset.

## V2.1 command and public distribution

- [x] Add the primary `jira` entry point; preserve both existing executable aliases, profiles and credential-store references.
- [x] Print an early stderr notice on legacy executable invocations, preserving JSON stdout and internal completion/update protocols.
- [x] Bump package/runtime/lock to 2.1.0 and update current command, installation and migration documentation.
- [x] Review reachable Git history (181 blobs) and all 57 available Actions run logs before public visibility; no credential leaks detected. Three URL-credential detections were reviewed synthetic rejection fixtures in `tests/test_auth.py`.
- [x] Test before the milestone push: 132 regressions, offline lock/build, wheel/sdist, all three installed entry points and local macOS arm64 native smoke pass. Documentation QA covers all 25 old command names, 86 parsed invocations, 16 shell blocks, links and checksum/error-handling fixtures.
- [x] Push the tested milestone, verify GitHub CI/native builds, and merge [PR #3](https://github.com/User17745/jira-cli-toolkit/pull/3) into main (`0675d21`, identical to the tested head tree).
- [x] Make the repository public and verify anonymous repository/release page and manifest access (HTTP 200). The shared-IP anonymous API quota was exhausted during this check; authenticated API requests and unauthenticated direct downloads work.
- [x] Tag the tested main commit and verify all eight v2.1.0 assets, latest-stable selection and a real v2.0-to-v2.1 standalone update; backup retained, config bytes/mode unchanged, repeat check is a no-op. Anonymous wheel download and the guide checksum verifier pass.
- [x] Upgrade the user’s installed pipx CLI to the verified stable wheel: `jira 2.1.0`, all three version/help checks and both legacy notices pass; the existing `work` profile authenticates from keyring with byte-identical config and unchanged permissions.

## Remaining work after v2.1

- [ ] Complete the [v2.5 authenticated API/spec roadmap](../v2.5-api/roadmap.md), including request safety, spec freshness, agent documentation and acceptance/release checks.
- [ ] Choose and add an explicit reuse/contribution license; public visibility alone does not grant open-source reuse rights.
- [ ] Enable and verify release attestations, then assess client-side verification, macOS signing/notarization and Windows signing.
- [ ] Verify interactive Windows Credential Manager and Linux wallet acceptance on user machines; current CI checks do not certify interactive prompts.
- [ ] Prioritize package-registry/distribution publication (PyPI/Homebrew or equivalents), broader native OS support, Data Center/JSM APIs and optional convenience commands based on demand.
- [ ] Remove the two previously authorized labeled BUG acceptance issues when an account with Delete Issues permission is available.

V2.1 release evidence: source milestone `d3f1ea9` passes [PR CI](https://github.com/User17745/jira-cli-toolkit/actions/runs/37574742016) and [native builds](https://github.com/User17745/jira-cli-toolkit/actions/runs/37574742210). Merged commit `0675d21` passes [main CI](https://github.com/User17745/jira-cli-toolkit/actions/runs/37574953579) and [main native builds](https://github.com/User17745/jira-cli-toolkit/actions/runs/37574953839); its identical tested tree is tagged `v2.1.0`. The [tag pipeline](https://github.com/User17745/jira-cli-toolkit/actions/runs/37574959673) passes all ten required compatibility/native/package/publication jobs. Published hashes/sizes and manifest commit/version match; native update and package/docs checks use isolated homes and perform no Jira writes.

Local v2.1 acceptance: the actual pipx installation upgrades through its recorded pip backend. `jira` is available on PATH, retained aliases emit the requested notice, installation discovery reports `pipx`, and the existing Keychain profile remains authenticated. The final documentation/evidence milestone reruns full regressions, package build and installed smoke checks before pushing to Git.

## README, website and installation milestone

- [x] Revamp the README with the supplied hero image, relevant release/CI/platform badges, quick start and linked full command reference.
- [x] Build a responsive shadcn/ui landing page with first-fold OS installation, copy controls, manual releases, migration and examples.
- [x] Add checksum-verified POSIX and PowerShell installers with platform checks and existing-command protection; document options and recovery.
- [ ] Verify desktop/mobile UI, accessibility interactions, installer success/failure cases and native Windows/macOS/Linux integration.
- [x] Before the milestone push, run full CLI regressions, wheel/sdist and installed-CLI smoke checks, docs QA, frontend lint/build/browser tests.
- [ ] Push the tested milestone promptly, verify CLI/native/site CI, merge, and publish GitHub Pages automatically.
- [ ] Verify public page/assets/install-script URLs, update repo homepage/topics, and record final build/deployment evidence.

Local website/installer validation: 141 CLI regressions, wheel/sdist builds and all three entry points in an isolated installed wheel pass; documentation QA validates links, 25 old command names, 86 migration invocations and 37 current README/website examples. Eight production-build browser checks pass at desktop/mobile sizes, including first-fold installation and overflow from 320px to 1440px. The verified macOS arm64 release binary passes offline installer success, checksum rejection and conflict checks. Frontend lint/type/build and the full npm dependency audit pass (zero vulnerabilities). Native CI runs installer integration for all four release targets before merge/publication.

The real public latest-stable POSIX installer also passes an isolated macOS arm64 download/install/version/context/update-discovery check, matching the previously verified v2.1 binary byte for byte. Initial PR CI passes website, all compatibility jobs and three native targets; Windows exposed a fixture inheriting PowerShell 7 module paths into Windows PowerShell 5.1. The fixture now selects the tested shell’s own modules; checksum verification remains unchanged.
