import { test, expect, type Page } from '@playwright/test'

const raw = 'https://raw.githubusercontent.com/User17745/jira-cli-toolkit/main/scripts'
const terminal = (page: Page) => page.getByRole('textbox', { name: 'Sandbox command' })
const log = (page: Page) => page.getByRole('log', { name: 'Sandbox output' })
const lastEntry = (page: Page) => log(page).locator('.t-entry').last()
const exitCode = (page: Page) => page.locator('.t-status .t-exit')

// Below 1100px the terminal is docked and starts collapsed.
async function openTerminal(page: Page) {
  const toggle = page.getByRole('button', { name: 'Sandbox terminal' })
  if (await toggle.isVisible() && await toggle.getAttribute('aria-expanded') === 'false') await toggle.click()
}

// Collapses the mobile dock so it doesn't cover the page; does nothing on desktop.
async function closeTerminal(page: Page) {
  const toggle = page.getByRole('button', { name: 'Sandbox terminal' })
  if (await toggle.isVisible() && await toggle.getAttribute('aria-expanded') === 'true') await toggle.click()
}

async function run(page: Page, command: string) {
  await openTerminal(page)
  await terminal(page).fill(command)
  await terminal(page).press('Enter')
}

test('OS tabs expose and copy exact working installation commands', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.goto('./')
  for (const os of ['macOS', 'Linux', 'Windows']) {
    await page.getByRole('tab', { name: os, exact: true }).click()
    const command = os === 'Windows' ? `irm ${raw}/install.ps1 | iex` : `curl -fsSL ${raw}/install.sh | bash\nexport PATH="$HOME/.local/bin:$PATH"`
    await expect(page.getByRole('tabpanel', { name: os, exact: true }).locator('pre')).toHaveText(command)
    await page.getByRole('button', { name: `Copy ${os} installation command` }).click()
    await expect(page.locator('.install-code:visible [role=status]')).toHaveText('Command copied to clipboard.')
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(command)
  }
  await expect(page.getByRole('link', { name: 'Prefer a manual install?' })).toHaveAttribute('href', 'https://github.com/User17745/jira-cli-toolkit/releases/latest')
})

test('clipboard failures provide recovery without a false success', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(navigator, 'clipboard', { value: { writeText: () => Promise.reject(new Error('denied')) } }))
  await page.goto('./')
  await page.locator('.install-code button').click()
  await expect(page.locator('.install-code:visible [role=status]')).toHaveText('Select the command and copy it manually.')
})

test('keyboard tabs switch the installation platform', async ({ page }) => {
  await page.goto('./')
  await page.getByRole('tab', { name: 'macOS', exact: true }).click()
  await page.getByRole('tab', { name: 'macOS', exact: true }).press('ArrowRight')
  await expect(page.getByRole('tab', { name: 'Linux', exact: true })).toHaveAttribute('aria-selected', 'true')
})

test('sandbox opens on an agent standup digest, labels sample data and keeps state', async ({ page }) => {
  await page.goto('./')
  await expect(page.locator('.example-label')).toHaveText('The sandbox terminal runs on sample data from an example site. Nothing reaches Jira.')
  await openTerminal(page)
  await expect(log(page).locator('.t-ask')).toContainText('Give me a standup digest for the active ENG sprint')
  await expect(log(page).locator('.t-tool-call').first()).toContainText('Bash(jira sprint list --state active --json)')
  await expect(log(page).locator('.t-tool-out').first()).toContainText('"maxResults": 50')
  await expect(log(page).locator('.t-reply')).toContainText('waits on OPS-7 Rotate the staging API token (Sam, To Do)')
  await run(page, 'jira issue list --open')
  await expect(log(page).getByRole('table', { name: 'Open issues (4 fetched)' })).toBeVisible()

  await run(page, "jira issue transition ENG-43 --to 'In Review'")
  await expect(lastEntry(page).locator('.t-out')).toHaveText('Moved ENG-43 → In Review')
  await expect(exitCode(page)).toHaveText('exit 0')
  await run(page, 'jira issue list --open --csv --columns key,status')
  await expect(lastEntry(page).locator('.t-out')).toContainText('ENG-43,In Review')

  await page.getByRole('button', { name: 'Reset sandbox' }).click()
  await run(page, 'jira issue list --open --csv --columns key,status')
  await expect(lastEntry(page).locator('.t-out')).toContainText('ENG-43,To Do')
})

