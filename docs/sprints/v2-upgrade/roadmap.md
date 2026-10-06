# Jira CLI v2 upgrade roadmap

Created: 6 October 2026

Status: in progress. Command foundation, API reliability, and cross-platform CI are implemented. Guided API-token authentication and profiles are being verified. Discovery, issue maintenance, templates, release publication, updater, and live acceptance remain in progress or planned.

## Goal

Turn the current support-oriented CLI into a general-purpose Jira Cloud tool. A user should be able to authenticate, select an unfamiliar project, discover its requirements, and create, update, and transition issues without changing Python code or knowing the original project's conventions.

Jira defines the available fields, issue types, workflows, and permissions. The CLI discovers those capabilities, offers useful defaults, and lets teams add optional templates.

## Tracking and scope

Every actionable item has a checkbox. Check implementation tasks after the change and its required verification are complete. Check a sprint's completion criteria only when the described user behavior has been demonstrated. Record decisions and evidence alongside the relevant item as work proceeds.

The initial release targets standard issue operations across Jira Cloud project types, within the capabilities and permissions exposed by Jira. Service Management customer requests and Data Center support are separate extensions. Arbitrary app-defined fields and validators cannot be assumed to be fully discoverable.

The repository is [User17745/jira-cli-toolkit](https://github.com/User17745/jira-cli-toolkit), renamed from `jira-support-cli` to reflect the broader product scope. It remains private; the release plan must account for authenticated downloads unless visibility is explicitly changed later. The executable is `jira-cli-toolkit`; the Python package and legacy executable remain `jsup` throughout v2.x. Command examples below use `jira` as shorthand for a user-chosen alias. See the [interface contract](interface-contract.md) for implemented behavior and migration decisions.

## Tested delivery checkpoints

Before every push: run the complete regression suite plus tests for the changed behavior, build the wheel/sdist, and smoke both installed entry points in an empty home. Push each substantial, reviewable milestone; record its commit and GitHub Actions result here. Failed checks must be fixed before the next milestone is marked complete. CI supplements local testing and does not replace it.

- [x] Foundation: regression tests and isolated package smoke checks; commit `8e0d8e6` pushed to `codex/v2-foundation` (draft PR #1).
- [x] CI foundation: test/build/install smoke jobs pass locally and on GitHub; push and record the run.
- [x] Sprint 2 reliability: new transport/pagination/output tests plus regressions and installed smoke checks; commit/push and verify CI.
- [x] Sprint 3 authentication: credential/config/recovery tests plus regressions and installed smoke checks; commit/push and verify CI.
- [ ] Sprint 4 discovery: required-field/metadata tests plus regressions and installed smoke checks; commit/push and verify CI.
- [ ] Sprint 5 maintenance: issue-operation tests plus regressions and installed smoke checks; commit/push and verify CI.
- [ ] Sprint 6 workflows: template/completion/output tests plus regressions and installed smoke checks; commit/push and verify CI.
- [ ] Sprint 7 distribution: release/updater tests plus regressions, native binary smoke checks, and GitHub release-candidate validation; commit/push and record evidence.
- [ ] Sprint 8 acceptance: full release checks and migration validation; commit/push verified release documentation and record CI results.

## Repository housekeeping

- [x] Rename `User17745/jira-support-cli` to `User17745/jira-cli-toolkit` on GitHub and verify the canonical repository URL.
- [x] Update this checkout's `origin` after the rename succeeds; preserve GitHub's old-name redirect and verify repository access. Leave other local clones to their owners.
- [ ] Review links, badges, installer URLs, release/updater endpoints, package metadata, and repository integrations for references to the old name as the related features are built; retain intentional legacy references in migration documentation.

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
- [ ] Implement endpoint-appropriate pagination for issue searches, projects, boards, sprints, comments, and metadata. Define a limit on total results separately from page size; add `--all`.
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
- [ ] Resolve issue types, priorities, components, users, transitions, and field names to identifiers; offer unambiguous selection and an ID escape hatch for duplicate names.
- [x] Support repeatable `--field` values and structured JSON input for complex fields; handle supported text, rich text, number, date, selection, array, and user-reference formats correctly.
- [x] In guided creation, select a valid issue type and prompt for missing required fields; apply only valid explicit/configured defaults. Respect editor-based description entry and description files.
- [x] In script mode, reject missing or invalid required values with field-level diagnostics; accept complete input without prompting.
- [ ] Support fields required during transitions and editable fields during updates; translate server validation errors into useful diagnostics instead of assuming metadata guarantees success.
- [x] Cache metadata with a TTL and explicit refresh, scoped to site/account/project/issue type and operation; invalidate affected entries when validation exposes stale configuration.
- [x] Document supported field formats and the structured-input escape hatch; identify unsupported app-specific field behavior explicitly rather than dropping supplied values.
- [x] Verify projects with different issue types, duplicate field names, required custom fields, rich-text requirements, stale metadata, and transition validators.

Completion criteria:

- [x] An unfamiliar project's Bug issue can be created with its required custom fields in both interactive and scripted modes.
- [x] Available transitions come from Jira, and a transition requiring additional fields can be completed when its requirements are supported.


Discovery evidence: 98 deterministic tests cover project-specific required fields, custom options, typed/ADF/structured input, ambiguous names/IDs, cache scoping/refresh/invalidation, scripted guards and transition requirements. Live project validation remains Sprint 8.

## Sprint 5 — Essential issue maintenance and collaboration

- [ ] Add `issue edit` for supported editable fields, including summary, description, priority, due date, labels, and components; distinguish replace/add/remove behavior for collection fields.
- [ ] Add `issue assign` and `issue unassign`, including current-user selection and permission-aware user resolution.
- [ ] Extend `issue list` with assignee, status, issue-type, label, board, full JQL, ordering, field selection, and pagination controls; document filter precedence.
- [ ] Add `issue create --parent` and supported parent edits, using project metadata and capabilities rather than a fixed Epic/Story hierarchy.
- [ ] Add `issue link` and `issue unlink` with available link-type discovery and explicit direction.
- [ ] Add attachment upload/list/download/delete, including multipart transport, safe download filenames, and file/size errors.
- [ ] Add comment edit/delete and editor/file input for comments; preserve permission and visibility behavior supported by the API.
- [ ] Verify maintenance operations against field restrictions, unresolved identities, disallowed parents, link direction, attachment failures, and comment ownership/permissions.

Completion criteria:

- [ ] A user can find, view, assign, update, transition, comment on, link, and attach evidence to an issue through the CLI.
- [ ] Unsupported or unauthorized updates fail with actionable errors and do not imply success.

## Sprint 6 — Templates and daily-use polish

- [ ] Define a versioned declarative template format for prompts, summary/description patterns, defaults, and field mappings; keep secrets and executable hooks out of templates.
- [ ] Add `template list/show/validate` and `issue create --template`; validate against the selected project/type and let explicit CLI input override template defaults.
- [ ] Ship the current callback workflow as an optional example template. Keep `ops-runbook` explicit and validated, with a documented way to remove or replace it.
- [ ] Route legacy `intake` through the callback compatibility template; retain its documented arguments and explain migration to ordinary template creation.
- [ ] Add shell completion for the supported shells, using local/cached metadata where possible and avoiding unnecessary network calls.
- [ ] Add configurable list columns and optional CSV output; keep JSON and readable terminal output consistent with their contracts.
- [ ] Improve project/board/sprint selection and the dashboard based on selected context; handle projects without applicable board or sprint capabilities.
- [ ] Verify template validation, override precedence, missing components, cross-project reuse, completion, and piped output.

Completion criteria:

- [ ] A team can share a template and use it on a compatible project without changing Python code; incompatible defaults are identified before submission.
- [ ] The original support workflow remains available explicitly, while generic operations retain project-neutral behavior.

## Sprint 7 — CI/CD, GitHub Releases, and update command

GitHub Releases is the shared distribution source for installers and the update command. CI runs on pull requests and pushes; versioned tags trigger automated release publication after validation. Builds from every commit must not silently become the latest stable version. Release/updater work can begin before later feature sprints, but a stable v2 release requires their completion.

### Release contract and CI

- [ ] Define the release manifest shared by the pipeline and updater: version, tag, commit, channel, artifact names, OS/architecture, supported runtime/platform requirements, size, checksum, and manifest schema version.
- [ ] Select and pin the standalone-binary packaging tool and build dependencies; keep Python wheel/sdist distribution for existing pipx/uv/pip users. Make the packaged runtime report its version and installation method.
- [ ] Define the supported binary matrix, starting with macOS arm64/x86_64, Linux x86_64, and Windows x86_64; validate runner availability and minimum OS requirements before promising additional architectures.
- [ ] Add GitHub Actions CI on pull requests and default-branch pushes for meaningful tests, lint/static checks selected for the project, Python package builds, and installed-package smoke tests. Run PR checks without publishing privileges or production Jira credentials.
- [ ] Add native binary build and smoke-test jobs for each supported platform, including `--version`, `--help`, and updater discovery without Jira configuration.
- [ ] Pin workflow actions and build inputs, use minimal job-specific permissions, and configure concurrency so overlapping runs cannot publish inconsistent assets for the same version.

### Automated publication

- [ ] Add a tag-triggered release workflow for versioned tags such as `v2.0.0`; confirm tag/package/runtime versions agree and release only tested commits under the agreed release policy.
- [ ] Build wheel/sdist and all supported binaries, assemble the manifest and SHA-256 checksums, and upload the complete asset set to a draft GitHub Release. Reuse the same built artifacts for testing and publication.
- [ ] Generate release notes and migration links; publish the release only after every required artifact and smoke check succeeds. Make retries idempotent and preserve already published versioned assets.
- [ ] Mark prerelease tags as prereleases and exclude them from stable updates; set the latest stable release explicitly so an older maintenance release or failed run cannot displace it.
- [ ] Produce artifact provenance/attestations where repository capabilities support them and define client verification separately from checksum validation; checksums alone detect corruption, not publisher identity.
- [ ] Decide whether release downloads are public or require GitHub authentication based on actual repository visibility; support private-release access if needed without changing repository visibility or reusing Jira credentials.
- [ ] Verify an end-to-end release-candidate run on GitHub, including asset download, manifest consistency, failed-matrix handling, publication permissions, and stable/prerelease selection.

### Update command

- [ ] Add `update`, `update --check`, and `update --version <version>`, keeping a legacy `jsup update` entry point. Support `--json`, `--no-input`, and explicit confirmation controls consistently with the CLI contract.
- [ ] Discover the latest published stable release from the renamed repository's GitHub Releases API, or resolve a requested version. Compare semantic versions correctly; avoid accidental downgrades and require explicit opt-in to prereleases or rollback.
- [ ] Detect the installed platform, architecture, version, and installation method. Select only compatible assets and explain unsupported platforms without changing the installation.
- [ ] For standalone installations, download from the canonical GitHub release, verify manifest/size/checksum and any required provenance, and validate the candidate executable before installation.
- [ ] Stage replacements beside the target where possible, preserve executable permissions, handle Windows running-executable replacement with an appropriate helper, and restore the previous executable if replacement or post-update validation fails.
- [ ] For package-manager installations, upgrade through the owning manager/environment using the verified release wheel or its documented distribution channel; never overwrite pipx/uv/Homebrew shims or use an unrelated Python environment. Provide exact instructions when automated delegation is unsupported.
- [ ] Preserve credentials, profiles, and contexts during binary/package replacement. Invoke versioned config migrations through the application and distinguish executable rollback from potentially irreversible config migration.
- [ ] Handle offline operation, GitHub API rate limits, private-release authentication, missing/incomplete assets, unsupported manifests, unwritable destinations, and concurrent updates with actionable errors. `--check` must never modify the installation.
- [ ] Verify update behavior for stable/prerelease/version selection, no-op updates, installation methods, platform matching, checksum mismatch, interrupted downloads, failed replacement, rollback, config preservation, and JSON/noninteractive operation.

### Existing-user bridge to v2

Version `0.2.0` does not contain an update command. A future command cannot appear in already installed copies without an initial upgrade.

- [ ] Choose and document a bootstrap path: publish a small compatible pre-v2 release containing the updater, or give current users a one-time package-manager reinstall/upgrade command. Once bootstrap succeeds, `jsup update` can use GitHub Releases for subsequent upgrades.
- [ ] Preserve the old executable and package identity through the bridge or provide an explicit migration mapping if the package name changes; test upgrades from the actual `0.2.0` distribution.
- [ ] Document release channels, update checks, pinned-version installation, package-manager handling, GitHub authentication when necessary, and rollback limitations. Avoid hidden auto-updates during ordinary Jira commands.

Completion criteria:

- [ ] A validated version tag automatically publishes complete, downloadable release assets on GitHub; failed builds and prereleases never replace latest stable.
- [ ] A supported standalone installation can check for and install that exact published release, verifies the candidate, and retains credentials/configuration.
- [ ] Existing pipx/uv/pip users have a tested bootstrap and upgrade path without breaking their managed environments; unsupported methods receive usable instructions.

## Sprint 8 — Validation, documentation, and release

- [ ] Run a representative acceptance matrix covering team-managed/company-managed Cloud projects, non-software project capabilities, required custom fields, differing workflows, restricted permissions, and headless operation.
- [ ] Exercise live integration smoke checks in a designated test project with authorized credentials; keep normal automated tests deterministic and independent of production Jira.
- [ ] Verify packaged installation in a clean environment, advertised Python versions, supported operating systems, credential-store behavior, completion, and uninstallation.
- [ ] Extend Sprint 7 CI with the complete parser/config/client/operation acceptance suite; include checks that prevent reintroducing original-project defaults into the generic paths.
- [ ] Rewrite the README and help examples around onboarding and common generic workflows; document field formats, profiles, credential storage, auth recovery, scripting, limitations, and troubleshooting.
- [ ] Publish a migration guide with old/new command mappings, config migration, default-behavior changes, JSON compatibility, alias duration, and rollback steps.
- [ ] Finalize package metadata, release version, installation channels, changelog, and executable names; publish a release candidate and record validation evidence before the stable release.
- [ ] Confirm credential/token redaction across status/config/doctor/errors and confirm no secrets are included in shipped fixtures, templates, examples, or diagnostic reports.

Completion criteria:

- [ ] A fresh user can install, authenticate, select a project, create an issue with required fields, update it, and transition it using only public documentation.
- [ ] An existing user can migrate and run the legacy examples without undocumented breakage.
- [ ] Scripts receive documented JSON and exit codes and never unexpectedly request input.
- [ ] Record release acceptance evidence and remaining limitations, then publish the stable release.

## Command migration reference

`jira` is shorthand for an optional user alias of `jira-cli-toolkit`. The grouped interface and legacy compatibility policy are recorded in the interface contract.

| Current command | Proposed interface |
| --- | --- |
| `jsup config init` | `jira auth login`, followed by context selection |
| `jsup config show` | `jira config show`; auth health via `jira auth status` |
| `jsup me` | `jira user me` |
| `jsup` / `jsup dashboard` | `jira dashboard`; new root shows local context/help |
| `jsup project-list` / `project-show` | `jira project list` / `view` |
| `jsup open -p ENG` | `jira issue list -p ENG --open` |
| `jsup issue-create` | `jira issue create` |
| `jsup intake` | `jira issue create --template callback` |
| `jsup issue-show ENG-42` | `jira issue view ENG-42` |
| `jsup transitions ENG-42` | `jira issue transitions ENG-42` |
| `jsup issue-move ENG-42` | `jira issue transition ENG-42` |
| `jsup issue-delete ENG-42` | `jira issue delete ENG-42` |
| `jsup comment-add` / `comment-list` | `jira issue comment add` / `list` |
| `jsup board-list` / `board-create` / `board-issues` | `jira board list` / `create` / `issues` |
| `jsup board-feature --enable` / `--disable` | `jira board feature enable` / `disable` |
| `jsup sprint-list` / `sprint-create` | `jira sprint list` / `create` |
| `jsup sprint-state <id> active` / `closed` | `jira sprint start <id>` / `close <id>` |
| `jsup sprint-state <id> future` | Supported state update via `jira sprint edit`; retain legacy parsing and validate legal transitions |
| `jsup sprint-add` | `jira sprint add-issues` |
| `jsup component-list` / `component-create` | `jira component list` / `create` |
| `jsup browse ENG-42` | `jira issue view ENG-42 --web` |
| `jsup browse board:<id>` | `jira board view <id> --web` |
| No existing update command | `jira update`, `jira update --check`, `jira update --version <version>`; retain `jsup update` after bootstrap |

## Later extensions — outside the initial release gate

These are candidate work packages. Prioritize them after the foundation is released and user demand is known.

- [ ] Add `filter list/view/create/update` and saved-filter selection in issue searches.
- [ ] Add `board view`, `board backlog`, and richer board configuration inspection where supported.
- [ ] Add `sprint view/edit/remove-issues`, including required start/close inputs and capability-aware behavior.
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

Distribution CI evidence: commit `364ba76`; [run 37489313815](https://github.com/User17745/jira-cli-toolkit/actions/runs/37489313815) passed Python packaging and all four native builds/smoke checks, including the real Windows deferred update helper. No release tag has been published yet.
