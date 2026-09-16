# jira-support-cli

Support tickets from the terminal using **official Jira Cloud REST APIs** (no third-party wrapper).

Repo: private — `User17745/jira-support-cli`

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in site, email, API token
# API token: https://id.atlassian.com/manage-profile/security/api-tokens
```

Or export env directly:

```bash
export JIRA_SITE="https://YOUR-site.atlassian.net"
export JIRA_EMAIL="you@example.com"
export JIRA_API_TOKEN="xxxx"
export JIRA_PROJECT="SUP"
```

## Support workflow

```bash
# 1. who am I (checks auth)
python jira_cli.py me

# 2. create the support project (once)
python jira_cli.py project-create --key SUP --name "Support" --type software --lead-me

# 3. create tickets
python jira_cli.py issue-create -p SUP -s "Login fails on checkout" -d "steps to repro..." -t Task --priority High
python jira_cli.py issue-create -p SUP -s "Refund request #123" -d "customer asked..." -t Task --label support --label billing

# 4. track open items
python jira_cli.py open -p SUP
python jira_cli.py open -p SUP --jql "priority = High"
python jira_cli.py open -p SUP --json | jq .

# 5. review one
python jira_cli.py issue-show SUP-123

# 6. move through workflow
python jira_cli.py transitions SUP-123
python jira_cli.py issue-move SUP-123 --to "In Progress"
python jira_cli.py issue-move SUP-123 --to Done

# 7. comments
python jira_cli.py comment-add SUP-123 -m "Looking into it, will update today"
python jira_cli.py comment-list SUP-123
```

## APIs used (official)

- `GET /rest/api/3/myself`
- `POST /rest/api/3/project` / `GET /rest/api/3/project/{key}`
- `POST /rest/api/3/issue` / `GET /rest/api/3/issue/{key}`
- `GET /rest/api/3/search/jql` (fallback: `/rest/api/3/search`)
- `GET+POST /rest/api/3/issue/{key}/transitions`
- `GET+POST /rest/api/3/issue/{key}/comment`

Boards (`/rest/agile/1.0/board`) are read/create/delete only — no rename endpoint, so this CLI intentionally skips board CRUD.