test('sandbox reproduces argparse errors, JSON errors and exit codes', async ({ page }) => {
  await page.goto('./')
  await run(page, 'jira issue list --json --csv')
  await expect(lastEntry(page).locator('.t-err')).toContainText('jira issue list: error: argument --csv: not allowed with argument --json')
  await expect(lastEntry(page).locator('.t-rprompt')).toHaveText('exit 2')

  await run(page, 'jira issue lst')
  await expect(lastEntry(page).locator('.t-err')).toContainText("argument issue_action: invalid choice: 'lst'")

  await run(page, 'jira issue view ENG-99 --json')
  await expect(lastEntry(page).locator('.t-out')).toContainText('"code": "jira_error"')
  await expect(exitCode(page)).toHaveText('exit 1')

  await terminal(page).fill('jira issue list')
  await terminal(page).press('Control+c')
  await expect(exitCode(page)).toHaveText('exit 130')
})

test('sandbox completes with Tab, suggests from history and releases focus after Escape', async ({ page }) => {
  await page.goto('./')
  await openTerminal(page)
  await expect(page.locator('.t-ghost')).toHaveText('ira --help')
  await terminal(page).focus()
  await terminal(page).press('ArrowRight')
  await expect(terminal(page)).toHaveValue('jira --help')
  await terminal(page).fill('jira iss')
  await terminal(page).press('Tab')
  await expect(terminal(page)).toHaveValue('jira issue ')
  await terminal(page).pressSequentially('transition ENG-4')
  await terminal(page).press('Tab')
  await expect(lastEntry(page).locator('.t-options')).toContainText('ENG-42')
  await terminal(page).fill('')
  await terminal(page).press('ArrowUp')
  await expect(terminal(page)).toHaveValue('jira issue list --open')
  await terminal(page).press('Escape')
  await terminal(page).press('Tab')
  await expect(terminal(page)).not.toBeFocused()
})

test('sandbox demonstrates jira api requests, spec lookups and their errors', async ({ page }) => {
  await page.goto('./')
  await page.getByRole('button', { name: 'Run jira api /rest/api/3/issue -X POST --spec' }).click()
  await expect(lastEntry(page).locator('.t-out')).toContainText('"operationId": "createIssue"')
  await run(page, 'jira api /rest/api/3/issue/ENG-42')
  await expect(lastEntry(page).locator('.t-out')).toContainText('"key": "ENG-42"')
  await run(page, 'jira api /rest/api/3/issue/ENG-99')
  await expect(lastEntry(page).locator('.t-err')).toContainText('"status": 404')
  await expect(exitCode(page)).toHaveText('exit 1')
  await run(page, 'jira api /rest/api/3/issue --data {}')
  await expect(lastEntry(page).locator('.t-err')).toContainText('--data needs an explicit method that accepts a body, such as -X POST.')
  await expect(exitCode(page)).toHaveText('exit 2')
})

test('the sandbox creates sprints, fills them and adds comments, with the real errors', async ({ page }) => {
  await page.goto('./')
  await run(page, "jira sprint create --board 18 --name 'APP Week 1'")
  await expect(lastEntry(page).locator('.t-out')).toHaveText("✓ {'id': 458, 'self': 'https://example.atlassian.net/rest/agile/1.0/sprint/458', 'state': 'future', 'name': 'APP Week 1', 'originBoardId': 18}")
  await run(page, 'jira sprint add-issues 458 APP-1 APP-2')
  await expect(lastEntry(page).locator('.t-out')).toHaveText('✓ {}')
  await run(page, 'jira issue list -p APP --json --fields customfield_10020 --limit 1 --order-by key --order asc')
  await expect(lastEntry(page).locator('.t-out')).toContainText('"name": "APP Week 1"')
  await run(page, 'jira sprint add-issues 999 APP-1')
  await expect(lastEntry(page).locator('.t-err')).toContainText('-> 404')
  await expect(exitCode(page)).toHaveText('exit 1')
  await run(page, 'jira issue comment add ENG-42')
  await expect(lastEntry(page).locator('.t-err')).toContainText('Supply --message, --message-file, or interactive --editor.')
  await expect(exitCode(page)).toHaveText('exit 2')
  await run(page, "jira issue comment add ENG-42 -m 'Looks good' --json")
  await expect(lastEntry(page).locator('.t-out')).toContainText('"text": "Looks good"')
})

