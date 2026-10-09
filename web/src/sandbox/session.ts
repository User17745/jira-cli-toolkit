// Runs parsed commands against the sample site and formats results the way jira prints them.
import { help, usage } from './help.ts'
import { parse, tokenize, type Values } from './parse.ts'
import { boards, desks, requests, initialIssues, initialSprints, issueTypes, me, profile, projects, site, statuses, users, type Issue } from './sample.ts'
import { child, root, type Node } from './tree.ts'

export type Tone = 'new' | 'indeterminate' | 'done' | 'active' | 'future' | 'closed' | 'bold'
export type Cell = { text: string; tone?: Tone }
export type Block =
  | { kind: 'text'; stream: 'stdout' | 'stderr'; text: string }
  | { kind: 'table'; title: string; columns: string[]; rows: Cell[][] }
  | { kind: 'panel'; title: string; subtitle: string; heading: [string, string]; lines: string[] }
  | { kind: 'note'; text: string }
  // An agent session in a replay; never produced by jira itself. A tool with output null is still running.
  | { kind: 'session' }
  | { kind: 'ask'; text: string }
  | { kind: 'say' | 'reply'; text: string }
  | { kind: 'tool'; name: 'Bash' | 'Write' | 'Edit'; input: string; output: Block[] | null; exit: number }
export type Result = { blocks: Block[]; exit: number | null }

const LIST_COMMANDS = new Set(['issue list', 'board list', 'board issues', 'project list', 'issue comment list', 'sprint list', 'component list', 'project issue-types', 'project fields', 'issue attachment list'])
const PRIORITY = ['Highest', 'High', 'Medium', 'Low', 'Lowest']
const DEFAULT_FIELDS = ['summary', 'status', 'assignee', 'priority', 'updated', 'components', 'labels']
const TODAY = '2026-10-07'

class Failure extends Error {
  exit: number
  code: string
  details: Record<string, unknown>
  constructor(exit: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message)
    this.exit = exit
    this.code = code
    this.details = details
  }
}

const invalid = (message: string) => new Failure(2, 'invalid_input', message)
function jiraError(method: string, path: string, status: number, body: object) {
  const hint = { 401: ' (authentication failed; replace the token with auth login, or migrate legacy credentials with config migrate)', 403: ' (permission denied for this operation)', 404: ' (not found; check the key or ID)' }[status] ?? ''
  return new Failure(1, 'jira_error', `Error: ${method} ${path} -> ${status}: ${JSON.stringify(body)}${hint}`, { status })
}

/** Python's repr() for the dict results that jira prints as `✓ {...}`. */
export function pyRepr(value: unknown): string {
  if (value === null || value === undefined) return 'None'
  if (value === true) return 'True'
  if (value === false) return 'False'
  if (typeof value === 'number') return String(value)
  if (typeof value === 'string') return value.includes("'") && !value.includes('"') ? `"${value}"` : `'${value.replaceAll("'", "\\'")}'`
  if (Array.isArray(value)) return `[${value.map(pyRepr).join(', ')}]`
  return `{${Object.entries(value as object).map(([k, v]) => `${pyRepr(k)}: ${pyRepr(v)}`).join(', ')}}`
}

