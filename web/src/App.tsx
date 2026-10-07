import { useMemo, useRef, useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Sandbox, suggestions, type SandboxHandle } from '@/components/Sandbox'
import { leaves, root, type Node } from '@/sandbox/tree'
import './App.css'

const repo = 'https://github.com/User17745/jira-cli-toolkit'
const docs = `${repo}/blob/main/README.md`
const latest = `${repo}/releases/latest`
const raw = 'https://raw.githubusercontent.com/User17745/jira-cli-toolkit/main/scripts'
const notices = `${import.meta.env.BASE_URL}third-party-notices.txt`
type OS = 'macos' | 'linux' | 'windows'
const platforms: Record<OS, { name: string; shell: string; command: string; note: string }> = {
  macos: { name: 'macOS', shell: 'Terminal', command: `curl -fsSL ${raw}/install.sh | bash\nexport PATH="$HOME/.local/bin:$PATH"`, note: 'macOS 15 or later, on Apple Silicon or Intel.' },
  linux: { name: 'Linux', shell: 'Terminal', command: `curl -fsSL ${raw}/install.sh | bash\nexport PATH="$HOME/.local/bin:$PATH"`, note: 'x86_64 with glibc 2.39 or later, such as Ubuntu 24.04.' },
  windows: { name: 'Windows', shell: 'PowerShell', command: `irm ${raw}/install.ps1 | iex`, note: 'Windows 10 or later on x86_64, with PowerShell 5.1 or later.' },
}

const exitCodes: { code: number; meaning: string; detail: string; example?: string }[] = [
  { code: 0, meaning: 'Success', detail: 'Data is on stdout.', example: 'jira issue list --open --json --limit 1' },
  { code: 1, meaning: 'Jira or network error', detail: 'Jira refused the request, or could not be reached.', example: 'jira issue view ENG-99' },
  { code: 2, meaning: 'Invalid input', detail: 'Bad arguments, missing values or configuration.', example: 'jira issue list --json --csv' },
  { code: 130, meaning: 'Interrupted', detail: 'Ctrl+C stopped the command, or input ended at a prompt.' },
]

function CopyButton({ text, label }: { text: string; label: string }) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle')
  async function copy() {
    try { await navigator.clipboard.writeText(text); setState('copied') }
    catch { setState('failed') }
    window.setTimeout(() => setState('idle'), 3500)
  }
  return <div className="copy-control">
    <button type="button" className="copy-button" onClick={copy} aria-label={label}>
      {state === 'copied' ? <Check size={15} aria-hidden="true" /> : <Copy size={15} aria-hidden="true" />}
      <span>{state === 'copied' ? 'Copied' : 'Copy'}</span>
    </button>
    <span className="copy-status" role="status">{state === 'failed' ? 'Select the command and copy it manually.' : state === 'copied' ? 'Command copied to clipboard.' : ''}</span>
  </div>
}

function Install() {
  const [os, setOS] = useState<OS>(() => /Win/i.test(navigator.userAgent) ? 'windows' : /Linux/i.test(navigator.userAgent) ? 'linux' : 'macos')
  return <section className="install" id="get-started" aria-labelledby="install-title">
    <h2 id="install-title">Install</h2>
    <Tabs value={os} onValueChange={value => setOS(value as OS)} className="install-tabs">
      <TabsList activateOnFocus variant="line" className="install-list" aria-label="Installation operating system">
        {(Object.keys(platforms) as OS[]).map(key => <TabsTrigger key={key} value={key}>{platforms[key].name}</TabsTrigger>)}
      </TabsList>
      {(Object.keys(platforms) as OS[]).map(key => <TabsContent value={key} key={key}>
        <div className="install-code">
          <div className="install-code-top"><span>{platforms[key].shell}</span><CopyButton text={platforms[key].command} label={`Copy ${platforms[key].name} installation command`} /></div>
          <pre tabIndex={0}><code>{platforms[key].command}</code></pre>
        </div>
        <p className="install-note">{platforms[key].note} The installer verifies release checksums first.</p>
      </TabsContent>)}
    </Tabs>
    <p className="install-links"><a href={latest}>Prefer a manual install?</a> <a href={`${repo}/blob/main/docs/migration/upgrade-to-v2.md`}>Upgrading from jsup?</a></p>
  </section>
}

function groupsOf(): { name: string; items: { path: string[]; node: Node }[] }[] {
  const general = (root.commands ?? []).filter(c => !c.commands).map(node => ({ path: [node.name], node }))
  const grouped = (root.commands ?? []).filter(c => c.commands).map(group => ({ name: group.name, items: leaves(group, [group.name]) }))
  return [...grouped.sort((a, b) => b.items.length - a.items.length), { name: 'more', items: general }]
}

