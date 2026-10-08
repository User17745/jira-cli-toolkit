import { Fragment, useMemo, useRef, useState } from 'react'
import { Check, ChevronRight, Copy, CornerDownLeft, Search } from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Kbd } from '@/components/ui/kbd'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Terminal, type TerminalHandle } from '@/components/Terminal'
import { ThemeToggle } from '@/components/ThemeToggle'
import { AsciiField } from '@/components/AsciiField'
import { leaves, root, type Node } from '@/sandbox/tree'
import { cn } from 'cn'
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

const examples = [
  { command: 'jira issue list --open', does: 'List open issues in your default project' },
  { command: 'jira issue view ENG-43', does: 'Show one issue in detail' },
  { command: "jira issue transition ENG-43 --to 'In Progress'", does: 'Move an issue through its workflow' },
  { command: 'jira issue assign ENG-44 --user me', does: 'Assign an issue to yourself' },
  { command: 'jira issue list --open --json --limit 1', does: 'Get JSON for a script' },
  { command: 'jira issue list --open --csv --columns key,status', does: 'Export CSV with the columns you choose' },
  { command: 'jira sprint list', does: 'See the active and upcoming sprints' },
  { command: 'jira help issue list', does: 'Read the real help for any command' },
]

const exitCodes: { code: number; meaning: string; detail: string; example?: string; why?: string }[] = [
  { code: 0, meaning: 'Success', detail: 'Data is on stdout.', example: 'jira issue list --open --json --limit 1', why: 'returns one open issue as JSON' },
  { code: 1, meaning: 'Jira or network error', detail: 'Jira refused the request, or couldn’t be reached.', example: 'jira issue view ENG-99', why: 'asks for an issue that doesn’t exist, so Jira answers 404' },
  { code: 2, meaning: 'Invalid input', detail: 'Bad arguments, missing values or configuration.', example: 'jira issue list --json --csv', why: 'combines two output formats that can’t be used together' },
  { code: 130, meaning: 'Interrupted', detail: 'Ctrl+C stopped the command, or input ended at a prompt.' },
]

function CopyButton({ text, label }: { text: string; label: string }) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle')
  async function copy() {
    try { await navigator.clipboard.writeText(text); setState('copied') }
    catch { setState('failed') }
    window.setTimeout(() => setState('idle'), 3500)
  }
  return <div className="absolute top-1.5 right-1.5">
    <button type="button" onClick={copy} aria-label={label} title={state === 'copied' ? 'Copied' : 'Copy'}
      className="grid size-8 place-items-center rounded-md text-[#a1a1a1] transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-2 focus-visible:outline-[#22d3ee]">
      {state === 'copied' ? <Check className="size-4 text-[#4ade80]" aria-hidden="true" /> : <Copy className="size-4" aria-hidden="true" />}
    </button>
    <span className="copy-status" role="status">{state === 'failed' ? 'Select the command and copy it manually.' : state === 'copied' ? 'Command copied to clipboard.' : ''}</span>
  </div>
}

function Install() {
  const [os, setOS] = useState<OS>(() => /Win/i.test(navigator.userAgent) ? 'windows' : /Linux/i.test(navigator.userAgent) ? 'linux' : 'macos')
  return <section id="get-started" aria-labelledby="install-title" className="rounded-xl border bg-card p-4 shadow-xs sm:p-5">
    <Tabs value={os} onValueChange={value => setOS(value as OS)} className="gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="install-title" className="text-sm font-medium">Install</h2>
        <TabsList activateOnFocus aria-label="Installation operating system">
          {(Object.keys(platforms) as OS[]).map(key => <TabsTrigger key={key} value={key} className="px-3">{platforms[key].name}</TabsTrigger>)}
        </TabsList>
      </div>
      {(Object.keys(platforms) as OS[]).map(key => <TabsContent value={key} key={key}>
        {/* Each line gets a prompt drawn by CSS, so the copied and displayed text stay identical. */}
        <div className="install-code relative rounded-lg border border-[#262626] bg-[#0a0a0a] text-[#ededed]">
          <pre tabIndex={0} data-prompt={platforms[key].shell === 'PowerShell' ? 'PS>' : '$'} aria-label={`${platforms[key].shell} command`}
            className="install-pre mr-10 overflow-x-auto py-3 pr-4 pl-3.5 font-mono text-[13px] leading-6 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-[#22d3ee]"><code>{platforms[key].command.split('\n').map((line, i) => <Fragment key={i}>{i > 0 && '\n'}<span className="cmd-line">{line}</span></Fragment>)}</code></pre>
          <CopyButton text={platforms[key].command} label={`Copy ${platforms[key].name} installation command`} />
        </div>
        <p className="mt-2.5 text-[13px] text-muted-foreground">{platforms[key].note} The installer verifies release checksums first.</p>
      </TabsContent>)}
    </Tabs>
    <p className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm">
      <a className="link" href={latest}>Prefer a manual install?</a>
      <a className="link" href={`${repo}/blob/main/docs/migration/upgrade-to-v2.md`}>Upgrading from jsup?</a>
    </p>
  </section>
}

