# v2.6 — Paginated API calls, service desk commands, an agent skill and winget

Decision recorded: 9 October 2026. Status: released in [v2.6.0](https://github.com/User17745/jira-cli-toolkit/releases/tag/v2.6.0) on 9 October 2026; the winget submission awaits Microsoft's CLA and review.

v2.5 shipped `jira api` and `--spec`; v2.5.1 and v2.5.2 added PyPI, release attestations and Homebrew. This release makes the CLI easier for agents to use well, adds friendly commands for Jira Service Management, and adds Windows Package Manager distribution.

Out of scope, by decision: macOS notarization and Windows code signing (paid accounts), and interactive Windows Credential Manager and Linux wallet acceptance on user machines. Both are recorded as declined in the [v2 roadmap](../v2-upgrade/roadmap.md#remaining-work-after-v21).

## 1. Housekeeping

- [x] Remove the finished `.claude/worktrees/web-feedback` worktree (its commit is on `main`) and ignore `.claude/worktrees/` so agent worktrees are never committed. Done on `main` by the session that created it.
- [ ] BUG-703 and BUG-704, the labeled v2 acceptance issues, stay until an account with **Delete Issues** permission on BUG removes them. The `work` account has Create Issues but not Delete Issues, so this cannot be done from this CLI. Their attachments and the temporary issue property are already removed.

## 2. `jira api --paginate`

Agents currently loop over pages themselves, using each endpoint's own protocol. `--paginate` follows the page protocol for them and returns one merged result.

Contract:

```sh
jira api /rest/api/3/project/search --paginate              # offset: startAt / maxResults / total / isLast
jira api /rest/agile/1.0/board/12/issue --paginate --query maxResults=50
jira api /rest/api/3/search/jql -X POST --data @q.json --paginate   # cursor: nextPageToken in the body
jira api /rest/servicedeskapi/servicedesk --paginate        # start / limit / isLastPage
jira api /rest/api/3/project/search --paginate --max-items 200
```

- [x] Detect the protocol from the first response: Jira offset pages (`startAt`, `maxResults`, `total` or `isLast`, with `values`, `issues`, `comments` or `worklogs`), cursor pages (`nextPageToken`, with `issues`), and Service Management pages (`start`, `limit`, `isLastPage`, with `values`).
- [x] Merge into one JSON object of the first page's shape: the item array holds every item, paging fields describe the merged result, and `fetched` gives the count. A response that is not a recognized page fails with `invalid_input` instead of guessing.
- [x] Allowed for GET, and for POST only on `/rest/api/3/search/jql` (where the cursor goes in the JSON body). Other methods and bodies fail before sending.
- [x] Bounds: `--max-items` (optional) and a hard limit of 1,000 pages; a repeated cursor or offset that doesn't advance fails as `jira_error` instead of looping. Each page request keeps the existing retry rules (GET retries, POST never does).
- [x] Not combinable with `--output`, `--include` or `--spec`. Errors on a later page report the page number; no partial output is printed.
- [x] Tests for every protocol, the limits, non-advancing pages, mid-run errors and rejected combinations; live read acceptance on BUG, board 1523 and the service desk endpoint.

Live, 9 October 2026 (`work` profile): project search over 2 offset pages (9 projects), POST and GET issue search over 5 cursor pages (30 and 10 unique issues, stopped by `--max-items`), and service desks over 3 pages of 1. Board 1523 has a single sprint, so its offset run stopped after one page as expected.

## 3. Service desk commands

`jira api` already reaches every Service Management endpoint. These commands cover the common read-and-respond workflow with readable output.

```sh
jira desk list                                  # service desks you can see
jira desk queues DESK                           # queues with issue counts
jira desk queue DESK QUEUE                      # issues in a queue
jira request list [--desk DESK] [--status open|closed|all]
jira request view KEY                           # request, status, participants
jira request comment KEY --message TEXT [--internal]
jira request transitions KEY
jira request transition KEY --to NAME|ID [--message TEXT]
```

- [x] Commands use the `/rest/servicedeskapi` endpoints with the existing identity resolver, retry rules, `--json`, `--csv` for lists, `--no-input` and redaction.
- [x] Customer-visible comments are the default only when stated in help; `--internal` adds an agent-only comment. Help and output say which one was made.
- [x] Desk and queue arguments accept an ID or an exact project key or name; ambiguous names fail with the candidates listed.
- [x] Fixture tests for every command, JSON/CSV shapes, pagination, permission errors and ambiguity; live read acceptance on the visible service desk. Writes (comments, transitions) are tested with fixtures only, because live writes notify customers.
- [x] Website command data regenerated; README and usage guide sections; sandbox sample data for at least `desk list` and `request view`.

Live, 9 October 2026: the `work` account is a customer on three desks (LDSUP, TS, VM), not an agent. `desk list`, `request list` (table and CSV), `request view` with participants and `request transitions` (none available to a customer on a closed request) were read live; `desk queues` returned the expected 403 with Jira's explanation, and an unknown desk listed the available ones. Queue listings, internal comments and transitions are covered by fixtures only; no live write was made, because comments and transitions notify customers.

## 4. An agent skill that ships with the CLI

The website has a prompt that asks an agent to write its own skill. Ship a maintained one instead, versioned with the CLI so it always matches the installed commands.

```sh
jira skill show                    # print SKILL.md
jira skill install                 # write ~/.claude/skills/jira/SKILL.md
jira skill install --path DIR      # any agent's skills or rules folder
```

- [x] `SKILL.md` covers when to use `jira` versus `jira api`, `--spec` before building a payload, `--json --no-input`, exit codes and the error object, pagination, the trust boundary, and safe defaults (no writes without the user asking, never print tokens).
- [x] Installed as package data, so pipx, Homebrew and the native binaries all carry it. `install` refuses to overwrite a changed file without `--force` and reports the path it wrote.
- [x] Tests check that every command the skill mentions exists in the parser, so the skill can't drift from the CLI.
- [x] Website setup step offers `jira skill install` next to the existing prompt.

## 5. Windows Package Manager (winget)

- [x] Manifests for `User17745.JiraCliToolkit` (portable installer, command alias `jira`), using the release's Windows binary URL and SHA-256 from the manifest. Generated by `scripts/release/winget.py` (schema 1.12.0).
- [x] Submit to `microsoft/winget-pkgs` from a fork, following its contribution rules. Microsoft's validation and review decide acceptance; note that the binary is not code-signed. Submitted as [microsoft/winget-pkgs#449318](https://github.com/microsoft/winget-pkgs/pull/449318). **Blocked on the maintainer:** Microsoft's CLA bot asks the PR author to reply `@microsoft-github-policy-service agree` (with `company="…"` if contributing for an employer); only the account owner can accept it.
- [x] `jira update` detects a winget installation and points to `winget upgrade` instead of replacing the file.
- [ ] Document `winget install User17745.JiraCliToolkit` once the package is accepted. Until then the README doesn't mention it.

## 6. Learning from real usage

- [x] GitHub issue templates for bug reports (with `jira update --info --json` output, which contains no secrets) and feature requests.
- [x] Record download counts (PyPI, GitHub releases, Homebrew tap) at each release in this roadmap, and let reported issues set the priorities after v2.6.

## 7. Release

- [x] Full regressions, website checks, clean wheel/sdist and native smoke checks.
- [x] Release candidate through the tag pipeline; verify assets, attestations and the PyPI pre-release.
- [x] Code review on the PR, merge, stable tag from `main`, then verify GitHub, PyPI, the Homebrew tap's automatic update and the user's pipx upgrade.

Release evidence, 9 October 2026:

- 224 Python tests and 55 website checks; clean wheel/sdist pass `twine check` and include `SKILL.md`; installed smoke checks pass.
- CodeRabbit raised 10 findings on [PR #14](https://github.com/User17745/jira-cli-toolkit/pull/14), all valid and fixed with regression tests: cursor pages with `isLast: false` and no token, offsets that don't advance, the service desk page limit, literal rendering of customer text, winget detection in machine-scope and registered custom roots, version checks before winget advice, sandbox CSV/JSON shapes and an issue-template option. One suggestion (`PortableCommandAlias`) proved wrong on Windows: it only applies to portables nested in a zip, and `Commands` names the link.
- v2.6.0rc1 and v2.6.0: all twelve tag jobs passed; assets match the manifest and checksums; all six files verify with `gh attestation verify`; PyPI received both; the native binary prints the bundled skill. Main CI, native builds and Pages passed on merge commit `321dd6a`, whose tree matches the tested PR head.
- [winget workflow](https://github.com/User17745/jira-cli-toolkit/actions/workflows/winget.yml) on windows-2025 (winget v1.11.510): "Manifest validation succeeded.", install verified the hash and added the `jira` alias, `jira --version` printed `jira 2.6.0`, and `jira update` reported `winget` and gave `winget upgrade --id User17745.JiraCliToolkit --exact`. The runner's winget can't be upgraded reliably, so manifests use schema 1.10.0, which winget-pkgs accepts.
- Homebrew: the tap's update workflow moved to 2.6.0 after verifying checksums and attestations; install tests passed on macOS arm64, macOS x86_64 and Linux x86_64.
- The user's pipx installation upgraded to 2.6.0 with `pipx upgrade jira-cli-toolkit`; live `request list --csv` and `api --paginate` work.

Downloads at release (most early GitHub downloads are this project's own release testing): PyPI 212 in the first week of publication; GitHub release assets v2.5.0 55, v2.5.1 29, v2.5.2 10, v2.6.0 5 on the day of release; Homebrew tap clones not yet reported by GitHub.

## Completion criteria

- [x] An agent can fetch every page of a supported endpoint with one command, bounded and without loops.
- [x] A service desk agent can list queues, read a request and reply from the terminal.
- [x] `jira skill install` gives an agent instructions that match the installed CLI.
- [x] Windows users can install with winget, or the submission's status is recorded with its blocker.