function Reference({ onRun }: { onRun: (command: string) => void }) {
  const [query, setQuery] = useState('')
  const groups = useMemo(groupsOf, [])
  const total = groups.reduce((n, g) => n + g.items.length, 0)
  const q = query.trim().toLowerCase()
  const shown = groups.map(g => ({ ...g, items: g.items.filter(i => !q || `${i.path.join(' ')} ${i.node.help}`.toLowerCase().includes(q)) })).filter(g => g.items.length)
  const count = shown.reduce((n, g) => n + g.items.length, 0)
  return <section className="reference" id="commands" aria-labelledby="commands-title">
    <div className="section-head">
      <h2 id="commands-title">Every command, read from the parser</h2>
      <p>This list is generated from the argument parser in jira {root.version}, so it can’t drift from the tool. Select a command to open its real help in the sandbox.</p>
    </div>
    <div className="reference-filter">
      <label htmlFor="command-filter">Filter commands</label>
      <input id="command-filter" type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="sprint, comment, attach…" autoComplete="off" spellCheck={false} />
      <p role="status">{count === total ? `${total} commands` : `${count} of ${total} commands`}</p>
    </div>
    {shown.length ? <div className="reference-groups">
      {shown.map(group => <div className="reference-group" key={group.name}>
        <h3>{group.name === 'more' ? 'Setup and maintenance' : `jira ${group.name}`}</h3>
        <ul>{group.items.map(({ path, node }) => <li key={path.join(' ')}>
          <button type="button" onClick={() => onRun(`jira help ${path.join(' ')}`)}>
            <code>{path.join(' ')}</code><span>{node.help}</span>
          </button>
        </li>)}</ul>
      </div>)}
    </div> : <p className="reference-empty">No command matches “{query}”. Try a noun such as issue, sprint or board.</p>}
  </section>
}

