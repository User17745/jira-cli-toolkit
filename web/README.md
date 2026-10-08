# CLI Toolkit for Jira landing page

React, TypeScript and Vite, with Tailwind CSS and generated shadcn/ui (Base UI) components. The site is static: no credentials, Jira requests, analytics, or backend. Fonts and visual assets are self-hosted. [Design decisions](DESIGN.md) explain the layout and the sandbox terminal.

## Develop

Use Node.js 24 LTS and npm:

```bash
npm ci
npm run dev
```

Open the printed URL. Vercel serves the site from the domain root. The GitHub Pages copy is built with `BASE_PATH=/jira-cli-toolkit/`, which sets both the Vite base and the Playwright URL.

### Command data

The sandbox and command reference read `src/data/commands.json`, which is generated from the real `jira` argument parser. After changing commands, regenerate it from the repository root:

```bash
python scripts/command_tree.py > web/src/data/commands.json
```

`tests/test_website_commands.py` fails in Python CI when the file drifts from the parser. Help text and argument errors in the sandbox are a port of Python's argparse formatting at 80 columns, so `jira <command> --help` on the site matches the installed CLI. Sample issues, users and sprints live in `src/sandbox/sample.ts` and are illustrative. The agent replays behind the use cases live in `src/sandbox/scenarios.ts`; their `jira` steps run through the sandbox session, so keep them valid commands when the parser changes. If hosting moves, update the canonical and OG URLs in `index.html` and the repository links in `src/App.tsx` together.

## Verify

```bash
npm run lint
npm run build
npx playwright install chromium
npm test
```

Playwright checks the built site served by Vite preview: OS tabs and keyboard navigation, exact copied commands and clipboard failures, the sandbox terminal (sample state, argparse and JSON errors, exit codes, Tab completion, history suggestions, Escape releasing focus, examples typing in without moving the page, the mobile dock), the command reference, FAQ, the theme toggle (system default, persisted, applied before paint), the decorative ASCII background, the pinned desktop terminal, responsive overflow, first-fold installation, and missing assets/console errors. It does not contact Jira or execute copied commands. Installers are tested separately by Python fixtures and native build integration on all four supported targets for stable builds. RC/development builds retain existing native CLI smoke checks and are never selected by fresh installers.

## Publish

The [Pages workflow](../.github/workflows/pages.yml) builds and tests pull requests and main. Only main deploys through GitHub’s Pages artifact/deployment actions. Repository Settings → Pages must select **GitHub Actions** as the build source. No npm build output is committed. Dependencies are locked in `package-lock.json`; action revisions are pinned.

Public URL: https://jira.abhishekaggarwal.com/ (Vercel). The GitHub Pages copy is at https://user17745.github.io/jira-cli-toolkit/.

The installation panel links to source-controlled POSIX/PowerShell scripts on main, which resolve the latest stable GitHub Release. Manual installation links to `/releases/latest`. Update documentation and browser assertions whenever these commands or platform constraints change. Raw authenticated API/spec functionality remains explicitly planned for v2.5.

Font and component license notices are served from `public/third-party-notices.txt`; preserve them when deploying. Original project code is licensed under [AGPL-3.0-only](../LICENSE); separately identified third-party material retains its own license terms.

Components and `src/shadcn.css` are generated/vendored from shadcn/ui 4.21.3. The code-generation CLI is not a build or runtime dependency. Keep its MIT notice when editing these sources.
