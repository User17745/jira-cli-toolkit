# jsup — Jira support-ticket CLI with a friendly TUI

Official Jira Cloud REST APIs only (platform v3 + Agile 1.0), Rich terminal UI.
Built for the RTR workflow: **RP** support kanban + **RD** sprint board.

## Install

```bash
pipx install .
jsup config init   # site, email, API token (https://id.atlassian.com/manage-profile/security/api-tokens), default project
jsup me
```

Config lives in `~/.config/jsup/config.json` (mode 600). Env vars
`JIRA_SITE` / `JIRA_EMAIL` / `JIRA_API_TOKEN` / `JIRA_PROJECT` also work and
override the file; `--site/--email/--token/-p` flags override everything.
`--json` on any command gives raw JSON for scripts.

## Daily use

```bash
jsup                        # dashboard: open counts per project
jsup open -p RP             # open support tickets
jsup open -p RP --jql "priority = Highest"
jsup intake -p RP           # guided callback-task wizard (name, issue, callback time)
jsup issue-show RP-21
jsup issue-move RP-21       # interactive transition picker (or --to "In Progress")
jsup comment-add RP-21 -m "On it, will update today"
jsup comment-list RP-21
jsup browse RP-21           # open in browser
```

## Sprint planning (RD)

```bash
jsup sprint-list --board 1525
jsup sprint-create --board 1525 --name "RD Sprint 2" --goal "Kill blocker B"
jsup sprint-add 1612 RP-21 RP-22
jsup sprint-state 1612 active   # active | closed | future
```

## Boards & project setup

```bash
jsup board-list --jql-project RP
jsup board-create -p RP --name "RTR Support" --type kanban
jsup board-issues 1526
jsup board-feature 1525 --feature jsw.agility.reports --enable  # team-managed only
jsup component-list -p RP
jsup project-list
```

## API limits (verified against Atlassian's OpenAPI spec)

- **No rename-board endpoint** (`/board/{id}` = GET + DELETE only) — rename in UI.
- **No column-write endpoint** (`/configuration` = GET only) — columns in UI.
- Project/component creation needs project admin; project creation needs Jira admin.
- RP `Bug` type requires the **Test Case Actual Result** (rich-text) field.