function csvCell(value: string) {
  return /[",\n\r]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value
}

// json.dumps default separators, used when CSV flattens list fields.
const pyJson = (value: unknown) => JSON.stringify(value).replaceAll('":', '": ').replaceAll(',"', ', "').replaceAll(',{', ', {')

export class Session {
  issues = initialIssues()
  sprints = initialSprints()
  private nextComment = 10200

  reset() {
    this.issues = initialIssues()
    this.sprints = initialSprints()
    this.nextComment = 10200
  }

  run(line: string): Result {
    const tokens = tokenize(line.trim())
    if ('error' in tokens) return { blocks: [{ kind: 'note', text: `The sandbox could not read that line: ${tokens.error} quote.` }], exit: null }
    if (!tokens.length) return { blocks: [], exit: null }
    if (tokens[0] !== 'jira') return { blocks: [{ kind: 'note', text: `This sandbox runs jira commands only. Try jira --help.` }], exit: null }
    if (tokens.some(t => ['|', '>', '>>', '&&', ';'].includes(t)))
      return { blocks: [{ kind: 'note', text: 'Pipes and redirects only work in your own shell. Run the jira part here, or copy the whole line into your terminal.' }], exit: null }

    const parsed = parse(tokens.slice(1))
    if (parsed.kind === 'error') return { blocks: [{ kind: 'text', stream: 'stderr', text: parsed.text }], exit: 2 }
    if (parsed.kind === 'help') return out(parsed.text)
    if (parsed.kind === 'version') return out(`jira ${root.version}`)
    if (parsed.kind === 'group') {
      if (parsed.path.length) return out(help(['jira', ...parsed.path].join(' '), parsed.node))
      return out(`jira: site=${site}  project=${profile.project}\nTry: jira --help · jira config init · jira issue list --open`)
    }
    if (parsed.legacy) {
      const modern = parsed.legacy === 'me' ? 'jira user me' : 'the grouped command shown in jira --help'
      return { blocks: [{ kind: 'note', text: `jira ${parsed.legacy} is a legacy name that keeps working through v2.x. The sandbox only runs current names; use ${modern}.` }], exit: null }
    }

    const command = parsed.path.join(' ')
    const { opts, args } = parsed
    try {
      if (opts.json && opts.csv) throw invalid('Choose --json or --csv, not both.')
      if (opts.csv && !LIST_COMMANDS.has(command)) throw invalid('--csv is supported only for list commands.')
      if (opts.profile && opts.profile !== profile.name) throw invalid(`Unknown profile: ${opts.profile}. Run profile list or auth login.`)
      return this.dispatch(command, opts, args)
    } catch (error) {
      if (!(error instanceof Failure)) throw error
      // jira api keeps stdout for response bodies, so its errors are always JSON on stderr.
      if (command === 'api') return { blocks: [{ kind: 'text', stream: 'stderr', text: JSON.stringify({ error: { code: error.code, message: error.message, ...error.details } }, null, 2) }], exit: error.exit }
      if (opts.json) return { blocks: [{ kind: 'text', stream: 'stdout', text: JSON.stringify({ error: { code: error.code, message: error.message, ...error.details } }, null, 2) }], exit: error.exit }
      return { blocks: [{ kind: 'text', stream: 'stderr', text: error.message }], exit: error.exit }
    }
  }

  private dispatch(command: string, opts: Values, args: Values): Result {
    switch (command) {
      case 'help': return this.help(args.path as string[] | undefined)
      case 'user me': return opts.json ? json({ accountId: me.accountId, accountType: 'atlassian', emailAddress: me.emailAddress, displayName: me.displayName, active: true, timeZone: 'UTC' }) : out(`✓ ${me.displayName} (${me.emailAddress})`)
      case 'issue list': return this.list(opts)
      case 'issue view': return this.view(args.key as string, opts)
      case 'issue transitions': return this.transitions(args.key as string, opts)
      case 'issue transition': return this.transition(args.key as string, opts)
      case 'issue assign': return this.assign(args.key as string, opts.user as string, opts)
      case 'issue unassign': return this.assign(args.key as string, null, opts)
      case 'sprint list': return this.sprintList(opts)
      case 'sprint create': return this.sprintCreate(opts)
      case 'sprint add-issues': return this.sprintAdd(args.sprint_id as string, args.keys as string[], opts)
      case 'issue comment add': return this.comment(args.key as string, opts)
      case 'issue create': return this.create(opts)
      case 'issue edit': return this.edit(args.key as string, opts)
      case 'api': return this.api(args.path as string, args.spec_action as string | undefined, opts)
      case 'desk list': return this.table(opts, 'Service desks (2 fetched)', ['id', 'key', 'name'], desks.map(d => ({ id: d.id, key: d.projectKey, name: d.projectName })))
      case 'request list': return this.table(opts, `Requests (${requests.length} fetched)`, ['key', 'status', 'summary', 'reporter', 'created', 'desk'], requests.map(({ key, status, summary, reporter, created, desk }) => ({ key, status, summary, reporter, created, desk })))
      case 'request view': return this.requestView(args.key as string, opts)
      case 'project list': return this.table(opts, 'Projects', ['key', 'name'], projects)
      case 'board list': return opts.json
        ? json({ maxResults: 50, startAt: 0, isLast: true, values: boards.map(b => ({ id: b.id, name: b.name, type: b.type })), fetched: boards.length })
        : table('Boards', ['ID', 'Type', 'Name'], boards.map(b => [{ text: String(b.id) }, { text: b.type }, { text: b.name }]))
    }
    const node = command.split(' ').reduce<Node | undefined>((n, name) => n && child(n, name), root)
    return { blocks: [{ kind: 'note', text: `jira ${command} parsed correctly. The sandbox has no sample data for it, so nothing ran. In your terminal it will ${node?.help || 'run against your Jira site'}.` }], exit: null }
  }

  // Mirrors the checks and messages in jsup/api.py; responses come from the sample site.
  private api(path: string, action: string | undefined, opts: Values): Result {
    const method = String(opts.method ?? 'GET').toUpperCase()
    if (path === 'spec') {
      if (action === 'refresh' || action === 'status' || !action)
        return { blocks: [{ kind: 'note', text: 'The sandbox has no spec cache. In your terminal, jira api spec refresh downloads the official OpenAPI documents and spec status shows their version and age.' }], exit: null }
      throw invalid(`Unknown spec action '${action}'; use jira api spec refresh or jira api spec status.`)
    }
    if (action) throw invalid(`Unexpected argument '${action}'; pass query values with --query KEY=VALUE.`)
    if (!path.startsWith('/')) throw invalid('PATH must be a Jira REST path such as /rest/api/3/myself. Use jira api spec refresh or jira api spec status for discovery.')
    if (/[^\x21-\x7e]/.test(path)) throw invalid('PATH must be printable ASCII without spaces; percent-encode other characters.')
    if (/[?#]/.test(path)) throw invalid('PATH must not contain a query or fragment; pass query values with --query KEY=VALUE.')
    if (path.includes('\\') || path.includes('//')) throw invalid('PATH must not contain backslashes or empty segments.')
    if (!path.startsWith('/rest/')) throw invalid('PATH must start with /rest/, for example /rest/api/3/myself or /rest/agile/1.0/board.')
    if (path.replace(/%2e/gi, '.').split('/').some(s => s === '.' || s === '..')) throw invalid('PATH must not contain . or .. segments.')
    const body = ['data', 'raw-data', 'form'].find(k => opts[k] !== undefined && !(Array.isArray(opts[k]) && !(opts[k] as string[]).length))
    if (body && ['GET', 'HEAD', 'OPTIONS'].includes(method)) throw invalid(`--${body} needs an explicit method that accepts a body, such as -X POST.`)
    if (opts.spec) return this.apiSpec(path, method)
    const issue = path.match(/^\/rest\/api\/3\/issue\/([^/]+)$/)
    if (method === 'GET' && path === '/rest/api/3/myself')
      return json({ accountId: me.accountId, emailAddress: me.emailAddress, displayName: me.displayName, active: true, timeZone: 'UTC' })
    if (method === 'GET' && issue) {
      const found = this.issues.find(i => i.key === issue[1].toUpperCase())
      if (!found) throw new Failure(1, 'jira_error', `GET ${path} -> 404`, { status: 404, method, path,
        body: { errorMessages: ['Issue does not exist or you do not have permission to see it.'], errors: {} } })
      return json(this.issueJson(found))
    }
    const board = path.match(/^\/rest\/agile\/1\.0\/board\/(\d+)\/sprint$/)
    if (method === 'GET' && board) {
      const values = this.sprints.filter(s => String(s.board) === board[1]).map(({ board: id, ...s }) => ({ ...s, originBoardId: id }))
      return json({ maxResults: 50, startAt: 0, isLast: true, values })
    }
    return { blocks: [{ kind: 'note', text: `jira api ${method} ${path} is valid. The sandbox has sample responses only for /rest/api/3/myself, /rest/api/3/issue/KEY and /rest/agile/1.0/board/12/sprint. In your terminal it calls your Jira site with your saved profile.` }], exit: null }
  }

  private apiSpec(path: string, method: string): Result {
    const key = path.match(/^\/rest\/api\/3\/issue\/([^/]+)$/)?.[1]
    if (path === '/rest/api/3/issue' && method === 'POST') return json({
      method, path, template: '/rest/api/3/issue', pathParameters: {}, operationId: 'createIssue', summary: 'Create issue',
      permissions: '*Browse projects* and *Create issues* project permissions for the project in which the issue or subtask is created.',
      scopes: { oauth2: [{ scheme: 'OAuth2', scopes: ['write:jira-work'], state: 'Current' }], connect: 'WRITE' },
      parameters: [{ in: 'query', name: 'updateHistory', schema: { type: 'boolean', default: false } }],
      requestBody: { content: { 'application/json': { schema: { 'x-schema': 'IssueUpdateDetails', type: 'object', properties: { fields: { type: 'object' }, update: { type: 'object' }, transition: { 'x-schema': 'IssueTransition' } } } } } },
      responses: {
        201: { description: 'Returned if the request is successful.' },
        400: { description: 'Returned if the request: * is missing required fields. * contains invalid field values. * contains fields that cannot be set for the issue type. …' },
        401: { description: 'Returned if the authentication credentials are incorrect or missing.' },
        403: { description: 'Returned if the user does not have the necessary permission.' },
        422: { description: 'Returned if a configuration problem prevents the creation of the issue.' },
      },
      note: 'Sample excerpt. The real output includes full schemas and examples from the official document, plus its version and fetch time.',
    })
    if (key && (method === 'GET' || method === 'DELETE')) return json({
      method, path, template: '/rest/api/3/issue/{issueIdOrKey}', pathParameters: { issueIdOrKey: key },
      operationId: method === 'GET' ? 'getIssue' : 'deleteIssue', summary: method === 'GET' ? 'Get issue' : 'Delete issue',
      permissions: `${method === 'GET' ? '*Browse projects* project permission for the project that the issue is in.' : '*Browse projects* and *Delete issues* project permission for the project containing the issue.'} If issue-level security is configured, issue-level security permission to view the issue.`,
      scopes: { oauth2: [{ scheme: 'OAuth2', scopes: [method === 'GET' ? 'read:jira-work' : 'write:jira-work'], state: 'Current' }], connect: method === 'GET' ? 'READ' : 'DELETE' },
      note: 'Sample excerpt. The real output includes every parameter and the full response schema.',
    })
    return { blocks: [{ kind: 'note', text: `The sandbox has sample specs only for POST /rest/api/3/issue and GET or DELETE /rest/api/3/issue/KEY. In your terminal, --spec looks up ${method} ${path} in the cached official OpenAPI documents.` }], exit: null }
  }

  private requestView(key: string, opts: Values): Result {
    const request = requests.find(r => r.key === key.toUpperCase())
    if (!request) throw jiraError('GET', `/rest/servicedeskapi/request/${key}`, 404, { errorMessage: 'Request does not exist or you do not have permission to see it.' })
    if (opts.json) return json({ issueKey: request.key, summary: request.summary, serviceDeskId: request.desk, currentStatus: { status: request.status }, reporter: { displayName: request.reporter } })
    return {
      blocks: [{
        kind: 'panel', title: 'Request', subtitle: `participants: ${request.participants.length}`, heading: [request.key, request.summary],
        lines: [`status=${request.status}  desk=${request.desk}  reporter=${request.reporter}  created=${request.created}`,
          ...(request.participants.length ? [`participants=${request.participants.join(', ')}`] : []),
          `SLA ${request.sla}`, '', 'Description:', request.description],
      }], exit: 0,
    }
  }

  private help(path: string[] = []) {
    let node: Node = root
    for (const part of path) {
      const next = child(node, part)
      if (!next) return { blocks: [{ kind: 'text' as const, stream: 'stderr' as const, text: `${usage('jira', root)}\njira: error: unknown help command: ${path.join(' ')}` }], exit: 2 }
      node = next
    }
    return out(help(['jira', ...path].join(' '), node))
  }

  private find(key: string, path: string) {
    const issue = this.issues.find(i => i.key === key.toUpperCase())
    if (!issue) throw jiraError('GET', path, 404, { errorMessages: ['Issue does not exist or you do not have permission to see it.'], errors: {} })
    return issue
  }

  /** Search returns the client's default fields unless --fields names others, as the real search does. */
  private issueJson(issue: Issue, only?: string[]) {
    const status = statuses.find(s => s.name === issue.status)!
    const assignee = users.find(u => u.accountId === issue.assignee)
    const sprint = this.sprints.find(s => s.id === issue.sprint)
    const all: Record<string, unknown> = {
      summary: issue.summary, issuetype: { name: issue.type }, status: { name: status.name, id: status.id, statusCategory: { key: status.category } },
      assignee: assignee ? { accountId: assignee.accountId, displayName: assignee.displayName } : null,
      priority: { name: issue.priority }, updated: `${issue.updated}T09:30:00.000+0000`,
      components: issue.components.map(name => ({ name })), labels: issue.labels,
      customfield_10016: issue.points ?? null,
      customfield_10020: sprint ? [{ id: sprint.id, name: sprint.name, state: sprint.state, boardId: sprint.board }] : null,
      issuelinks: (issue.blockedBy ?? []).map((key, i) => ({ id: String(20000 + i), type: { name: 'Blocks', inward: 'is blocked by', outward: 'blocks' },
        inwardIssue: { key, fields: { summary: this.issues.find(x => x.key === key)?.summary, status: { name: this.issues.find(x => x.key === key)?.status } } } })),
    }
    const names = only ?? DEFAULT_FIELDS
    return {
      id: String(10000 + Number(issue.key.split('-')[1])), self: `${site}/rest/api/3/issue/${10000 + Number(issue.key.split('-')[1])}`, key: issue.key,
      fields: Object.fromEntries(names.filter(n => n in all).map(n => [n, all[n]])),
    }
  }

  private list(opts: Values): Result {
    const status = opts.status as string[] | undefined
    const labels = opts.label as string[] | undefined
    const filters = Boolean(opts.open || opts.project || opts.assignee || status || opts.type || labels || opts.board)
    if (opts.jql) {
      if (filters || opts['order-by'] || opts.order) throw invalid('--jql is a complete query; omit generated filters and ordering flags.')
      return { blocks: [{ kind: 'note', text: 'The sandbox does not evaluate JQL. In your terminal, jira sends this query to Jira exactly as written.' }], exit: null }
    }
    const board = opts.board ? boards.find(b => String(b.id) === opts.board) : undefined
    if (opts.board && !board) throw jiraError('GET', `/rest/agile/1.0/board/${opts.board}/issue`, 404, { errorMessages: ['The requested board cannot be viewed because it either does not exist or you do not have permission to view it.'], errors: {} })
    const project = ((opts.project as string | undefined) ?? (board ? board.project : profile.project)).toUpperCase()
    if (!projects.some(p => p.key === project)) throw jiraError('POST', '/rest/api/3/search/jql', 400, { errorMessages: [`The value '${opts.project}' does not exist for the field 'project'.`], warningMessages: [] })

    const accountId = opts.assignee === 'me' ? me.accountId : typeof opts.assignee === 'string' ? opts.assignee.replace(/^id:/, '') : undefined
    let found = this.issues.filter(i => i.key.startsWith(`${project}-`)
      && (!opts.open || i.status !== 'Done')
      && (!accountId || i.assignee === accountId)
      && (!status || status.some(s => s.toLowerCase() === i.status.toLowerCase()))
      && (!opts.type || String(opts.type).toLowerCase() === i.type.toLowerCase())
      && (!labels || labels.every(l => i.labels.includes(l))))
    const by = (opts['order-by'] as string | undefined) ?? 'updated'
    const sign = opts.order === 'asc' ? 1 : -1
    const rank = (i: Issue) => by === 'priority' ? -PRIORITY.indexOf(i.priority) : by === 'key' ? Number(i.key.split('-')[1]) : i.updated
    found = [...found].sort((a, b) => (rank(a) > rank(b) ? 1 : rank(a) < rank(b) ? -1 : 0) * sign)
    if (!opts.all) found = found.slice(0, Number(opts.limit ?? 50))

    const only = typeof opts.fields === 'string' ? opts.fields.split(',').map(f => f.trim()).filter(Boolean) : undefined
    const data = { issues: found.map(i => this.issueJson(i, only)), isLast: true, fetched: found.length }
    if (opts.json) return json(data)
    const rows = data.issues.map(({ fields, ...rest }) => ({
      ...rest, ...Object.fromEntries(Object.entries(fields).map(([k, v]) =>
        [k, Array.isArray(v) ? pyJson(v) : v && typeof v === 'object' ? (v as Record<string, string>).displayName ?? (v as Record<string, string>).name : v ?? '']))
    } as Record<string, string>))
    const columns = typeof opts.columns === 'string' ? opts.columns.split(',') : undefined
    if (opts.csv) {
      const names = columns ?? [...new Set(rows.flatMap(r => Object.keys(r)))]
      return out([names.join(','), ...rows.map(r => names.map(n => csvCell(String(r[n] ?? ''))).join(','))].join('\n'))
    }
    const title = `${opts.open ? 'Open issues' : 'Issues'} (${found.length} fetched)`
    if (columns) return table(title, columns, rows.map(r => columns.map(c => ({ text: String(r[c] ?? '') }))))
    return table(title, ['Key', 'Status', 'Summary', 'Assignee', 'Updated'], found.map(i => [
      { text: i.key, tone: 'bold' }, { text: i.status, tone: statuses.find(s => s.name === i.status)!.category },
      { text: i.summary }, { text: users.find(u => u.accountId === i.assignee)?.displayName ?? '-' }, { text: i.updated },
    ]))
  }

  private view(key: string, opts: Values): Result {
    const issue = this.find(key, `/rest/api/3/issue/${key}`)
    if (opts.web) return out(`Opening ${site}/browse/${issue.key}`)
    if (opts.json) {
      const data = this.issueJson(issue, [...DEFAULT_FIELDS, 'issuetype', 'customfield_10016', 'customfield_10020', 'issuelinks'])
      return json({ ...data, fields: { ...data.fields, comment: { total: issue.comments } } })
    }
    const assignee = users.find(u => u.accountId === issue.assignee)?.displayName ?? '-'
    return {
      blocks: [{
        kind: 'panel', title: 'Issue', subtitle: `comments: ${issue.comments}`, heading: [issue.key, issue.summary],
        lines: [`status=${issue.status}  type=${issue.type}  priority=${issue.priority}`,
          `assignee=${assignee}  labels=${issue.labels.join(', ') || '-'}  components=${issue.components.join(', ') || '-'}`,
          ...(issue.description ? ['', issue.description] : [])],
      }], exit: 0,
    }
  }

  private available(issue: Issue) {
    return statuses.filter(s => s.name !== issue.status)
  }

  private transitions(key: string, opts: Values): Result {
    const issue = this.find(key, `/rest/api/3/issue/${key}/transitions`)
    const data = { expand: 'transitions', transitions: this.available(issue).map(s => ({ id: s.id, name: s.name, to: { name: s.name } })) }
    return opts.json ? json(data) : out(`✓ ${pyRepr(data)}`)
  }

  private transition(key: string, opts: Values): Result {
    const issue = this.find(key, `/rest/api/3/issue/${key}/transitions`)
    const items = this.available(issue)
    const list = (sep: string) => items.map(s => `${s.name} [id:${s.id}]`).join(sep)
    if (opts.to === undefined) throw invalid(`Pass --to; available values: ${list(', ')}`)
    const raw = String(opts.to).replace(/^id:/, '')
    const exact = items.filter(s => s.id === raw)
    const matches = exact.length ? exact : items.filter(s => s.name.toLowerCase() === raw.toLowerCase())
    if (matches.length !== 1) throw invalid(`--to ${pyRepr(opts.to)} is unavailable or ambiguous; use an explicit ID. Available: ${list(', ')}`)
    issue.status = matches[0].name
    issue.updated = TODAY
    const data = { moved: issue.key, transition_id: matches[0].id, to: matches[0].name }
    return opts.json ? json(data) : out(`Moved ${issue.key} → ${matches[0].name}`)
  }

  private assign(key: string, user: string | null, opts: Values): Result {
    const issue = this.find(key, `/rest/api/3/issue/${key}`)
    let account: string | null = null
    if (user === 'me') account = me.accountId
    else if (user?.startsWith('id:')) account = user.slice(3)
    else if (user) {
      const matches = users.filter(u => [u.displayName.toLowerCase(), u.emailAddress.toLowerCase()].includes(user.toLowerCase()))
      if (matches.length !== 1) throw invalid('User is unavailable or ambiguous; use --user id:<account ID>.')
      account = matches[0].accountId
    }
    issue.assignee = account
    issue.updated = TODAY
    const data = { issue: issue.key, assignee: account }
    return opts.json ? json(data) : out(`✓ ${pyRepr(data)}`)
  }

  /** Mirrors fields.create for the summary, type, priority, assignee and labels the sample metadata offers. */
  private create(opts: Values): Result {
    const project = String(opts.project ?? profile.project).toUpperCase()
    if (!projects.some(p => p.key === project)) throw jiraError('GET', `/rest/api/3/issue/createmeta/${project}/issuetypes`, 404, { errorMessages: [`No project could be found with key '${project}'.`], errors: {} })
    if (opts.template !== undefined || opts['fields-file'] !== undefined || opts['description-file'] !== undefined || opts.editor)
      return { blocks: [{ kind: 'note', text: 'The sandbox creates issues from flags only. In your terminal, templates, --fields-file, --description-file and --editor work too.' }], exit: null }
    const list = issueTypes.map(t => `${t.name} [id:${t.id}]`).join(', ')
    if (opts.type === undefined) throw invalid(`Pass --type; available values: ${list}`)
    const raw = String(opts.type).replace(/^id:/, '')
    const type = issueTypes.find(t => t.id === raw) ?? issueTypes.find(t => t.name.toLowerCase() === raw.toLowerCase())
    if (!type) throw invalid(`--type ${pyRepr(opts.type)} is unavailable or ambiguous; use an explicit ID. Available: ${list}`)
    if (!opts.summary) throw invalid('Required fields missing: Summary (summary). Supply --field FIELD=VALUE or --fields-file.')
    const priority = opts.priority === undefined ? 'Medium' : PRIORITY.find(p => p.toLowerCase() === String(opts.priority).toLowerCase())
    if (!priority) throw invalid('Priority: value is not allowed.')
    const number = Math.max(0, ...this.issues.filter(i => i.key.startsWith(`${project}-`)).map(i => Number(i.key.split('-')[1]))) + 1
    const key = `${project}-${number}`
    this.issues.push({ key, summary: String(opts.summary), status: 'To Do', type: type.name, priority, assignee: (opts.assignee as string | undefined)?.replace(/^id:/, '') ?? null,
      labels: (opts.label as string[] | undefined) ?? [], components: (opts.component as string[] | undefined) ?? [], updated: TODAY, description: String(opts.description ?? ''), comments: 0 })
    const data = { id: String(10000 + number), key, self: `${site}/rest/api/3/issue/${10000 + number}` }
    return opts.json ? json(data) : out(`✓ ${pyRepr(data)}`)
  }

  /** Mirrors maintenance.edit for summary, priority and labels, the fields sample issues can edit. */
  private edit(key: string, opts: Values): Result {
    const issue = this.find(key, `/rest/api/3/issue/${key}/editmeta`)
    const list = (name: string) => (opts[name] as string[] | undefined) ?? []
    const [replace, add, remove] = [list('label'), list('add-label'), list('remove-label')]
    if (replace.length && (add.length || remove.length)) throw invalid('Use either --label replacement or add/remove operations.')
    for (const name of ['due-date', 'parent', 'description', 'component', 'add-component', 'remove-component', 'field'])
      if (opts[name] !== undefined && !(Array.isArray(opts[name]) && !(opts[name] as string[]).length))
        return { blocks: [{ kind: 'note', text: `The sandbox edits summary, priority and labels only. In your terminal, --${name} is checked against the issue’s edit metadata.` }], exit: null }
    const fields: string[] = []
    let priority: string | undefined
    if (opts.priority !== undefined) {
      priority = PRIORITY.find(p => p.toLowerCase() === String(opts.priority).toLowerCase())
      if (!priority) throw invalid('Priority: value is not allowed.')
      fields.push('priority')
    }
    if (opts.summary !== undefined) fields.push('summary')
    if (replace.length) fields.push('labels')
    const operations = add.length || remove.length ? ['labels'] : []
    if (!fields.length && !operations.length) throw invalid('No changes supplied. Use issue edit --help.')
    if (priority) issue.priority = priority
    if (opts.summary !== undefined) issue.summary = String(opts.summary)
    if (replace.length) issue.labels = replace
    issue.labels = [...issue.labels.filter(l => !remove.includes(l)), ...add.filter(l => !issue.labels.includes(l))]
    issue.updated = TODAY
    const data = { updated: issue.key, fields: fields.sort(), operations }
    return opts.json ? json(data) : out(`✓ ${pyRepr(data)}`)
  }

  private sprintCreate(opts: Values): Result {
    const boardId = Number(opts.board ?? profile.board)
    if (!boards.some(b => b.id === boardId)) throw jiraError('POST', '/rest/agile/1.0/sprint', 400, { errorMessages: [], errors: { originBoardId: 'Board does not exist or you do not have permission to see it.' } })
    const sprint = { id: Math.max(...this.sprints.map(s => s.id)) + 1, state: 'future', name: String(opts.name), goal: String(opts.goal ?? ''), board: boardId }
    this.sprints.push(sprint)
    // Jira answers with the new sprint; an empty goal is sent as null and omitted.
    const data = { id: sprint.id, self: `${site}/rest/agile/1.0/sprint/${sprint.id}`, state: sprint.state, name: sprint.name, originBoardId: boardId, ...(sprint.goal ? { goal: sprint.goal } : {}) }
    return opts.json ? json(data) : out(`✓ ${pyRepr(data)}`)
  }

  private sprintAdd(id: string, keys: string[], opts: Values): Result {
    const path = `/rest/agile/1.0/sprint/${id}/issue`
    const sprint = this.sprints.find(s => s.id === Number(id))
    if (!sprint) throw jiraError('POST', path, 404, { errorMessages: ['Sprint does not exist or you do not have permission to view it.'], errors: {} })
    const issues = keys.map(key => this.find(key, path))
    for (const issue of issues) { issue.sprint = sprint.id; issue.updated = TODAY }
    // Jira answers 204 No Content, which the client returns as an empty dict.
    return opts.json ? json({}) : out('✓ {}')
  }

  private comment(key: string, opts: Values): Result {
    const issue = this.find(key, `/rest/api/3/issue/${key}/comment`)
    if (opts['message-file'] !== undefined) return { blocks: [{ kind: 'note', text: 'The sandbox cannot read local files. Use --message here; in your terminal --message-file reads the comment from a file.' }], exit: null }
    if (opts.message === undefined) throw invalid('Supply --message, --message-file, or interactive --editor.')
    const text = String(opts.message)
    if (!text.trim()) throw invalid('Comment body cannot be empty.')
    issue.comments++
    issue.updated = TODAY
    const id = String(this.nextComment++)
    const stamp = `${TODAY}T09:30:00.000+0000`
    const data = { self: `${site}/rest/api/3/issue/${10000 + Number(issue.key.split('-')[1])}/comment/${id}`, id,
      author: { accountId: me.accountId, displayName: me.displayName, active: true },
      body: { type: 'doc', version: 1, content: [{ type: 'paragraph', content: [{ type: 'text', text }] }] },
      created: stamp, updated: stamp }
    return opts.json ? json(data) : out(`✓ ${pyRepr(data)}`)
  }

  private sprintList(opts: Values): Result {
    const boardId = Number(opts.board ?? profile.board)
    if (!boards.some(b => b.id === boardId)) throw jiraError('GET', `/rest/agile/1.0/board/${boardId}/sprint`, 404, { errorMessages: ['The requested board cannot be viewed because it either does not exist or you do not have permission to view it.'], errors: {} })
    const states = String(opts.state ?? 'active,future').split(',')
    const values = this.sprints.filter(s => s.board === boardId && states.includes(s.state)).slice(0, Number(opts.limit ?? 50))
    if (opts.json) return json({ maxResults: 50, startAt: 0, isLast: true, values: values.map(({ board, ...s }) => ({ ...s, originBoardId: board })), fetched: values.length })
    if (opts.csv) return out(['id,state,name,goal,originBoardId', ...values.map(s => [s.id, s.state, s.name, s.goal, s.board].map(v => csvCell(String(v))).join(','))].join('\n'))
    return table('Sprints', ['ID', 'State', 'Name', 'Goal'], values.map(s => [{ text: String(s.id) }, { text: s.state, tone: s.state as Tone }, { text: s.name }, { text: s.goal }]))
  }

  private table(opts: Values, title: string, columns: string[], rows: Record<string, string>[]): Result {
    if (opts.json) return json(rows)
    if (opts.csv) return out([columns.join(','), ...rows.map(r => columns.map(c => csvCell(r[c])).join(','))].join('\n'))
    return table(title, columns, rows.map(r => columns.map(c => ({ text: r[c] }))))
  }
}

function out(text: string): Result {
  return { blocks: [{ kind: 'text', stream: 'stdout', text }], exit: 0 }
}

function json(data: unknown): Result {
  return out(JSON.stringify(data, null, 2))
}

function table(title: string, columns: string[], rows: Cell[][]): Result {
  return { blocks: [{ kind: 'table', title, columns, rows }], exit: 0 }
}
