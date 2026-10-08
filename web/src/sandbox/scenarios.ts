// Agent sessions replayed in the sandbox. Each starts from a plain-language request. `jira` tool calls
// run against the sample site, so their output is what the sandbox prints and their writes stay in it.
// Other programs (pytest, git) and file edits have fixed, illustrative results; so does a `jira` step
// with `output`, which shows what a fresh install prints when the always-signed-in sandbox can't.
export type Step =
  | { say: string }
  | { run: string; output?: string; exit?: number }
  | { tool: 'Write' | 'Edit'; file: string; result: string }
  | { reply: string }
export type Scenario = { id: string; prompt: string; steps: Step[]; after: string }

const plan: Scenario = {
  id: 'plan',
  prompt: 'Plan the checkout launch (APP) into weekly sprints on board 18. Keep everyone at or under 80% so there’s room for ad-hoc work, run the streams in parallel, and don’t schedule anything before what it depends on lands. Test the plan before you touch Jira.',
  steps: [
    { say: 'I’ll start with the backlog, including owners and estimates.' },
    { run: 'jira issue list -p APP --open --json --fields summary,assignee,labels,customfield_10016' },
    { say: '13 issues, 54 points across business, product, backend, frontend and QA. I’ll write the plan as a file, with a test for each of your rules.' },
    { tool: 'Write', file: 'plan.yaml', result: 'Wrote 41 lines to plan.yaml' },
    { tool: 'Write', file: 'tests/test_plan.py', result: 'Wrote 64 lines to tests/test_plan.py' },
    { run: 'pytest tests/test_plan.py -q', exit: 1, output: [
      'F.F...                                                     [100%]',
      'FAILED test_plan.py::test_capacity - Jamie Lee has 13 points in week 1; the limit is 8 (80% of 10)',
      'FAILED test_plan.py::test_dependencies - APP-11 (qa) is in week 1, before APP-8 (frontend) lands',
      '2 failed, 4 passed in 0.04s',
    ].join('\n') },
    { say: 'Two rules fail. Moving APP-9 to week 2, and APP-11 to week 3, after the checkout UI and form validation land.' },
    { tool: 'Edit', file: 'plan.yaml', result: 'Updated plan.yaml: APP-9 → week 2, APP-11 → week 3' },
    { run: 'pytest tests/test_plan.py -q', output: '......                                                     [100%]\n6 passed in 0.03s' },
    { say: 'All six checks pass. Creating the sprints and filling them.' },
    { run: "jira sprint create --board 18 --name 'APP Week 1' --goal 'Spec, payments API and checkout UI'" },
    { run: 'jira sprint add-issues 458 APP-1 APP-3 APP-5 APP-8 APP-13' },
    { run: "jira sprint create --board 18 --name 'APP Week 2' --goal 'Webhooks, form validation and load tests'" },
    { run: 'jira sprint add-issues 459 APP-2 APP-4 APP-6 APP-9 APP-12' },
    { run: "jira sprint create --board 18 --name 'APP Week 3' --goal 'Refunds, confirmation page and end-to-end tests'" },
    { run: 'jira sprint add-issues 460 APP-7 APP-10 APP-11' },
    { run: 'jira sprint list --board 18' },
    { reply: [
      'Planned APP into three weekly sprints on board 18:',
      '',
      '  Week 1  APP-1 APP-3 APP-5 APP-8 APP-13',
      '  Week 2  APP-2 APP-4 APP-6 APP-9 APP-12',
      '  Week 3  APP-7 APP-10 APP-11',
      '',
      'All five streams start in week 1. Nobody has more than 8 of 10 points in any week, so 20% stays free for ad-hoc work.',
      'QA writes the test plan in week 1 and runs the end-to-end tests once the UI lands.',
    ].join('\n') },
  ],
  after: 'The sample site kept these sprints. Try jira sprint list --board 18 or jira issue view APP-9.',
}

const standupSteps: Step[] = [
  { say: 'Checking the active sprint and its open issues, with links.' },
  { run: 'jira sprint list --state active --json' },
  { run: 'jira issue list --open --json --fields summary,status,assignee,updated,issuelinks' },
]
const digest = [
  'ENG Sprint 14 · 4 open issues',
  '',
  'Blocked   ENG-42 Ship the onboarding flow (Alex)',
  '          waits on OPS-7 Rotate the staging API token (Sam, To Do)',
  'Stale     ENG-45 Document exit codes (Sam): In Review for 6 days',
  'Unowned   ENG-44 Update release notes for v2.1',
  'On track  ENG-43 Fix keyboard navigation in the issue picker (Jamie)',
].join('\n')

const standup: Scenario = {
  id: 'standup',
  prompt: 'Give me a standup digest for the active ENG sprint: what’s blocked, what’s stale, and who’s waiting on whom. Nudge whoever can unblock the most.',
  steps: [
    ...standupSteps,
    { say: 'OPS-7 blocks ENG-42, so it unblocks the most. Asking Sam on the ticket.' },
    { run: "jira issue comment add OPS-7 --message 'ENG-42 (onboarding) is waiting on this token. Can it go first today?'" },
    { reply: `${digest}\n\nI asked Sam on OPS-7 to take it first today.` },
  ],
  after: 'Try jira issue view OPS-7 to see the new comment count.',
}