test('use cases replay an agent in the sandbox, and the sample site keeps its writes', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('./')
  // Choosing a card plays its replay.
  await page.getByRole('tab', { name: 'Developers' }).click()
  await expect(log(page).locator('.t-ask').last()).toContainText('PR #142 just merged. Update Jira to match.')
  await expect(log(page).locator('.t-tool-call').filter({ hasText: 'git log' })).toBeVisible()
  await expect(log(page).getByText('Moved ENG-43 → Done')).toBeVisible()
  await expect(lastEntry(page).locator('.t-note')).toContainText('ENG-43 is no longer there')
  await run(page, 'jira issue list --open --csv --columns key')
  await expect(lastEntry(page).locator('.t-out')).not.toContainText('ENG-43')
})

test('the planning replay fails its checks, re-plans, and skips to the end on any key', async ({ page }) => {
  await page.goto('./')
  await page.getByRole('button', { name: 'Watch an agent plan sprints' }).click()
  await expect(page.locator('#terminal-keys')).toContainText('agent replay')
  await terminal(page).press('x')
  await expect(log(page).getByRole('table', { name: 'Sprints' })).toContainText('APP Week 3')
  await expect(log(page).locator('.t-tool[data-state=failed] .t-tool-call')).toContainText('Bash(pytest tests/test_plan.py -q) exit 1')
  await expect(log(page).locator('.t-reply').last()).toContainText('Nobody has more than 8 of 10 points in any week')
  await expect(log(page).getByText('2 failed, 4 passed', { exact: false })).toBeVisible()
  await expect(page.locator('#terminal-keys')).toContainText('tab complete')
  await run(page, 'jira sprint list --board 18 --csv')
  await expect(lastEntry(page).locator('.t-out')).toContainText('460,future,APP Week 3')
})

test('arrow keys move between use-case cards without playing them', async ({ page }) => {
  await page.goto('./')
  await page.getByRole('tab', { name: 'Project managers' }).focus()
  await page.keyboard.press('ArrowRight')
  await expect(page.getByRole('tab', { name: 'Scrum masters' })).toBeFocused()
  await expect(page.locator('#terminal-keys')).toContainText('tab complete')
  await page.keyboard.press('Enter')
  await expect(log(page).locator('.t-ask').last()).toContainText('Nudge whoever can unblock the most.')
})

test('Ctrl+C stops a replay where it is', async ({ page }) => {
  await page.goto('./')
  await page.getByRole('tab', { name: 'Scrum masters' }).click()
  // Press only once the replay is running; earlier, Ctrl+C can land before it starts listening.
  await expect(page.locator('#terminal-keys')).toContainText('agent replay')
  await terminal(page).press('Control+c')
  await expect(exitCode(page)).toHaveText('exit 130')
  await expect(page.locator('#terminal-keys')).toContainText('tab complete')
  await expect(log(page).getByText('Try jira issue view OPS-7')).toHaveCount(0)
})

test('more replays: backlog cleanup, an incident, release notes and the first run before sign-in', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('./')
  const play = async (card: string) => {
    await closeTerminal(page)
    await page.getByRole('tab', { name: card }).click()
  }
  await play('Team leads A backlog')
  await expect(log(page).getByText("✓ {'updated': 'OPS-7', 'fields': ['priority'], 'operations': ['labels']}")).toBeVisible()
  await run(page, 'jira issue view OPS-7 --json')
  await expect(lastEntry(page).locator('.t-out')).toContainText('"name": "Highest"')

  await play('On-call engineers')
  await expect(log(page).getByText("✓ {'id': '10010', 'key': 'OPS-10'", { exact: false })).toBeVisible()
  await run(page, 'jira issue list -p OPS --open --csv --columns key,summary')
  await expect(lastEntry(page).locator('.t-out')).toContainText('OPS-8,Checkout returns 502 after the 09:10 deploy')

  await play('Release managers')
  await expect(log(page).locator('.t-reply').last()).toContainText('Tokens are redacted from error output (ENG-38)')

  await closeTerminal(page)
  await page.getByRole('button', { name: 'Replay a first run' }).click()
  await expect(log(page).locator('.t-tool[data-state=failed]').last()).toContainText('No complete credentials. Run auth login or config migrate.')
  await expect(log(page).locator('.t-reply').last()).toContainText('jira auth login --profile work')
  await expect(log(page).locator('.t-reply').last()).toContainText('Please don’t paste the token here.')
})