function BrandMark() {
  return <svg viewBox="0 0 64 64" className="size-6" aria-hidden="true">
    <rect width="64" height="64" rx="15" fill="currentColor" />
    <path d="m17 20 12 12-12 12" fill="none" stroke="var(--background)" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
    <rect x="34" y="19" width="13" height="26" rx="2" fill="#4ade80" />
  </svg>
}

function GitHubMark({ className }: { className?: string }) {
  // GitHub's mark-github octicon (Primer Octicons, MIT).
  return <svg viewBox="0 0 16 16" className={className} fill="currentColor" aria-hidden="true"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z" /></svg>
}

function SectionHead({ id, title, children }: { id: string; title: string; children?: React.ReactNode }) {
  return <div className="mb-6 max-w-2xl space-y-2">
    <h2 id={id} className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h2>
    {children && <p className="text-muted-foreground">{children}</p>}
  </div>
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
  return <section className="section" id="commands" aria-labelledby="commands-title">
    <SectionHead id="commands-title" title="Every command, read from the parser">
      This list is generated from the argument parser in jira {root.version}, so it can’t drift from the tool. Select a command to open its real help in the terminal.
    </SectionHead>
    <div className="reference-filter mb-6 flex flex-wrap items-center gap-3">
      <label htmlFor="command-filter" className="sr-only">Filter commands</label>
      <div className="relative w-full max-w-xs">
        <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <Input id="command-filter" type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Filter commands" autoComplete="off" spellCheck={false} className="h-9 pl-8" />
      </div>
      <p role="status" className="text-sm text-muted-foreground">{count === total ? `${total} commands` : `${count} of ${total} commands`}</p>
    </div>
    {shown.length ? <div className="grid gap-x-8 gap-y-6 sm:grid-cols-2">
      {shown.map(group => <div key={group.name} className="min-w-0">
        <h3 className="mb-1 font-mono text-[13px] font-medium text-muted-foreground">{group.name === 'more' ? 'setup and maintenance' : `jira ${group.name}`}</h3>
        <ul className="divide-y rounded-lg border">{group.items.map(({ path, node }) => <li key={path.join(' ')}>
          <button type="button" onClick={() => onRun(`jira help ${path.join(' ')}`)} className="group flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-muted/60 focus-visible:bg-muted/60 focus-visible:outline-none">
            <span className="min-w-0 flex-1"><code className="block font-mono text-[13px] font-medium">{path.join(' ')}</code><span className="block text-[13px] text-muted-foreground">{node.help}</span></span>
            <ChevronRight className="size-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100" aria-hidden="true" />
          </button>
        </li>)}</ul>
      </div>)}
    </div> : <p className="text-muted-foreground">No command matches “{query}”. Try a noun such as issue, sprint or board.</p>}
  </section>
}

