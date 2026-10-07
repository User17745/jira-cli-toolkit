# Developer migration: old jsup commands to v2

For installing v2 or migrating saved credentials, start with the [upgrade guide](upgrade-to-v2.md). This guide covers CLI invocations, aliases, output consumers and unattended scripts. Examples use `ENG`, issue `ENG-42`, board `123`, and sprint `456`; replace these with your own accessible resources. Names such as `Task` and `Done` must exist in your project's metadata/workflow.

## Compatibility and migration strategy

The distribution/import package is still `jsup`; the primary executable is `jira` starting with v2.1. All three executables (`jira`, `jira-cli-toolkit`, and `jsup`) accept grouped and legacy command names throughout v2.x. Existing scripts can keep `jsup issue-show ...` while you migrate one workflow at a time. Alias availability does not preserve every old query, dashboard, pagination or credential behavior; review the changes below.

Use `jira <resource> <action>` for new work. V2.1 installs `jira` directly; remove any old shell alias that hides it. The repository name remains `jira-cli-toolkit`. If another Jira CLI owns `jira` on your PATH, choose which installation provides it or invoke the retained `jira-cli-toolkit` alias explicitly. CLI compatibility does not promise stability for private Python implementation helpers.

Suggested order: upgrade/install, verify authentication, migrate read-only queries and output handling, then migrate creation/transitions after inspecting project metadata. Test writes in a disposable project with appropriate permissions and a cleanup arrangement.

Invoking `jsup` or `jira-cli-toolkit` prints a startup warning on stderr pointing to `jira`. Legacy names remain supported throughout v2.x and may be deprecated in a future major release. JSON stdout remains unchanged; internal completion/update helpers suppress the notice.

## Old-to-new command reference

These are implemented v2 commands. Flags not shown retain their operation-specific meaning unless noted below. Use help for the full option list.

| Old invocation | Grouped v2 invocation | Migration note |
| --- | --- | --- |
| `jsup` | `jira` | New root shows local context; `jsup` root still opens a dashboard |
| `jsup dashboard -p ENG` | `jira dashboard -p ENG` | Choose project(s) explicitly; human counts are approximate |
| `jsup config init` | `jira auth login --profile work` | New profile setup; existing saved identity uses `config migrate` first |
| `jsup config show` | `jira config show` | Schema-2 preferences contain profile references, not tokens |
| `jsup me` | `jira user me` | `auth status` additionally describes credential health/source |
| `jsup project-list` | `jira project list` | Pagination controls are available |
| `jsup project-show ENG` | `jira project view ENG` | Same project key argument |
| `jsup open -p ENG` | `jira issue list -p ENG --open` | Keep `--open` to exclude Done |
| `jsup issue-create -p ENG -s "Fix login"` | `jira issue create -p ENG -s "Fix login" --type Task` | Discover a valid type and required fields; grouped creation has no Task default |
| `jsup intake -p ENG` | `jira issue create -p ENG --template callback` | Explicit template/variables replace the legacy wizard; template defaults need project compatibility |
| `jsup issue-show ENG-42` | `jira issue view ENG-42` | API view; add `--web` for the browser |
| `jsup transitions ENG-42` | `jira issue transitions ENG-42` | Lists available workflow actions |
| `jsup issue-move ENG-42 --to Done` | `jira issue transition ENG-42 --to Done` | Transition name/ID, not a move between projects; required fields are supported |
| `jsup issue-delete ENG-42 --yes` | `jira issue delete ENG-42 --yes` | Permanent deletion still needs explicit confirmation in scripts |
| `jsup comment-add ENG-42 -m "On it"` | `jira issue comment add ENG-42 -m "On it"` | Also supports message files/editor |
| `jsup comment-list ENG-42` | `jira issue comment list ENG-42` | Pagination controls are available |
| `jsup board-list --jql-project ENG` | `jira board list -p ENG` | Grouped board list uses the selected project by default |
| `jsup board-create -p ENG --name Delivery` | `jira board create -p ENG --name Delivery` | Existing JQL/filter/type options remain |
| `jsup board-issues 123 --max 50` | `jira board issues 123 --limit 50` | `--max` remains an alias; limit bounds total results |
| `jsup board-feature 123 --feature jsw.agility.reports --enable` | `jira board feature enable 123 --feature jsw.agility.reports` | Availability is governed by board capability/permissions |
| `jsup board-feature 123 --feature jsw.agility.reports --disable` | `jira board feature disable 123 --feature jsw.agility.reports` | Enable/disable becomes the action |
| `jsup sprint-list --board 123` | `jira sprint list --board 123` | Grouped form may use a saved default board |
| `jsup sprint-create --board 123 --name Iteration` | `jira sprint create --board 123 --name Iteration` | Existing goal option remains |
| `jsup sprint-state 456 active` | `jira sprint start 456` | Jira must allow the state transition |
| `jsup sprint-state 456 closed` | `jira sprint close 456` | Jira must allow the state transition |
| `jsup sprint-state 456 future` | `jira sprint edit 456 --state future` | State is an explicit flag in grouped edit |
| `jsup sprint-add 456 ENG-42 ENG-43` | `jira sprint add-issues 456 ENG-42 ENG-43` | Same sprint ID and issue keys |
| `jsup component-list -p ENG` | `jira component list -p ENG` | Same project selection |
| `jsup component-create -p ENG --name Backend --desc "API work"` | `jira component create -p ENG --name Backend --description "API work"` | `--desc` remains an alias |
| `jsup browse ENG-42` | `jira issue view ENG-42 --web` | Uses browser session; only a site URL is needed |
| `jsup browse board:123` | `jira board view 123 --web` | Board URL does not depend on a default project |

