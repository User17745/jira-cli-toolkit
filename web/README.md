# Jira CLI Toolkit landing page

React, TypeScript and Vite, with Tailwind CSS and generated shadcn/ui (Base UI) components. The site is static: no credentials, Jira requests, analytics, or backend. Fonts and visual assets are self-hosted. [Design decisions](DESIGN.md) explain the installation-first layout.

## Develop

Use Node.js 24 LTS and npm:

```bash
npm ci
npm run dev
```

Open the printed URL under `/jira-cli-toolkit/`. The Vite base is the GitHub Pages repository path. Change `vite.config.ts`, the canonical/OG URLs in `index.html`, and repo links in `src/App.tsx` together if hosting moves.

## Verify

```bash
npm run lint
npm run build
npx playwright install chromium
npm test
```

Playwright checks the built site served by Vite preview: OS tabs and keyboard navigation, exact copied commands and clipboard failures, example tabs, FAQ, mobile menu, responsive overflow, first-fold installation, and missing assets/console errors. It does not contact Jira or execute copied commands. Installers are tested separately by Python fixtures and native build integration on all four supported targets.

## Publish

The [Pages workflow](../.github/workflows/pages.yml) builds and tests pull requests and main. Only main deploys through GitHub’s Pages artifact/deployment actions. Repository Settings → Pages must select **GitHub Actions** as the build source. No npm build output is committed. Dependencies are locked in `package-lock.json`; action revisions are pinned.

Public URL: https://user17745.github.io/jira-cli-toolkit/

The installation panel links to source-controlled POSIX/PowerShell scripts on main, which resolve the latest stable GitHub Release. Manual installation links to `/releases/latest`. Update documentation and browser assertions whenever these commands or platform constraints change. Raw authenticated API/spec functionality remains explicitly planned for v2.5.

Font and component license notices are served from `public/third-party-notices.txt`; preserve them when deploying. They do not assign a license to this repository’s own code.

Components and `src/shadcn.css` are generated/vendored from shadcn/ui 4.21.3. The code-generation CLI is not a build or runtime dependency. Keep its MIT notice when editing these sources.