test('agent rules copy exactly and name the safe defaults', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.goto('./')
  await page.getByRole('button', { name: 'Copy the skill prompt' }).click()
  await expect(page.locator('#agents [role=status]:visible')).toHaveText('Prompt copied to clipboard.')
  const prompt = await page.evaluate(() => navigator.clipboard.readText())
  expect(prompt).toBe(await page.getByLabel('Prompt that creates the Jira skill').innerText())
  expect(prompt).toContain('Create a skill named "jira"')
  expect(prompt).toContain('~/.claude/skills/jira/SKILL.md')
  expect(prompt).toContain('Add `--json --no-input` to every command')

  await page.getByRole('tab', { name: 'One repository' }).click()
  await page.getByRole('button', { name: 'Copy the agent rules' }).click()
  await expect(page.locator('#agents [role=status]:visible')).toHaveText('Rules copied to clipboard.')
  const rules = await page.evaluate(() => navigator.clipboard.readText())
  expect(rules).toBe(await page.getByLabel('Agent rules for Jira').innerText())
  expect(rules).toContain('Add `--json --no-input` to every command')
  expect(rules).toContain('Deletes need `--yes`.')
  expect(rules).toContain('run `jira auth status --json --no-input`. If it fails, stop and ask me to sign in')
  expect(rules).toContain('Never ask for my API token')
  await expect(page.getByRole('link', { name: 'What the profile does and doesn’t protect' })).toHaveAttribute('href', /docs\/usage\.md#what-keeping-the-token/)
})