function App() {
  const terminal = useRef<TerminalHandle>(null)
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState<string>()
  const run = (command: string) => { setActive(command); terminal.current?.run(command) }
  return <>
    <a className="skip-link" href="#get-started">Skip to installation</a>
    <AsciiField />
    <header className="sticky top-0 z-30 border-b bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-6 px-4 sm:px-6">
        <a className="flex items-center gap-2 whitespace-nowrap" href="#" aria-label="CLI Toolkit for Jira home">
          <BrandMark />
          <span className="font-semibold tracking-tight">CLI Toolkit</span>
          <span className="text-sm text-muted-foreground">for Jira</span>
        </a>
        <nav aria-label="Main navigation" className="hidden items-center gap-5 text-sm text-muted-foreground md:flex">
          <a className="hover:text-foreground" href="#try">Try it</a>
          <a className="hover:text-foreground" href="#scripting">Scripting</a>
          <a className="hover:text-foreground" href="#commands">Commands</a>
          <a className="hover:text-foreground" href={docs}>Docs</a>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <a className={cn(buttonVariants({ variant: 'ghost', size: 'sm' }), 'hidden sm:inline-flex')} href={repo}><GitHubMark className="size-4" />GitHub</a>
          <ThemeToggle />
          <a className={buttonVariants({ size: 'sm' })} href="#get-started">Install the CLI</a>
        </div>
      </div>
    </header>

    <div className="layout relative z-10 mx-auto grid max-w-[1440px] gap-10 px-4 sm:px-6">
      <div className="min-w-0">
      <main>
        <section className="hero flex flex-col items-start pt-6 pb-12 sm:pt-16" aria-labelledby="hero-title">
          <h1 id="hero-title" className="max-w-[16ch] text-4xl font-semibold tracking-tighter text-balance sm:text-5xl xl:text-6xl">Jira Cloud, from your terminal.</h1>
          <p className="order-4 mt-6 max-w-xl text-base text-pretty text-muted-foreground sm:order-none sm:mt-5 sm:text-lg">An independent command-line tool for Jira Cloud. List, view, move and assign issues, plan sprints, and script all of it with JSON, CSV and exit codes that mean one thing each.</p>
          <div className="order-2 mt-3 space-y-3 sm:order-none sm:mt-4">
            <p className="hero-independence text-sm font-medium">Independently maintained. Not affiliated with Atlassian.</p>
            <div className="hero-open-source flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-muted-foreground">
              <a className={cn(buttonVariants({ size: 'sm' }), 'gh-badge gap-1.5')} href={repo}><GitHubMark className="size-4" />View on GitHub</a>
              <p>Open source under the <a className="link text-foreground" href={`${repo}/blob/main/LICENSE`}>AGPL-3.0 license</a>.</p>
            </div>
          </div>
          <p className="hero-proof order-5 mt-2 text-sm text-muted-foreground sm:order-none sm:mt-3">Runs within your Jira permissions, using your existing API token.</p>
          <div className="order-3 mt-5 w-full max-w-xl sm:order-none sm:mt-8"><Install /></div>
        </section>

        <section className="section" id="try" aria-labelledby="try-title">
          <SectionHead id="try-title" title="Try it before you install">
            <span className="example-label">The sandbox terminal runs on sample data from an example site. Nothing reaches Jira.</span> Pick a command, or type your own.
          </SectionHead>
          <ul className="divide-y overflow-hidden rounded-xl border">{examples.map(e => <li key={e.command}>
            <button type="button" onClick={() => run(e.command)} data-active={active === e.command} aria-label={`Run ${e.command}`}
              className="group flex w-full items-center gap-4 px-4 py-3 text-left transition-colors hover:bg-muted/60 focus-visible:bg-muted/60 focus-visible:outline-none data-[active=true]:bg-muted">
              <span className="min-w-0 flex-1">
                <code className="block font-mono text-[13px] font-medium break-words">{e.command}</code>
                <span className="block text-sm text-muted-foreground">{e.does}</span>
              </span>
              <Kbd className="opacity-60 group-hover:opacity-100 group-data-[active=true]:opacity-100"><CornerDownLeft aria-hidden="true" /></Kbd>
            </button>
          </li>)}</ul>
        </section>

        <section className="section" id="scripting" aria-labelledby="scripting-title">
          <SectionHead id="scripting-title" title="Predictable enough to script">
            Data goes to stdout. Messages and prompts go to stderr. Add <code className="inline-code">--json</code> and failures become JSON on stdout too, so a script never has to parse prose.
          </SectionHead>
          <div className="overflow-hidden rounded-xl border">
            <Table className="exit-table">
              <TableHeader><TableRow className="bg-muted/40 hover:bg-muted/40"><TableHead className="w-16 pl-4">Exit</TableHead><TableHead>Meaning</TableHead><TableHead className="pr-4 text-right"><span className="sr-only">Example</span></TableHead></TableRow></TableHeader>
              <TableBody>{exitCodes.map(row => <TableRow key={row.code}>
                <TableCell className="pl-4 align-top font-mono text-base font-semibold">{row.code}</TableCell>
                <TableCell className="align-top whitespace-normal">
                  <p><span className="font-medium">{row.meaning}.</span> <span className="text-muted-foreground">{row.detail}</span></p>
                  {row.example
                    ? <p className="mt-1 text-[13px] text-muted-foreground">Example: <code className="inline-code">{row.example}</code> {row.why}, so it exits {row.code}.</p>
                    : <p className="mt-1 text-[13px] text-muted-foreground">Press <Kbd>Ctrl</Kbd> <Kbd>C</Kbd> in the terminal to see it.</p>}
                </TableCell>
                <TableCell className="pr-4 text-right align-top">
                  {row.example && <button type="button" className={buttonVariants({ variant: 'outline', size: 'sm' })} onClick={() => run(row.example!)} aria-label={`Run ${row.example} in the sandbox`}>Run</button>}
                </TableCell>
              </TableRow>)}</TableBody>
            </Table>
          </div>
          <div className="mt-8 grid gap-8 xl:grid-cols-2">
            <div className="min-w-0">
              <h3 className="mb-3 text-sm font-medium">Every error has one shape with <code className="inline-code">--json</code></h3>
              <pre tabIndex={0} className="overflow-x-auto rounded-xl border bg-[#0a0a0a] p-4 font-mono text-[13px] leading-relaxed text-[#ededed]"><code>{`$ jira issue view ENG-99 --json
{
  "error": {
    "code": "jira_error",
    "message": "Error: GET /rest/api/3/issue/…",
    "status": 404
  }
}`}</code></pre>
            </div>
            <ul className="space-y-3 text-sm text-muted-foreground xl:pt-8">
              {[
                <><code className="inline-code">--no-input</code>, or any input that isn’t a terminal, never prompts. Missing values fail with exit 2.</>,
                <>Global flags such as <code className="inline-code">--project</code> and <code className="inline-code">--json</code> work before or after the command.</>,
                <>Deletes ask for confirmation, or need <code className="inline-code">--yes</code> when nothing can prompt.</>,
                <>Tokens stay in your OS credential store and are redacted from error output.</>,
              ].map((rule, i) => <li key={i} className="flex gap-2.5"><Check className="mt-0.5 size-4 shrink-0 text-foreground" aria-hidden="true" /><span>{rule}</span></li>)}
            </ul>
          </div>
        </section>

        <Reference onRun={run} />

        <section className="section" aria-labelledby="setup-title">
          <SectionHead id="setup-title" title="From install to your first list" />
          <ol className="steps space-y-6">
            <li><p><a className="link" href="#get-started">Choose your system</a> and run its install command. It puts <code className="inline-code">jira</code> on your PATH.</p></li>
            <li><p>Sign in with an API token. Guided login links to token creation, explains scopes, and stores the token in your OS credential store by default. For headless use, choose environment authentication or explicit POSIX plaintext file storage.</p><code className="step-code">jira auth login --profile work</code></li>
            <li><p>Pick a default project, then list what’s open.</p><code className="step-code">jira context use --project ENG</code><code className="step-code">jira issue list --open</code></li>
          </ol>
        </section>

        <section className="section" id="faq" aria-labelledby="questions-title">
          <SectionHead id="questions-title" title="Before you install">What it supports today, and what it doesn’t yet.</SectionHead>
          <Accordion className="faq max-w-2xl">
            <AccordionItem value="independent"><AccordionTrigger>Is this an official Atlassian tool?</AccordionTrigger><AccordionContent>No. CLI Toolkit for Jira is independently maintained by <a className="link" href="https://github.com/User17745">User17745</a> and is not affiliated with, endorsed by, or sponsored by Atlassian. The <code className="inline-code">jira</code> command runs this toolkit and connects to your Jira Cloud account.</AccordionContent></AccordionItem>
            <AccordionItem value="auth"><AccordionTrigger>Do I need a new Jira account?</AccordionTrigger><AccordionContent>No. Use your existing Jira Cloud site, email, and API token. The CLI uses your account’s Jira permissions. Guided login links to token creation and explains scopes; tokens cannot refresh automatically.</AccordionContent></AccordionItem>
            <AccordionItem value="support"><AccordionTrigger>Does it support every Jira edition?</AccordionTrigger><AccordionContent>The current release supports standard Jira Cloud issue workflows, plus Software boards and sprints where permissions allow. Data Center and Service Management customer-request APIs are future work.</AccordionContent></AccordionItem>
            <AccordionItem value="api"><AccordionTrigger>Can I call any Jira API endpoint?</AccordionTrigger><AccordionContent>Not yet. Generic API requests with <code className="inline-code">jira api</code> and <code className="inline-code">--spec</code> discovery are <a className="link" href={`${repo}/blob/main/docs/sprints/v2.5-api/roadmap.md`}>planned for v2.5</a>. Today’s commands are the ones listed above.</AccordionContent></AccordionItem>
            <AccordionItem value="platform"><AccordionTrigger>Which systems can run it?</AccordionTrigger><AccordionContent>Native releases support macOS 15+ on Apple Silicon and Intel, Linux x86_64 with glibc 2.39+, and Windows 10+ x86_64. For other compatible systems, install the verified Python wheel with Python 3.10 or later. <a className="link" href={`${repo}/blob/main/docs/migration/upgrade-to-v2.md`}>See installation options.</a></AccordionContent></AccordionItem>
            <AccordionItem value="upgrade"><AccordionTrigger>Already using jsup or jira-cli-toolkit?</AccordionTrigger><AccordionContent>Your configuration and credential references stay the same. Upgrade through the manager that owns your installation. Existing command names still work in v2.x and show a migration notice. <a className="link" href={`${repo}/blob/main/docs/migration/legacy-commands.md`}>Use the migration guide.</a></AccordionContent></AccordionItem>
          </Accordion>
        </section>
      </main>
      <footer className="border-t">
        <div className="pt-8 pb-28 min-[1100px]:pb-12">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <a className="flex items-center gap-2" href="#">
              <BrandMark />
              <span className="font-semibold tracking-tight">CLI Toolkit</span> <span className="text-sm text-muted-foreground">for Jira</span>
            </a>
            <nav aria-label="Project links" className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground">
              <a className="hover:text-foreground" href={repo}>Source</a><a className="hover:text-foreground" href={`${repo}/blob/main/LICENSE`}>License</a><a className="hover:text-foreground" href={latest}>Releases</a><a className="hover:text-foreground" href={`${repo}/issues`}>Report an issue</a><a className="hover:text-foreground" href={notices}>Third-party notices</a>
            </nav>
          </div>
          <section className="independent-notice mt-8 max-w-[80ch] space-y-3 text-xs leading-relaxed text-muted-foreground" aria-labelledby="independence-title">
            <h2 id="independence-title" className="text-sm font-medium text-foreground">Independent project and intellectual property notice</h2>
            <p>CLI Toolkit for Jira is independently developed and maintained. It is not affiliated with, sponsored by, endorsed by, or otherwise associated with Atlassian or any of its affiliated business entities. It is not an official Jira product.</p>
            <p>References to Jira and Atlassian, including the <code className="font-mono">jira</code> command name, identify the external service and describe compatibility and usage. They do not claim ownership of those names or imply an official relationship. Jira and Atlassian are trademarks of Atlassian.</p>
            <p>No infringement of third-party trademarks, copyrights, patents, or other intellectual property rights is intended. This statement does not establish that a particular use is non-infringing or replace any permission that may be required.</p>
            <p className="project-license border-t pt-3">Copyright © 2026 Abhishek Aggarwal. Original project code is licensed under <a className="link" href={`${repo}/blob/main/LICENSE`}>GNU AGPL v3 only (AGPL-3.0-only)</a>. You may redistribute and modify it under that license. Provided without warranty, including merchantability or fitness for a particular purpose. <a className="link" href={`${repo}/blob/main/NOTICE`}>Project notice</a>. <a className="link" href={notices}>Third-party licenses</a>. Third-party components and assets retain their applicable license terms. The project license does not grant rights to third-party trademarks.</p>
          </section>
        </div>
      </footer>
      </div>

      <aside className="terminal-column" aria-label="Sandbox">
        <Terminal ref={terminal} open={open} onOpenChange={setOpen} />
      </aside>
    </div>

  </>
}
export default App
