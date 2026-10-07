import { useState } from 'react'
import { Laptop, ArrowDown, ArrowUpRight, Check, CheckCheck, ChevronRight, Code2, Copy, GitPullRequest, KeyRound, Menu, Monitor, ShieldCheck, Terminal, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import './App.css'

const repo = 'https://github.com/User17745/jira-cli-toolkit'
const docs = `${repo}/blob/main/README.md`
const latest = `${repo}/releases/latest`
const raw = 'https://raw.githubusercontent.com/User17745/jira-cli-toolkit/main/scripts'
type OS = 'macos' | 'linux' | 'windows'
const platforms: Record<OS, { name: string; icon: typeof Laptop; command: string; note: string }> = {
  macos: { name: 'macOS', icon: Laptop, command: `curl -fsSL ${raw}/install.sh | bash\nexport PATH="$HOME/.local/bin:$PATH"`, note: 'macOS 15+ · Apple Silicon or Intel' },
  linux: { name: 'Linux', icon: Terminal, command: `curl -fsSL ${raw}/install.sh | bash\nexport PATH="$HOME/.local/bin:$PATH"`, note: 'x86_64 · glibc 2.39+ (Ubuntu 24.04+)' },
  windows: { name: 'Windows', icon: Monitor, command: `irm ${raw}/install.ps1 | iex`, note: 'Windows 10+ x86_64 · PowerShell 5.1 or later' },
}
const demos = {
  issues: { label: 'Find your next issue', command: 'jira issue list -p ENG --open', lines: ['Key      Summary                       Status', 'ENG-42   Ship the onboarding flow      In Progress', 'ENG-43   Fix keyboard navigation       To Do', 'ENG-44   Update release notes          To Do'], footer: 'Project ENG · 3 example issues' },
  boards: { label: 'Plan a sprint', command: 'jira sprint list --board 123', lines: ['ID    Name                  State', '456   Onboarding sprint     active', '457   Accessibility         future', '458   Release polish        future'], footer: 'Board 123 · example sprint data' },
  scripts: { label: 'Make it scriptable', command: 'jira issue list -p ENG --open --json --no-input', lines: ['{', '  "issues": [', '    { "key": "ENG-42", "fields": { "summary":', '        "Ship the onboarding flow" } }', '  ], "fetched": 1', '}'], footer: 'Structured stdout · explicit exit codes' },
}

function CopyButton({ text, label = 'Copy command' }: { text: string; label?: string }) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle')
  async function copy() {
    try { await navigator.clipboard.writeText(text); setState('copied') }
    catch { setState('failed') }
    window.setTimeout(() => setState('idle'), 3500)
  }
  return <div className="copy-control">
    <Button variant="ghost" className="copy-button" onClick={copy} aria-label={label}>
      {state === 'copied' ? <Check size={16} /> : <Copy size={16} />}
      <span>{state === 'copied' ? 'Copied' : 'Copy'}</span>
    </Button>
    <span className="copy-status" role="status">{state === 'failed' ? 'Select the command and copy it manually.' : state === 'copied' ? 'Command copied to clipboard.' : ''}</span>
  </div>
}