V2 adds `help`, auth/profile/context/doctor commands, metadata discovery, issue editing/assignment/relationships/attachments, comment maintenance, templates, completion, CSV and updates. See the [README](../../README.md) for these workflows. Generic `api`/`--spec` requests are [planned for v2.5](../sprints/v2.5-api/roadmap.md) and do not exist in v2.0.0.

## Behavior changes that affect scripts

### Query scope, open issues and boards

Grouped `issue list` includes Done unless you pass `--open`. Legacy `open --jql` appends a condition to the selected project's unfinished-issue query; grouped `issue list --jql` treats the argument as a complete query and ignores the saved/environment default project.

```sh
# Old: project ENG, unfinished issues, plus an extra condition.
jsup open -p ENG --jql 'priority = High' --max 100 --json

# New equivalent: express all conditions and ordering in complete JQL.
jira issue list \
  --jql 'project = "ENG" AND statusCategory != Done AND priority = High ORDER BY updated DESC' \
  --limit 100 --json --no-input
```

Do not add `--project`, `--open`, generated assignee/status/type/label/board filters, or nondefault ordering flags to complete JQL. Put those conditions/order into the JQL itself. For a generated query, use `issue list -p ENG --open --assignee me` without `--jql`.

Grouped `board list` filters by the selected project; legacy `board-list` still lists all accessible boards unless `--jql-project` is given. To retain that unfiltered behavior, keep `jsup board-list` or use `jira board-list`. `--all` fetches every page; it does not clear project filtering. An `issue list --board 123` query uses the board scope and ignores a saved project unless `--project` is explicit.

The old implicit RP/RD/BUG dashboard project set is gone. Select `dashboard --projects ENG HR`, or configure a default project. `jira` without a command is a local context display and performs no dashboard API query.

### Creation, custom fields and transitions

Legacy `issue-create` retains its Task/default-payload path. Grouped creation discovers issue types and creation fields for the selected project. Interactive use guides missing values; scripts supply a valid type, summary and all required fields.

```sh
jira project issue-types ENG --json --no-input
jira project fields ENG --type Task --json --no-input

# A write example: use only in a test project after reviewing required fields.
jira issue create -p ENG --type Task \
  --summary "Fix login" --description-file description.txt \
  --field customfield_12345=2026-10-07 --json --no-input
```

The custom field is an example date field: replace its ID/type/value using discovery. `--field FIELD=VALUE` uses metadata for conversion; `--field FIELD:=JSON` supplies structured JSON. `--fields-file` accepts a JSON object keyed by field ID/name. Ambiguous names need IDs; type/option selections support `id:ID`. Add `--refresh` when rediscovering changed creation metadata. `--description` and `--description-file` have legacy `--desc`/`--desc-file` aliases.

`issue transition ENG-42 --to NAME_OR_ID` acts on the available transition ID/name, not a target status ID. The grouped form supports `--field`/`--fields-file` for required transition fields. Headless use needs `--to`; inspect `issue transitions` first. Jira remains authoritative for validators not exposed in metadata. After an uncertain write/network outcome, inspect the issue before retrying; recovery does not automatically replay the write.

Legacy `intake` remains explicitly tied to callback behavior. The `callback` template defaults to Task, High priority, the `callback` label and `ops-runbook` component. Inspect it with `template show callback` and validate it against the project before scripted creation. Use `--var name=Alice --var issue="Cannot sign in" --var callback="Tomorrow"` to supply its variables. Override defaults with explicit flags or a project-specific template; optional components can be cleared with `--field 'components:=[]'` on a compatible project. Ordinary `issue create` injects no callback metadata.

### Pagination and JSON consumers