const merge: Scenario = {
  id: 'merge',
  prompt: 'PR #142 just merged. Update Jira to match.',
  steps: [
    { run: 'git log -1 --format=%s', output: 'fix(picker): keep the last option reachable when the list scrolls (ENG-43)' },
    { say: 'The merged commit references ENG-43. Moving it to Done and linking the fix.' },
    { run: 'jira issue transition ENG-43 --to Done' },
    { run: "jira issue comment add ENG-43 --message 'Fixed in #142. Ships in v2.1.'" },
    { reply: 'ENG-43 is Done, with a comment linking #142. Nothing else in the sprint needed a change.' },
  ],
  after: 'Try jira issue list --open: ENG-43 is no longer there.',
}

const triage: Scenario = {
  id: 'triage',
  prompt: 'Tidy the ENG backlog before planning. Give unowned work to someone with room for it, and make sure anything blocking other work is marked and prioritised.',
  steps: [
    { say: 'Reading every open ENG issue with owners, priorities and links.' },
    { run: 'jira issue list --open --json --fields summary,status,assignee,priority,labels,issuelinks' },
    { say: 'ENG-44 has no owner. Alex is mid-way through the onboarding flow and Sam owns the blocker, so ENG-44 goes to Jamie. OPS-7 blocks ENG-42 but is only High.' },
    { run: "jira issue assign ENG-44 --user 'Jamie Lee'" },
    { run: 'jira issue edit OPS-7 --priority Highest --add-label blocker' },
    { reply: [
      'Backlog tidied:',
      '',
      '  ENG-44  Update release notes for v2.1: assigned to Jamie Lee',
      '  OPS-7   Rotate the staging API token: raised to Highest and',
      '          labelled blocker, since ENG-42 waits on it',
      '',
      'No other open ENG issue is unowned or blocked.',
    ].join('\n') },
  ],
  after: 'Try jira issue view OPS-7 or jira issue list --open.',
}

const incident: Scenario = {
  id: 'incident',
  prompt: 'Checkout has returned 502s since this morning’s 09:10 deploy; we rolled back at 09:31. File the incident in OPS with the timeline, plus follow-ups so it can’t happen again.',
  steps: [
    { say: 'Checking OPS for an existing report first.' },
    { run: 'jira issue list -p OPS --open --json --fields summary,status,labels' },
    { say: 'Nothing filed yet. Creating the incident, then two follow-ups.' },
    { run: "jira issue create -p OPS --type Bug --priority Highest --label incident --summary 'Checkout returns 502 after the 09:10 deploy'" },
    { run: "jira issue comment add OPS-8 --message 'Timeline: 09:10 deploy; 09:14 first 502s; 09:31 rolled back; 09:33 error rate normal.'" },
    { run: "jira issue create -p OPS --type Task --label incident --summary 'Add a canary stage before checkout deploys'" },
    { run: "jira issue create -p OPS --type Task --label incident --summary 'Alert when the checkout 5xx rate is above 1%'" },
    { reply: [
      'Filed the incident and its follow-ups in OPS:',
      '',
      '  OPS-8   Bug, Highest  Checkout returns 502 after the 09:10 deploy',
      '  OPS-9   Task          Add a canary stage before checkout deploys',
      '  OPS-10  Task          Alert when the checkout 5xx rate is above 1%',
      '',
      'The timeline is a comment on OPS-8, and all three are labelled incident.',
      'Should I assign owners, or link the follow-ups to OPS-8?',
    ].join('\n') },
  ],
  after: 'Try jira issue list -p OPS --open.',
}

const release: Scenario = {
  id: 'release',
  prompt: 'Draft release notes from everything finished in the last ENG sprint, grouped into new features and fixes.',
  steps: [
    { say: 'Finding the last closed sprint and what was finished in it.' },
    { run: 'jira sprint list --state closed --json' },
    { run: 'jira issue list --status Done --json --fields summary,issuetype,customfield_10020' },
    { reply: [
      'Release notes for v2.0 (ENG Sprint 13):',
      '',
      'New',
      '  - Install with one command on macOS and Linux (ENG-37)',
      '  - Export issue lists as CSV (ENG-39)',
      '',
      'Fixed',
      '  - Tokens are redacted from error output (ENG-38)',
      '',
      'Should I post this on ENG-44, the release-notes task?',
    ].join('\n') },
  ],
  after: 'Try jira issue list --status Done.',
}

const firstRun: Scenario = {
  id: 'setup',
  prompt: 'What’s open in ENG?',
  steps: [
    { say: 'Checking that the Jira CLI is signed in first.' },
    { run: 'jira auth status --json --no-input', exit: 2, output: '{\n  "error": {\n    "code": "invalid_input",\n    "message": "No complete credentials. Run auth login or config migrate."\n  }\n}' },
    { reply: [
      'The Jira CLI isn’t signed in yet, so I can’t read ENG. In your own terminal:',
      '',
      '  1. jira auth login --profile work',
      '     It links to API-token creation and keeps the token in your OS credential store.',
      '  2. On macOS: jira auth status --profile work, then choose Always Allow.',
      '  3. jira context use --project ENG',
      '',
      'Tell me when that’s done and I’ll list what’s open. Please don’t paste the token here.',
    ].join('\n') },
  ],
  after: 'The sandbox is always signed in, so this replay shows what a fresh install prints.',
}

export const scenarios = { plan, standup, merge, triage, incident, release, setup: firstRun }
export type ScenarioId = keyof typeof scenarios
// The terminal opens on a finished, read-only standup session, so the sample site is unchanged.
export const intro: Scenario = { ...standup, prompt: 'Give me a standup digest for the active ENG sprint: what’s blocked, what’s stale, and who’s waiting on whom.', steps: [...standupSteps, { reply: digest }], after: 'That was a replay. Type a jira command yourself, or press → for jira --help.' }