function InstallPanel() {
  const [os, setOS] = useState<OS>(() => /Win/i.test(navigator.userAgent) ? 'windows' : /Linux/i.test(navigator.userAgent) ? 'linux' : 'macos')
  return <section className="install-panel" id="get-started" aria-labelledby="install-title">
    <div className="install-title-row"><h2 id="install-title">Get started</h2><Badge variant="secondary"><span className="status-dot" /> Native install</Badge></div>
    <p className="install-intro">One command. Your terminal does the rest.</p>
    <Tabs value={os} onValueChange={(value) => setOS(value as OS)} className="os-tabs">
      <TabsList activateOnFocus className="os-list" aria-label="Installation operating system">
        {(Object.keys(platforms) as OS[]).map(key => { const Icon = platforms[key].icon; return <TabsTrigger key={key} value={key}><Icon size={16} />{platforms[key].name}</TabsTrigger> })}
      </TabsList>
      {(Object.keys(platforms) as OS[]).map(key => <TabsContent value={key} key={key}>
        <div className="install-code"><div className="code-top"><span>{key === 'windows' ? 'PowerShell' : 'Terminal'}</span><CopyButton text={platforms[key].command} label={`Copy ${platforms[key].name} installation command`} /></div><pre tabIndex={0}><code>{platforms[key].command}</code></pre></div>
        <p className="platform-note">{platforms[key].note}</p>
      </TabsContent>)}
    </Tabs>
    <div className="install-check"><ShieldCheck size={16} /><span>Verifies release checksums before installing.</span></div>
    <div className="install-links"><a href={latest}>Prefer a manual install?<ArrowUpRight size={15} /></a><a href={`${repo}/blob/main/docs/migration/upgrade-to-v2.md`}>Upgrading? Read the guide.</a></div>
  </section>
}

function Workbench() {
  const [demo, setDemo] = useState('issues')
  return <section className="workbench" id="workflows" aria-label="Jira command examples">
    <div className="workbench-top"><span><Terminal size={17} /> Less switching. More shipping.</span><span className="example-label">Illustration with sample data</span></div>
    <div className="workbench-body">
      <div className="terminal-demo">
        <Tabs value={demo} onValueChange={(value) => setDemo(String(value))}>
          <TabsList activateOnFocus variant="line" className="demo-tabs" aria-label="Command examples">
            <TabsTrigger value="issues">Issues</TabsTrigger><TabsTrigger value="boards">Sprints</TabsTrigger><TabsTrigger value="scripts">JSON</TabsTrigger>
          </TabsList>
          {Object.entries(demos).map(([key, example]) => <TabsContent key={key} value={key}>
            <div className="terminal-prompt"><span>$</span><code>{example.command}</code><CopyButton text={example.command} label={`Copy ${example.label.toLowerCase()} command`} /></div>
            <pre className="terminal-output" tabIndex={0}>{example.lines.join('\n')}</pre>
            <div className="terminal-footer"><span className="status-dot" />{example.footer}</div>
          </TabsContent>)}
        </Tabs>
      </div>
      <div className="mini-board" aria-label="Illustrative project workflow with sample data">
        <div className="board-heading"><span className="project-symbol">E</span><div><strong>Engineering</strong><span>Original workflow illustration.</span></div><GitPullRequest size={19} /></div>
        <div className="board-columns">
          <div className="board-lane"><h3>To do <span>2</span></h3><div className="issue-note"><span><span className="issue-kind bug" />ENG-43</span><p>Fix keyboard navigation</p><div className="issue-bottom"><Badge variant="secondary">Accessibility</Badge><span className="avatar">JL</span></div></div><div className="issue-note"><span><span className="issue-kind" />ENG-44</span><p>Update release notes</p><div className="issue-bottom"><Badge variant="secondary">Release</Badge><span className="avatar blue">AK</span></div></div></div>
          <div className="board-lane"><h3>In progress <span>1</span></h3><div className="issue-note active-issue"><span><span className="issue-kind" />ENG-42</span><p>Ship the onboarding flow</p><div className="issue-bottom"><Badge variant="secondary">Onboarding</Badge><span className="avatar blue">AK</span></div></div><div className="board-hint"><CheckCheck size={17} /><span>Your workflow.<br />In your terminal.</span></div></div>
        </div>
      </div>
    </div>
  </section>
}

