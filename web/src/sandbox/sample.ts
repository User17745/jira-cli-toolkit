// Sample site for the sandbox. Every name, key and account here is illustrative.
export type Category = 'new' | 'indeterminate' | 'done'
export type Status = { id: string; name: string; category: Category }
export type User = { accountId: string; displayName: string; emailAddress: string }
export type Issue = {
  key: string; summary: string; status: string; type: string; priority: string
  assignee: string | null; labels: string[]; components: string[]; updated: string
  description: string; comments: number
  // Story point estimate, sprint ID and blocking issue keys; absent on most issues.
  points?: number; sprint?: number; blockedBy?: string[]
}
export type Sprint = { id: number; state: string; name: string; goal: string; board: number }

export const site = 'https://example.atlassian.net'
export const profile = { name: 'work', project: 'ENG', board: 12 }

export const statuses: Status[] = [
  { id: '11', name: 'To Do', category: 'new' },
  { id: '21', name: 'In Progress', category: 'indeterminate' },
  { id: '31', name: 'In Review', category: 'indeterminate' },
  { id: '41', name: 'Done', category: 'done' },
]

export const users: User[] = [
  { accountId: '712020:4f1c0b9e-alex', displayName: 'Alex Rivera', emailAddress: 'alex@example.com' },
  { accountId: '712020:9d2e7a31-jamie', displayName: 'Jamie Lee', emailAddress: 'jamie@example.com' },
  { accountId: '712020:c08b55f2-sam', displayName: 'Sam Okafor', emailAddress: 'sam@example.com' },
  { accountId: '712020:1a7e3c90-priya', displayName: 'Priya Shah', emailAddress: 'priya@example.com' },
  { accountId: '712020:6b42d1e8-noor', displayName: 'Noor Haddad', emailAddress: 'noor@example.com' },
]
export const me = users[0]

export const issueTypes = [
  { id: '10001', name: 'Story' },
  { id: '10002', name: 'Task' },
  { id: '10003', name: 'Bug' },
]

export const projects = [
  { key: 'ENG', name: 'Engineering' },
  { key: 'OPS', name: 'Operations' },
  { key: 'APP', name: 'Checkout launch' },
]

export const boards = [
  { id: 12, type: 'scrum', name: 'ENG board', project: 'ENG' },
  { id: 15, type: 'kanban', name: 'OPS flow', project: 'OPS' },
  { id: 18, type: 'scrum', name: 'APP board', project: 'APP' },
]

export const initialSprints = (): Sprint[] => [
  { id: 455, state: 'closed', name: 'ENG Sprint 13', goal: 'Release v2.0 installers', board: 12 },
  { id: 456, state: 'active', name: 'ENG Sprint 14', goal: 'Ship onboarding and keyboard fixes', board: 12 },
  { id: 457, state: 'future', name: 'ENG Sprint 15', goal: 'Release notes and docs polish', board: 12 },
]

// The checkout launch backlog: one label per work stream, estimated but not yet planned into sprints.
const backlog: [string, string, string, number, number][] = [
  ['Write pricing page copy and launch plan', 'business', 'Story', 3, 3],
  ['Draft the partner announcement', 'business', 'Task', 2, 3],
  ['Write the checkout spec and acceptance criteria', 'product', 'Story', 3, 0],
  ['Define checkout analytics events', 'product', 'Task', 2, 0],
  ['Build the payments API', 'backend', 'Story', 8, 2],
  ['Send order webhooks', 'backend', 'Story', 5, 2],
  ['Add the refunds endpoint', 'backend', 'Story', 5, 2],
  ['Build the checkout UI', 'frontend', 'Story', 8, 1],
  ['Validate the payment form', 'frontend', 'Story', 5, 1],
  ['Build the order confirmation page', 'frontend', 'Story', 3, 1],
  ['Write end-to-end checkout tests', 'qa', 'Task', 5, 4],
  ['Load test the payments API', 'qa', 'Task', 3, 4],
  ['Write the checkout test plan', 'qa', 'Task', 2, 4],
]

export function initialIssues(): Issue[] {
  return [
    { key: 'ENG-42', summary: 'Ship the onboarding flow', status: 'In Progress', type: 'Story', priority: 'High', assignee: users[0].accountId, labels: ['onboarding'], components: ['web'], updated: '2026-10-06', description: 'Walk new users from install to their first issue list.', comments: 3, blockedBy: ['OPS-7'] },
    { key: 'ENG-43', summary: 'Fix keyboard navigation in the issue picker', status: 'To Do', type: 'Bug', priority: 'Medium', assignee: users[1].accountId, labels: ['accessibility'], components: ['cli'], updated: '2026-10-05', description: 'Arrow keys skip the last option when the list scrolls.', comments: 1 },
    { key: 'ENG-44', summary: 'Update release notes for v2.1', status: 'To Do', type: 'Task', priority: 'Low', assignee: null, labels: ['release'], components: [], updated: '2026-10-02', description: '', comments: 0 },
    { key: 'ENG-45', summary: 'Document exit codes for scripts', status: 'In Review', type: 'Task', priority: 'Medium', assignee: users[2].accountId, labels: ['docs'], components: ['cli'], updated: '2026-10-01', description: 'List 0, 1, 2 and 130 with one example each.', comments: 2 },
    { key: 'ENG-39', summary: 'Add CSV export to issue list', status: 'Done', type: 'Story', priority: 'Medium', assignee: users[0].accountId, labels: ['scripting'], components: ['cli'], updated: '2026-09-28', description: '', comments: 4, sprint: 455 },
    { key: 'ENG-38', summary: 'Redact tokens from error output', status: 'Done', type: 'Bug', priority: 'High', assignee: users[2].accountId, labels: ['security'], components: ['cli'], updated: '2026-09-27', description: '', comments: 2, sprint: 455 },
    { key: 'ENG-37', summary: 'Install with one command on macOS and Linux', status: 'Done', type: 'Story', priority: 'High', assignee: users[1].accountId, labels: ['release'], components: ['cli'], updated: '2026-09-26', description: '', comments: 5, sprint: 455 },
    { key: 'OPS-7', summary: 'Rotate the staging API token', status: 'To Do', type: 'Task', priority: 'High', assignee: users[2].accountId, labels: [], components: [], updated: '2026-10-04', description: 'The onboarding flow needs a working staging token.', comments: 0 },
    ...backlog.map(([summary, stream, type, points, owner], i): Issue => ({
      key: `APP-${i + 1}`, summary, status: 'To Do', type, priority: 'Medium', assignee: users[owner].accountId,
      labels: [stream], components: [], updated: '2026-10-06', description: '', comments: 0, points,
    })),
  ]
}