`--limit`/`--max` is a positive total-result bound across pages, not a page size. `--all` overrides the limit and follows every page. Search uses the enhanced POST/cursor API; scripts must not rely on the old deprecated-search fallback or require an exact `total` on every response. Paged API objects add `fetched`; inspect `issues`/`values` as appropriate. Some resource lists are arrays, so do not assume a uniform envelope.

New grouped `jira --json` runtime errors are JSON objects on **stdout** with a nonzero exit code:

```json
{"error":{"code":"jira_error","message":"...","status":403}}
```

Other codes include `invalid_input`, `network_error`, `uncertain_outcome`, `file_error` and `aborted`; HTTP status is present for Jira errors. Argparse usage errors still go to stderr. The `jsup` executable and legacy aliases keep runtime errors on stderr. If a script switches only the executable, or only the command spelling, verify which error contract it now uses. Progress/spinners use stderr.

Legacy `jsup dashboard --json` retains `project`/`hint`. Grouped `jira dashboard --json` returns `site` and project results with approximate `count` values or per-project errors. `config show --json` also changes from legacy fields to schema-2 profile preferences after migration. Update consumers rather than scraping human tables or requiring old dashboard/config shapes.

| Exit code | Meaning |
| --- | --- |
| 0 | Success, including help/version |
| 1 | Jira/API, network or uncertain-write failure |
| 2 | Usage, missing configuration/input, local file failure or declined confirmation |
| 130 | Interrupted input/operation |

`--json`, `--no-input`, and nonterminal input disable prompts. They do not confirm destructive operations: issue/link/comment/attachment deletion and standalone updates still require `--yes` for scripts. Here is a Bash example that checks the CLI's exit code before consuming JSON; `jq` is an optional external dependency:

```sh
#!/usr/bin/env bash
set -euo pipefail
jira_exit_code=0
jira issue list --profile work --project ENG --open \
  --all --json --no-input > issues.json || jira_exit_code=$?
if [ "$jira_exit_code" -ne 0 ]; then
  cat issues.json >&2
  exit "$jira_exit_code"
fi
jq -r '.issues[] | [.key, .fields.summary] | @tsv' issues.json
```

## Credentials and project selection

Migration moves saved credentials into `~/.config/jsup/config.json` schema-2 preferences and the selected secret store. Stop reading `JIRA_API_TOKEN` from that JSON in scripts; the token is no longer there. Choose a profile, or have your CI secret mechanism provide a complete `JIRA_SITE`, `JIRA_EMAIL`, `JIRA_API_TOKEN` environment identity.

| Selection in schema 2 | Behavior |
| --- | --- |
| Explicit `--profile work` or `JIRA_PROFILE=work` | Uses that profile's complete identity; ignores identity environment variables |
| Complete `--site`, `--email`, `--token` with no explicit profile | Uses that complete flag identity; avoid credential-bearing command arguments in scripts |
| Complete identity environment, with no explicit profile/identity flags | Uses the environment identity |
| Neither explicit identity nor environment identity | Uses the active profile |
| Partial identity flags/environment | Fails instead of borrowing another profile's missing values |
| `--project` or `JIRA_PROJECT` | Overrides project independently; does not change the account |

Combining identity flags with explicit profile selection is rejected. When using CI environment authentication, omit `--profile` and ensure `JIRA_PROFILE` is unset; setting it selects the saved profile instead. For desktop scripts, `--profile work` avoids accidental identity overrides from environment variables. The legacy pre-migration file retains per-setting precedence until migration succeeds.

A complete flag/environment identity also does not inherit a saved profile's project or board. Supply `--project` or `JIRA_PROJECT` explicitly, and `--board` when needed for software operations. This matters to old scripts that supplied all credentials through the environment but borrowed a project from the legacy config.

Native macOS access must already be approved for headless commands; Linux scripted wallet access is rejected and needs a complete environment identity or explicit POSIX file storage. `auth status` checks identity; `doctor --project ENG` also checks project access. `auth logout` removes a local credential without revoking the upstream token or clearing environment variables. API tokens have no automatic refresh; auth recovery never retries the original write for you.

## Check your migrated workflow

- [ ] Install v2 with the existing manager; both executables report the intended version.
- [ ] Select the intended identity and project; verify status and doctor.
- [ ] Compare old and new read-only query scope, issue keys and pagination.
- [ ] Update JSON/config/dashboard consumers and preserve nonzero exit codes.
- [ ] Supply explicit values and confirmation flags in unattended commands.
- [ ] Discover the project's types/required fields and transitions before migrating writes.
- [ ] Test mutations with a disposable resource and an authorized cleanup plan.
- [ ] Remove plaintext-token assumptions from scripts, configs and templates.

Find command help without contacting Jira:

```sh
jira --help
jira help issue create
jira help issue comment add
jira help sprint edit
```