test('the first fold names the agents that can use it, with their marks', async ({ page }, info) => {
  const errors: string[] = []
  page.on('response', r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`) })
  await page.goto('./')
  const list = page.getByRole('list', { name: 'Agents that can use it' })
  await expect(list.getByRole('listitem')).toHaveCount(12)
  for (const name of ['Claude Code', 'Pi', 'OpenCode', 'Command Code', 'Cursor', 'GitHub Copilot', 'Gemini CLI', 'Cline', 'Windsurf', 'Zed', 'Warp', 'Qwen Code'])
    await expect(list.getByText(name, { exact: true })).toBeVisible()
  if (info.project.name === 'desktop') await expect(list).toBeInViewport()
  // Each mark loads, and the footer and notices say they belong to their owners.
  const loaded = await page.locator('.agent-logo').evaluateAll(spans => Promise.all(spans.map(span => {
    const url = getComputedStyle(span).maskImage.slice(5, -2)
    return fetch(url).then(r => r.ok && r.headers.get('content-type')?.includes('svg'))
  })))
  expect(loaded.every(Boolean)).toBe(true)
  await expect(page.locator('.independent-notice')).toContainText('The agent names and logos identify tools that can run the CLI')
  expect(errors).toEqual([])
})

test('outbound links open in a new tab without access to this page', async ({ page }) => {
  await page.goto('./')
  const outbound = page.locator('a[href^="http"]')
  expect(await outbound.count()).toBeGreaterThan(10)
  for (const link of await outbound.all()) {
    await expect(link).toHaveAttribute('target', '_blank')
    await expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  }
})

test('examples, exit-code rows and the command reference type into the terminal without moving the page', async ({ page }, info) => {
  await page.goto('./')
  await page.locator('#try').scrollIntoViewIfNeeded()
  const before = await page.evaluate(() => scrollY)
  await page.getByRole('button', { name: 'Run jira sprint list' }).click()
  await expect(log(page).getByRole('table', { name: 'Sprints' })).toBeVisible()
  if (info.project.name === 'desktop') expect(await page.evaluate(() => scrollY)).toBe(before)
  await expect(page.getByRole('button', { name: 'Run jira sprint list' })).toHaveAttribute('data-active', 'true')
  await expect(page.getByText('Example: jira issue view ENG-99 asks for an issue that doesn’t exist', { exact: false })).toBeVisible()

  if (info.project.name === 'mobile') await page.getByRole('button', { name: 'Sandbox terminal' }).click()
  await page.getByRole('button', { name: 'Run jira issue view ENG-99 in the sandbox' }).click()
  await expect(exitCode(page)).toHaveText('exit 1')

  if (info.project.name === 'mobile') await page.getByRole('button', { name: 'Sandbox terminal' }).click()
  await page.getByLabel('Filter commands').fill('attach')
  await expect(page.locator('.reference-filter [role=status]')).toHaveText(/^4 of \d+ commands$/)
  await page.getByRole('button', { name: /issue attachment upload/ }).click()
  await expect(lastEntry(page).locator('.t-out')).toContainText('usage: jira issue attachment upload')
  if (info.project.name === 'mobile') await page.getByRole('button', { name: 'Sandbox terminal' }).click()
  await page.getByLabel('Filter commands').fill('zzz')
  await expect(page.getByText('No command matches “zzz”.', { exact: false })).toBeVisible()
})

test('theme follows the system, toggles, persists and applies before paint', async ({ browser, baseURL }) => {
  const context = await browser.newContext({ baseURL, colorScheme: 'dark' })
  try {
    const page = await context.newPage()
    await page.goto('./')
    await expect(page.locator('html')).toHaveClass(/dark/)
    await page.getByRole('button', { name: 'Switch to light theme' }).click()
    await expect(page.locator('html')).not.toHaveClass(/dark/)
    // The inline script reads the saved choice before React mounts.
    await page.reload()
    expect(await page.evaluate(() => document.documentElement.classList.contains('dark'))).toBe(false)
    await expect(page.getByRole('button', { name: 'Switch to dark theme' })).toBeVisible()
  } finally {
    await context.close()
  }
})

test('ASCII background is decorative and the install prompts are not copied text', async ({ page }) => {
  await page.goto('./')
  await expect(page.locator('canvas.ascii-field')).toHaveAttribute('aria-hidden', 'true')
  const prompt = await page.locator('.install-code:visible .cmd-line').first().evaluate(e => getComputedStyle(e, '::before').content)
  expect(prompt).toMatch(/\$|PS>/)
})

test('the desktop terminal stays below the header at the end of the page', async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop', 'the terminal docks on narrow screens')
  await page.goto('./')
  await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'instant' }))
  const header = await page.locator('header').boundingBox()
  const terminal = await page.locator('.terminal').boundingBox()
  expect(terminal!.y).toBeGreaterThanOrEqual(header!.y + header!.height)
  expect(terminal!.y + terminal!.height).toBeLessThanOrEqual(page.viewportSize()!.height)
})

test('first fold says the project is open source and links to GitHub and the license', async ({ page }) => {
  await page.goto('./')
  const line = page.locator('.hero-open-source')
  await expect(line).toBeInViewport()
  await expect(line).toContainText('Open source under the AGPL-3.0 license.')
  await expect(line.getByRole('link', { name: 'View on GitHub' })).toHaveAttribute('href', 'https://github.com/User17745/jira-cli-toolkit')
  await expect(line.locator('svg')).toBeVisible()
  await expect(line.getByRole('link', { name: 'AGPL-3.0 license' })).toHaveAttribute('href', 'https://github.com/User17745/jira-cli-toolkit/blob/main/LICENSE')
})

test('first fold contains installation, assets load and narrow layouts do not overflow', async ({ page }, info) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  page.on('response', r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`) })
  await page.goto('./')
  await page.evaluate(() => document.fonts.ready)
  const command = await page.locator('.install-code').boundingBox()
  expect(command).toBeTruthy()
  // On narrow screens the docked terminal bar covers the bottom of the viewport.
  const dock = info.project.name === 'mobile' ? await page.locator('.terminal').boundingBox() : null
  expect(command!.y + command!.height).toBeLessThanOrEqual(dock ? dock.y : page.viewportSize()!.height)
  for (const width of info.project.name === 'mobile' ? [320, 390, 760] : [768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 1000 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    // Mobile emulation widens the layout viewport instead of scrolling, so compare with the device width too.
    expect(await page.evaluate(() => window.innerWidth)).toBe(width)
  }
  await page.setViewportSize(info.project.name === 'mobile' ? { width: 390, height: 844 } : { width: 1440, height: 1000 })
  await page.screenshot({ path: `test-results/landing-${info.project.name}-fold.png` })
  await page.screenshot({ path: `test-results/landing-${info.project.name}.png`, fullPage: true })
  expect(errors).toEqual([])
})

