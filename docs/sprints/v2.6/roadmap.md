# v2.6 — Paginated API calls, service desk commands, an agent skill and winget

Decision recorded: 9 October 2026. Status: planned. None of the commands below exist in v2.5.2.

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

- [ ] Commands use the `/rest/servicedeskapi` endpoints with the existing identity resolver, retry rules, `--json`, `--csv` for lists, `--no-input` and redaction.
- [ ] Customer-visible comments are the default only when stated in help; `--internal` adds an agent-only comment. Help and output say which one was made.
- [ ] Desk and queue arguments accept an ID or an exact project key or name; ambiguous names fail with the candidates listed.
- [ ] Fixture tests for every command, JSON/CSV shapes, pagination, permission errors and ambiguity; live read acceptance on the visible service desk. Writes (comments, transitions) are tested with fixtures only, because live writes notify customers.
- [ ] Website command data regenerated; README and usage guide sections; sandbox sample data for at least `desk list` and `request view`.

## 4. An agent skill that ships with the CLI

The website has a prompt that asks an agent to write its own skill. Ship a maintained one instead, versioned with the CLI so it always matches the installed commands.

```sh
jira skill show                    # print SKILL.md
jira skill install                 # write ~/.claude/skills/jira/SKILL.md
jira skill install --path DIR      # any agent's skills or rules folder
```

- [ ] `SKILL.md` covers when to use `jira` versus `jira api`, `--spec` before building a payload, `--json --no-input`, exit codes and the error object, pagination, the trust boundary, and safe defaults (no writes without the user asking, never print tokens).
- [ ] Installed as package data, so pipx, Homebrew and the native binaries all carry it. `install` refuses to overwrite a changed file without `--force` and reports the path it wrote.
- [ ] Tests check that every command the skill mentions exists in the parser, so the skill can't drift from the CLI.
- [ ] Website setup step offers `jira skill install` next to the existing prompt.

## 5. Windows Package Manager (winget)

- [ ] Manifests for `User17745.JiraCliToolkit` (portable installer, command alias `jira`), using the release's Windows binary URL and SHA-256 from the manifest.
- [ ] Submit to `microsoft/winget-pkgs` from a fork, following its contribution rules. Microsoft's validation and review decide acceptance; note that the binary is not code-signed.
- [ ] `jira update` detects a winget installation and points to `winget upgrade` instead of replacing the file.
- [ ] Document `winget install User17745.JiraCliToolkit` once the package is accepted.

## 6. Learning from real usage

- [ ] GitHub issue templates for bug reports (with `jira update --info --json` output, which contains no secrets) and feature requests.
- [ ] Record download counts (PyPI, GitHub releases, Homebrew tap) at each release in this roadmap, and let reported issues set the priorities after v2.6.

## 7. Release

- [ ] Full regressions, website checks, clean wheel/sdist and native smoke checks.
- [ ] Release candidate through the tag pipeline; verify assets, attestations and the PyPI pre-release.
- [ ] Code review on the PR, merge, stable tag from `main`, then verify GitHub, PyPI, the Homebrew tap's automatic update and the user's pipx upgrade.

## Completion criteria

- [ ] An agent can fetch every page of a supported endpoint with one command, bounded and without loops.
- [ ] A service desk agent can list queues, read a request and reply from the terminal.
- [ ] `jira skill install` gives an agent instructions that match the installed CLI.
- [ ] Windows users can install with winget, or the submission's status is recorded with its blocker.