function App() {
  const sandbox = useRef<SandboxHandle>(null)
  const run = (command: string) => sandbox.current?.run(command)
  return <>
    <a className="skip-link" href="#get-started">Skip to installation</a>
    <header className="site-header">
      <a className="brand" href="#" aria-label="CLI Toolkit for Jira home"><span className="brand-name">CLI Toolkit</span> <span className="brand-for">for Jira</span></a>
      <nav aria-label="Main navigation">
        <a className="nav-optional" href="#scripting">Scripting</a>
        <a className="nav-optional" href="#commands">Commands</a>
        <a href={docs}>Docs</a>
        <a href={repo}>GitHub</a>
        <a className="nav-install" href="#get-started">Install the CLI</a>
      </nav>
    </header>
    <main>
      <section className="hero" aria-labelledby="hero-title">
        <h1 id="hero-title"><span className="hero-prompt" aria-hidden="true">$ </span>jira issue list --open</h1>
        <div className="hero-copy">
          <p className="hero-lead">An independent command-line tool for Jira Cloud. List, view, move and assign issues, plan sprints, and script all of it with JSON, CSV and exit codes that mean one thing each.</p>
          <p className="hero-independence">Independently maintained. Not affiliated with Atlassian.</p>
          <p className="hero-proof">Runs within your Jira permissions, using your existing API token.</p>
          <Install />
        </div>
        <div className="hero-sandbox">
          <Sandbox ref={sandbox} />
          <div className="try">
            <p id="try-title">Try</p>
            <ul aria-labelledby="try-title">{suggestions.map(s => <li key={s}><button type="button" onClick={() => run(s)}><code>{s}</code></button></li>)}</ul>
          </div>
        </div>
      </section>

      <section className="scripting" id="scripting" aria-labelledby="scripting-title">
        <div className="section-head">
          <h2 id="scripting-title">Predictable enough to script</h2>
          <p>Data goes to stdout. Messages and prompts go to stderr. Add <code>--json</code> and failures become JSON on stdout too, so a script never has to parse prose.</p>
        </div>
        <div className="scripting-grid">
          <table className="exit-table">
            <caption>Exit codes</caption>
            <thead><tr><th scope="col">Code</th><th scope="col">Meaning</th></tr></thead>
            <tbody>{exitCodes.map(row => <tr key={row.code}>
              <td><code>{row.code}</code></td>
              <td><p><strong>{row.meaning}.</strong> {row.detail}</p>{row.example
                ? <button type="button" className="run-button" onClick={() => run(row.example!)} aria-label={`Run ${row.example} in the sandbox`}>Run <code>{row.example}</code></button>
                : <p className="run-hint">Press <kbd>Ctrl</kbd>+<kbd>C</kbd> in the sandbox to see it.</p>}</td>
            </tr>)}</tbody>
          </table>
          <div className="error-shape">
            <p className="error-shape-title">Every error has one shape with <code>--json</code></p>
            <pre tabIndex={0}><code>{`$ jira issue view ENG-99 --json
{
  "error": {
    "code": "jira_error",
    "message": "Error: GET /rest/api/3/issue/ENG-99 -> 404: …",
    "status": 404
  }
}`}</code></pre>
            <ul className="rules">
              <li><code>--no-input</code>, or any input that isn’t a terminal, never prompts. Missing values fail with exit 2.</li>
              <li>Global flags such as <code>--project</code> and <code>--json</code> work before or after the command.</li>
              <li>Deletes ask for confirmation, or need <code>--yes</code> when nothing can prompt.</li>
              <li>Tokens stay in your OS credential store and are redacted from error output.</li>
            </ul>
          </div>
        </div>
      </section>

      <Reference onRun={run} />

      <section className="setup" aria-labelledby="setup-title">
        <div className="section-head">
          <h2 id="setup-title">From install to your first list</h2>
        </div>
        <ol className="steps">
          <li><p><a href="#get-started">Choose your system</a> and run its install command. It puts <code>jira</code> on your PATH.</p></li>
          <li><p>Sign in with an API token. Guided login links to token creation, explains scopes, and stores the token in your OS credential store by default. For headless use, choose environment authentication or explicit POSIX plaintext file storage.</p><code>jira auth login --profile work</code></li>
          <li><p>Pick a default project, then list what’s open.</p><code>jira context use --project ENG</code><code>jira issue list --open</code></li>
        </ol>
      </section>

      <section className="questions" aria-labelledby="questions-title">
        <div className="section-head">
          <h2 id="questions-title">Before you install</h2>
          <p>What it supports today, and what it doesn’t yet.</p>
        </div>
        <Accordion className="faq">
          <AccordionItem value="independent"><AccordionTrigger>Is this an official Atlassian tool?</AccordionTrigger><AccordionContent>No. CLI Toolkit for Jira is independently maintained by <a href="https://github.com/User17745">User17745</a> and is not affiliated with, endorsed by, or sponsored by Atlassian. The <code>jira</code> command runs this toolkit and connects to your Jira Cloud account.</AccordionContent></AccordionItem>
          <AccordionItem value="auth"><AccordionTrigger>Do I need a new Jira account?</AccordionTrigger><AccordionContent>No. Use your existing Jira Cloud site, email, and API token. The CLI uses your account’s Jira permissions. Guided login links to token creation and explains scopes; tokens cannot refresh automatically.</AccordionContent></AccordionItem>
          <AccordionItem value="support"><AccordionTrigger>Does it support every Jira edition?</AccordionTrigger><AccordionContent>The current release supports standard Jira Cloud issue workflows, plus Software boards and sprints where permissions allow. Data Center and Service Management customer-request APIs are future work.</AccordionContent></AccordionItem>
          <AccordionItem value="api"><AccordionTrigger>Can I call any Jira API endpoint?</AccordionTrigger><AccordionContent>Not yet. Generic API requests with <code>jira api</code> and <code>--spec</code> discovery are <a href={`${repo}/blob/main/docs/sprints/v2.5-api/roadmap.md`}>planned for v2.5</a>. Today’s commands are the ones listed above.</AccordionContent></AccordionItem>
          <AccordionItem value="platform"><AccordionTrigger>Which systems can run it?</AccordionTrigger><AccordionContent>Native releases support macOS 15+ on Apple Silicon and Intel, Linux x86_64 with glibc 2.39+, and Windows 10+ x86_64. For other compatible systems, install the verified Python wheel with Python 3.10 or later. <a href={`${repo}/blob/main/docs/migration/upgrade-to-v2.md`}>See installation options.</a></AccordionContent></AccordionItem>
          <AccordionItem value="upgrade"><AccordionTrigger>Already using jsup or jira-cli-toolkit?</AccordionTrigger><AccordionContent>Your configuration and credential references stay the same. Upgrade through the manager that owns your installation. Existing command names still work in v2.x and show a migration notice. <a href={`${repo}/blob/main/docs/migration/legacy-commands.md`}>Use the migration guide.</a></AccordionContent></AccordionItem>
        </Accordion>
      </section>
    </main>
    <footer className="site-footer">
      <div className="footer-row">
        <a className="brand" href="#"><span className="brand-name">CLI Toolkit</span> <span className="brand-for">for Jira</span></a>
        <nav aria-label="Project links"><a href={repo}>Source</a><a href={`${repo}/blob/main/LICENSE`}>License</a><a href={latest}>Releases</a><a href={`${repo}/issues`}>Report an issue</a><a href={notices}>Third-party notices</a></nav>
      </div>
      <section className="independent-notice" aria-labelledby="independence-title">
        <h2 id="independence-title">Independent project and intellectual property notice</h2>
        <p>CLI Toolkit for Jira is independently developed and maintained. It is not affiliated with, sponsored by, endorsed by, or otherwise associated with Atlassian or any of its affiliated business entities. It is not an official Jira product.</p>
        <p>References to Jira and Atlassian, including the <code>jira</code> command name, identify the external service and describe compatibility and usage. They do not claim ownership of those names or imply an official relationship. Jira and Atlassian are trademarks of Atlassian.</p>
        <p>No infringement of third-party trademarks, copyrights, patents, or other intellectual property rights is intended. This statement does not establish that a particular use is non-infringing or replace any permission that may be required.</p>
        <p className="project-license">Copyright © 2026 Abhishek Aggarwal. Original project code is licensed under <a href={`${repo}/blob/main/LICENSE`}>GNU AGPL v3 only (AGPL-3.0-only)</a>. You may redistribute and modify it under that license. Provided without warranty, including merchantability or fitness for a particular purpose. <a href={`${repo}/blob/main/NOTICE`}>Project notice</a>. <a href={notices}>Third-party licenses</a>. Third-party components and assets retain their applicable license terms. The project license does not grant rights to third-party trademarks.</p>
      </section>
    </footer>
  </>
}
export default App