test('project identity and installation action clearly distinguish the independent CLI', async ({ page }, info) => {
  await page.goto('./')
  await expect(page).toHaveTitle('CLI Toolkit for Jira — Hand Jira Cloud to your AI agents')
  await expect(page.getByRole('link', { name: 'CLI Toolkit for Jira home' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Install the CLI', exact: true })).toHaveAttribute('href', '#get-started')
  await expect(page.locator('meta[property="og:image"]')).toHaveCount(0)
  await expect(page.locator('.independent-notice')).toContainText('not affiliated with, sponsored by, endorsed by, or otherwise associated with Atlassian or any of its affiliated business entities')
  await expect(page.locator('.independent-notice')).toContainText('including the jira command name')
  await expect(page.locator('.independent-notice')).toContainText('No infringement of third-party trademarks, copyrights, patents, or other intellectual property rights is intended.')
  await expect(page.locator('.independent-notice')).toContainText('This statement does not establish that a particular use is non-infringing')
  await expect(page.getByRole('link', { name: 'License', exact: true })).toHaveAttribute('href', 'https://github.com/User17745/jira-cli-toolkit/blob/main/LICENSE')
  await expect(page.locator('.project-license')).toContainText('AGPL-3.0-only')
  await expect(page.locator('.project-license')).toContainText('Provided without warranty')
  await page.locator('.independent-notice').scrollIntoViewIfNeeded()
  await expect(page.getByRole('heading', { name: 'Independent project and intellectual property notice' })).toBeInViewport()
  await page.screenshot({ path: `test-results/legal-notice-${info.project.name}.png` })
})

test('ownership, support claims, planned features and sample data are clear', async ({ page }) => {
  await page.goto('./')
  await expect(page.locator('.hero-independence')).toBeInViewport()
  await expect(page.locator('.hero-independence')).toHaveText('Independently maintained. Not affiliated with Atlassian.')
  await expect(page.locator('.hero-proof')).toContainText('within your Jira permissions')
  await expect(page.getByText('stores the token in your OS credential store by default', { exact: false })).toBeVisible()
  for (const selector of ['meta[name="description"]', 'meta[property="og:description"]']) {
    await expect(page.locator(selector)).toHaveAttribute('content', /Not affiliated with Atlassian/)
  }
  await page.getByRole('button', { name: 'Is this an official Atlassian tool?' }).click()
  await expect(page.getByRole('link', { name: 'User17745', exact: true })).toHaveAttribute('href', 'https://github.com/User17745')
  await expect(page.getByText('command runs this toolkit and connects to your Jira Cloud account.', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Do I need a new Jira account?' }).click()
  await expect(page.getByText('The CLI uses your account’s Jira permissions.', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Can I call any Jira API endpoint?' }).click()
  await expect(page.getByText('Keeping the token out of the command isn’t isolation', { exact: false })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Read the API and agent guide.' })).toHaveAttribute('href', /docs\/usage\.md#calling-any-rest-endpoint$/)
  const [notices] = await Promise.all([page.waitForEvent('popup'), page.getByRole('link', { name: 'Third-party notices', exact: true }).click()])
  await expect(notices.locator('body')).toContainText('SIL OPEN FONT LICENSE')
  await expect(notices.locator('body')).toContainText('The Geist Project Authors')
  await expect(notices.locator('body')).toContainText('Copyright (c) 2023 shadcn')
  await expect(notices.locator('body')).toContainText('macOS is a trademark of Apple Inc.')
  await expect(notices.locator('body')).toContainText('Windows and PowerShell are trademarks of the Microsoft group of companies.')
})

test('JavaScript-disabled visitors see independent identity and installation links', async ({ browser, baseURL }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, baseURL })
  try {
    const page = await context.newPage()
    await page.goto('./')
    await expect(page.locator('body')).toContainText('CLI Toolkit for Jira is independently maintained and is not affiliated with Atlassian.', { useInnerText: true })
    await expect(page.getByRole('link', { name: 'GitHub', exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'GNU AGPL v3 only license.', exact: true })).toHaveAttribute('href', 'https://github.com/User17745/jira-cli-toolkit/blob/main/LICENSE')
    await expect(page.getByRole('link', { name: 'Download the latest release.', exact: true })).toHaveAttribute('href', 'https://github.com/User17745/jira-cli-toolkit/releases/latest')
  } finally {
    await context.close()
  }
})