function App() {
  const [menu, setMenu] = useState(false)
  return <>
    <a className="skip-link" href="#get-started">Skip to installation</a>
    <header className="site-header"><div className="header-inner">
      <a className="brand" href="#" aria-label="CLI Toolkit for Jira home"><span className="brand-icon"><Terminal size={24} /></span><span className="brand-command">CLI Toolkit</span><span className="brand-name">for Jira</span></a>
      <nav className="desktop-nav" aria-label="Main navigation"><a href="#workflows">Workflows</a><a href={docs}>Documentation</a><a className="github-link" href={repo}><Code2 size={17} /> GitHub<ArrowUpRight size={14} /></a></nav>
      <Button variant="ghost" className="menu-toggle" aria-label={menu ? 'Close navigation' : 'Open navigation'} aria-expanded={menu} onClick={() => setMenu(!menu)}>{menu ? <X /> : <Menu />}</Button>
    </div>{menu && <nav className="mobile-nav" aria-label="Mobile navigation"><a href="#workflows" onClick={() => setMenu(false)}>Workflows</a><a href={docs}>Documentation</a><a href={repo}>GitHub</a></nav>}</header>
    <main>
      <div className="page-shell">
        <section className="hero" aria-labelledby="hero-title"><div className="hero-copy">
          <div className="cloud-note"><span className="small-terminal">$ jira</span><span>Independent CLI for Jira Cloud</span></div>
          <h1 id="hero-title">Your work.<br />At your command.</h1>
          <p className="hero-description">Find issues, move work forward, and manage sprints. Right where you already work.</p>
          <p className="hero-independence">Independently maintained. Not affiliated with Atlassian.</p>
          <div className="hero-actions"><a className="text-link" href="#workflows">See it in action <ArrowDown size={16} /></a><a className="release-link" href={latest}>Latest release <ArrowUpRight size={15} /></a></div>
          <div className="hero-proof"><span><Check size={15} /> Within your Jira permissions</span><span><KeyRound size={15} /> Your existing API token</span></div>
        </div><InstallPanel /></section>
        <Workbench />
        <section className="setup-strip" aria-label="Next steps"><div><span className="setup-number">1</span><p>Install <code>jira</code><span>Choose your OS above.</span></p></div><div><span className="setup-number">2</span><p>Connect your account<span><code>jira auth login --profile work</code></span></p></div><div><span className="setup-number">3</span><p>Pick your project<span><code>jira context use --project ENG</code></span></p></div></section>
      </div>
      <section className="capabilities" aria-labelledby="capabilities-title"><div className="page-shell"><div className="section-intro"><h2 id="capabilities-title">Fits the way<br />your team works.</h2><p>Keep your projects, permissions, and workflows.<br />Bring them into your terminal.</p></div>
        <div className="feature-row"><div className="feature-copy"><GitPullRequest className="feature-icon" /><h3>Work with your project’s fields.</h3><p>Create and edit issues, add comments and attachments, and follow the transitions your workflow allows. Field discovery helps you supply the right inputs.</p><a href={`${docs}#everyday-workflows`}>Explore the commands <ChevronRight size={16} /></a></div><div className="field-example"><div className="example-command"><code>jira project fields -p ENG --type Bug</code><Code2 size={18} /></div><div className="field-line"><span>Summary</span><Badge>Required</Badge></div><div className="field-line"><span>Issue type</span><strong>Bug</strong></div><div className="field-line"><span>Your custom fields</span><strong>Discovered from Jira</strong></div><div className="field-line"><span>Available transitions</span><strong>Your workflow</strong></div></div></div>
        <div className="feature-row"><div className="feature-copy"><KeyRound className="feature-icon" /><h3>Choose your account and context.</h3><p>Use named profiles for different accounts and sites. Login defaults to your OS credential store. For headless use, choose environment authentication or explicit POSIX plaintext file storage. Guided login explains setup and permissions.</p><a href={`${docs}#authentication-and-profiles`}>Set up authentication <ChevronRight size={16} /></a></div><div className="profile-example"><div className="profile-top"><span className="profile-avatar">W</span><div><strong>work</strong><span>Example profile · native storage</span></div><Badge className="profile-status"><Check size={12} /> Connected</Badge></div><div className="profile-detail"><span>Project</span><strong>ENG</strong></div><div className="profile-detail"><span>Token</span><strong><ShieldCheck size={15} /> OS credential store</strong></div><code>jira auth status --profile work</code></div></div>
        <div className="feature-row"><div className="feature-copy"><Code2 className="feature-icon" /><h3>Ready for scripts and agents.</h3><p>Use structured JSON, CSV, explicit exit codes, and noninteractive commands. Build repeatable workflows around the commands you use every day.</p><a href={`${docs}#automation-and-agents`}>Automate a workflow <ChevronRight size={16} /></a></div><div className="automation-example"><div className="automation-label"><Terminal size={17} /><span>Readable in a terminal. Useful in a script.</span></div><pre><code>{'jira issue list -p ENG --open \\\n  --csv --columns key,summary,status\n\njira issue view ENG-42 --json --no-input'}</code></pre><p>Generic API requests and <code>--spec</code> discovery are <a href={`${repo}/blob/main/docs/sprints/v2.5-api/roadmap.md`}>planned for v2.5</a>.</p></div></div>
      </div></section>
      <section className="help-section page-shell" aria-labelledby="help-title"><div><h2 id="help-title">A few things<br />before you start.</h2><p>Install it, connect it, make it yours.</p><a className="text-link" href={docs}>Read the documentation <ArrowUpRight size={15} /></a></div><Accordion className="faq">
        <AccordionItem value="independent"><AccordionTrigger>Is this an official Atlassian tool?</AccordionTrigger><AccordionContent>No. CLI Toolkit for Jira is independently maintained by <a href="https://github.com/User17745">User17745</a> and is not affiliated with, endorsed by, or sponsored by Atlassian. The <code>jira</code> command runs this toolkit and connects to your Jira Cloud account.</AccordionContent></AccordionItem>
        <AccordionItem value="auth"><AccordionTrigger>Do I need a new Jira account?</AccordionTrigger><AccordionContent>No. Use your existing Jira Cloud site, email, and API token. The CLI uses your account’s Jira permissions. Guided login links to token creation and explains scopes; tokens cannot refresh automatically.</AccordionContent></AccordionItem>
        <AccordionItem value="platform"><AccordionTrigger>Which systems can run it?</AccordionTrigger><AccordionContent>Native releases support macOS 15+ on Apple Silicon and Intel, Linux x86_64 with glibc 2.39+, and Windows 10+ x86_64. For other compatible systems, install the verified Python wheel with Python 3.10 or later. <a href={`${repo}/blob/main/docs/migration/upgrade-to-v2.md`}>See installation options.</a></AccordionContent></AccordionItem>
        <AccordionItem value="upgrade"><AccordionTrigger>Already using jsup or jira-cli-toolkit?</AccordionTrigger><AccordionContent>Your configuration and credential references stay the same. Upgrade through the manager that owns your installation. Existing command names still work in v2.x and show a migration notice. <a href={`${repo}/blob/main/docs/migration/legacy-commands.md`}>Use the migration guide.</a></AccordionContent></AccordionItem>
        <AccordionItem value="support"><AccordionTrigger>Does it support every Jira edition?</AccordionTrigger><AccordionContent>The current release supports standard Jira Cloud issue workflows, plus Software boards and sprints where permissions allow. Data Center and Service Management customer-request APIs are future work.</AccordionContent></AccordionItem>
      </Accordion></section>
      <section className="bottom-cta page-shell"><div><h2>Your next issue is a command away.</h2><p>Get back to the work, without leaving your terminal.</p></div><a className="primary-link" href="#get-started"><Terminal size={18} /> Install the CLI</a></section>
    </main>
    <footer className="site-footer page-shell"><a className="footer-brand" href="#"><Terminal size={18} /><strong>CLI Toolkit</strong><span>for Jira</span></a><span>Independent tools for your terminal.</span><div><a href={repo}>Source</a><a href={latest}>Releases</a><a href={`${repo}/issues`}>Report an issue</a><a href={`${import.meta.env.BASE_URL}third-party-notices.txt`}>Third-party notices</a></div></footer>
    <p className="independent-notice page-shell">Independent project. Not affiliated with, endorsed by, or sponsored by Atlassian. Jira and Atlassian are trademarks of Atlassian.</p>
  </>
}
export default App
