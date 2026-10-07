import { test, expect } from '@playwright/test'

const raw = 'https://raw.githubusercontent.com/User17745/jira-cli-toolkit/main/scripts'
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

test('keyboard tabs, command examples, FAQ and mobile menu work', async ({ page }, info) => {
  await page.goto('./')
  await page.getByRole('tab', { name: 'macOS', exact: true }).click()
  await page.getByRole('tab', { name: 'macOS', exact: true }).press('ArrowRight')
  await expect(page.getByRole('tab', { name: 'Linux', exact: true })).toHaveAttribute('aria-selected', 'true')
  await page.getByRole('tab', { name: 'Sprints', exact: true }).click()
  await expect(page.getByRole('tabpanel', { name: 'Sprints', exact: true }).locator('.terminal-prompt code')).toHaveText('jira sprint list --board 123')
  await page.getByRole('tab', { name: 'JSON', exact: true }).click()
  await expect(page.getByRole('tabpanel', { name: 'JSON', exact: true }).locator('.terminal-output')).toContainText('"issues"')
  await page.getByRole('button', { name: 'Do I need a new Jira account?' }).click()
  await expect(page.getByText('No. Use your existing Jira Cloud site', { exact: false })).toBeVisible()
  if (info.project.name === 'mobile') {
    await page.getByRole('button', { name: 'Open navigation' }).click()
    await expect(page.getByRole('navigation', { name: 'Mobile navigation' })).toBeVisible()
    await page.getByRole('navigation', { name: 'Mobile navigation' }).getByRole('link', { name: 'Workflows' }).click()
    await expect(page.getByRole('button', { name: 'Open navigation' })).toHaveAttribute('aria-expanded', 'false')
  }
})

test('first fold contains installation, assets load and narrow layouts do not overflow', async ({ page }, info) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  page.on('response', r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`) })
  await page.goto('./')
  await page.evaluate(() => document.fonts.ready)
  const command = await page.locator('.install-code').boundingBox()
  expect(command).toBeTruthy()
  expect(command!.y + command!.height).toBeLessThanOrEqual(page.viewportSize()!.height)
  for (const width of info.project.name === 'mobile' ? [320, 390, 760] : [768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 1000 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  }
  await page.setViewportSize(info.project.name === 'mobile' ? { width: 390, height: 844 } : { width: 1440, height: 1000 })
  await page.screenshot({ path: `test-results/landing-${info.project.name}-fold.png` })
  await page.screenshot({ path: `test-results/landing-${info.project.name}.png`, fullPage: true })
  expect(errors).toEqual([])
})

test('project identity and installation action clearly distinguish the independent CLI', async ({ page }) => {
  await page.goto('./')
  await expect(page).toHaveTitle('CLI Toolkit for Jira — Your work. At your command.')
  await expect(page.getByRole('link', { name: 'CLI Toolkit for Jira home' })).toBeVisible()
  await expect(page.getByText('Independent CLI for Jira Cloud', { exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Install the CLI', exact: true })).toHaveAttribute('href', '#get-started')
  await expect(page.getByText('Install jira', { exact: true })).toHaveCount(0)
  await expect(page.locator('meta[property="og:image"]')).toHaveCount(0)
  await expect(page.locator('.independent-notice')).toHaveText('Independent project. Not affiliated with, endorsed by, or sponsored by Atlassian. Jira is a trademark of Atlassian.')
  await page.locator('.independent-notice').scrollIntoViewIfNeeded()
  await expect(page.locator('.independent-notice')).toBeInViewport()
})
