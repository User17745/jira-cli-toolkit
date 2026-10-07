# Landing page design

Subject: Jira Cloud workflows from the terminal. Audience: developers and teams installing the `jira` command. The first screen must let a visitor choose an OS, copy the install command, or open the latest release.

Palette: paper #FAFCFF, ink #151A25, toolkit teal #087F75, board lane #DCE8F8, terminal #172336, success #89EDCA. Teal belongs to the toolkit’s terminal identity; pale board lanes reference the work being managed. The terminal is the one strong visual accent.

Type: Space Grotesk for the headline and navigation, Manrope for instructions, JetBrains Mono for commands. Self-hosted fonts. Headline left aligned; concise body lines under 70 characters.

Layout:
```
[ CLI Toolkit / for Jira           Workflows   Docs   GitHub ]
[ Your work.               | Get started                ]
[ At your command.         | macOS | Linux | Windows     ]
[ short explanation       | command + Copy             ]
[ supported workflow note | requirements / manual link ]
[ terminal + project board: interactive command examples ]
[ project-aware work      | metadata / issue example    ]
[ secure profiles         | local config / auth example ]
[ scripts and agents      | JSON / CSV example          ]
[ docs, migration, next release + compact footer          ]
```

Review before implementation: a centered banner plus three identical feature cards would obscure installation and feel like a generic SaaS template. Use an asymmetric installation-first hero and a terminal/board pairing that directly represents this CLI. Use original terminal artwork in the README; do not incorporate Atlassian’s logo into the project’s identity. Use actual supported v2.1 commands throughout; the raw API/spec flow is labeled planned for v2.5.

Interactions: accessible shadcn/ui OS and demo tabs, copy confirmation/error handling, keyboard focus, mobile navigation, reduced-motion support. No continuous animation or decorative gradients. Responsive installation panel remains directly after the headline on mobile.

Final critique: desktop gives the OS installation panel equal importance to the headline. Mobile initially pushed the command too low; shortened headline sizing and removed duplicate intro links/proof on mobile so installation fits the first fold. Enlarged terminal text, kept copy-error recovery explicit, enabled arrow-key tab activation, and hid inactive exiting panels immediately to avoid duplicate content during tab switches. Confirmed no horizontal overflow from 320px to 1440px. Self-hosted Latin font subsets reduce unnecessary font downloads; third-party notices remain available.

Branding correction plan: foreground CLI Toolkit, with a smaller “for Jira” compatibility reference. Keep the terminal command literal in code examples, use “Install the CLI” for the action, and make independence explicit above the fold and in a readable footer notice. Replace the supplied logo-bearing banner with an original SVG terminal cover. Retain the installation-first layout, font roles and responsive interactions. Review: a disclaimer alone would leave the oversized product wordmark and logo ambiguous; change the identity and artwork together.

Branding critique: desktop and 320–760px mobile layouts retain readable identity and first-fold installation. The compatibility reference is smaller than CLI Toolkit, the terminal artwork uses our own teal mark, and the footer notice stays readable on mobile. Text-only social metadata avoids republishing the earlier logo-bearing cover.

Independent-agent review pass: preserve the toolkit identity and installation-first layout. Add a short, readable non-affiliation line near the hero, qualify Cloud/storage claims, and identify the board/profile as sample illustrations. Carry independence into search/social/noscript copy and make third-party notices easy to find. Keep the existing teal/ink palette, font roles and command examples. Review before editing: this is a clarity pass, not a new brand; generic Kanban shapes and a standard licensed fruit icon do not establish infringement. Do not change the tool, its aliases, installation scripts or repository.

Review-pass critique: explicit independence remains readable before installation on mobile, and the command block still fits the first fold. A neutral laptop preserves OS recognition, while original-illustration/sample labels distinguish mock data from a product screenshot. The agent’s follow-up found no further concrete correction. The notices are easier to find without adding a long legal footer.

Disclaimer/license pass: retain the short first-fold independence line and expand the closing notice into three readable paragraphs drafted by the reviewing agent. Use a quiet 17px heading, 13px body, and an 80ch maximum line length; separate the license paragraph with a single rule. Source, license, warranty and third-party notices are discoverable at the end. Review: this provides the requested complete statement without turning the installation flow into a legal interstitial. Preserve current typography/palette and mobile installation.

## DX-first redesign (October 2026)

Brief: re-imagine the page for any Jira Cloud developer, “very DX first”. ENG and the sample people are examples, not a target team.

Concept: the page behaves like the CLI. The headline is a command, `$ jira issue list --open`, and the terminal beside it shows that command’s output. Everything after is what a developer checks before adopting a tool: how it behaves in scripts, what commands exist, how to set it up, and what it doesn’t do yet.

Palette: paper #EEF2EF, ink #0E2A27, toolkit teal #087F75 (kept from the mark), terminal pane #0D3A35. Inside the terminal, status colors come from the CLI’s own `STATUS_STYLE`: cyan #7FD3E6 for new, amber #F0C454 for in progress, green #93D69A for done, red #FF8F80 for errors.

Type: Martian Mono (variable, width 75–112.5%) only for text a person types or the CLI prints. The headline is set at 112.5% width and sized to stay on one line; below 720px it switches to 75% width instead of wrapping. Atkinson Hyperlegible Next for prose. They replace Space Grotesk, Manrope and JetBrains Mono. Neither mono face ships box-drawing glyphs, so Rich tables and panels render as HTML tables and bordered blocks instead of ASCII art. `✓` and `→` fall back to the system mono.

Layout:
```
[ CLI Toolkit for Jira        Scripting  Commands  Docs  GitHub  [Install the CLI] ]
[ $ jira issue list --open   (one line, full width)                               ]
[ what it is, independence, permissions | sandbox terminal (sample data)          ]
[ install tabs + copy                   | Try: runnable example commands          ]
[ Predictable enough to script: exit codes 0/1/2/130 with Run buttons | JSON error shape, rules ]
[ Every command, read from the parser: filter + grouped list, each opens real help ]
[ 1 install  2 auth login  3 context use + issue list   (numbered: a real sequence) ]
[ Before you install: limits and FAQ                                               ]
[ footer links + full independence and license notice                             ]
```

Sandbox: commands run against sample data in the browser; nothing reaches Jira, and the label says so. The parser is driven by `commands.json` from the real argparse tree, and help/usage/error text is a port of argparse’s formatter. During development all 75 `--help` texts and 31 argparse error cases were compared byte for byte against the installed CLI. Runtime messages (unknown profile, `--to` choices, 404 hints, JSON error shape, `Moved KEY → Status`, `✓ {...}` dict output) were copied from the source. Writes are simulated only for transition and assign, so later `issue list` calls reflect them. Commands without sample data say so in a sandbox note rather than inventing output. Keyboard: Tab completes, arrows recall history, Ctrl+C gives exit 130, Ctrl+L clears, and Escape releases Tab so keyboard users aren’t trapped. Output is announced through a polite live region; the input sits outside it.

Review before implementation, against generic defaults: rejected an auto-typing hero (motion nobody asked for), a dark page with an acid accent (a stock “developer” look), ALL-CAPS man-page headings, and feature cards. Motion happens only in response to running a command. Exit codes, the parser-generated reference and the honest limits are the DX proof. Slogans were cut.

Critique from screenshots: the first headline broke between “issue” and “list”, so it is now sized from the container to stay on one line. At 1024px a two-column hero squeezed the issue table, so the hero stacks below 1120px. The initial terminal auto-scrolled past its own first command on mobile, so it now opens at the top. Status cells wrapped (“In / Progress”), so only prose columns wrap, as Rich does. `130` wrapped in the exit table, and three columns crowded the Run buttons, so the table now has two columns. The placeholder “type jira --help” read as a typed `type` command, so it is now set in italic sans. Removed one accessory: a “Last exit code” readout that repeated each command’s own `exit N` line.

Constraints retained from the brand and legal reviews: CLI Toolkit identity first with a smaller “for Jira”, the independence line above the fold, the full three-paragraph notice and AGPL-3.0-only paragraph, the maintainer and permissions FAQ answers, the OS credential-store wording, v2.5 `jira api`/`--spec` labeled as planned, third-party notices (now with Martian Mono and Atkinson Hyperlegible Next), noscript content, and no og:image.

## Terminal-first shadcn redesign (October 2026)

Feedback on the first DX pass: the terminal mattered most but scrolled out of view, and clicking an example scrolled the page to it. It didn’t look or feel like a terminal, nothing showed that it accepted input, and the paper/teal palette with Martian Mono and Atkinson read as unpolished. The user asked for shadcn/ui with a Vercel-like look. The exit-code examples that end in 1 and 2 also read as broken, because nothing said they fail on purpose.

Direction: shadcn/ui on its neutral palette, with Geist and Geist Mono. The page is white with near-black type, hairline borders and black primary buttons. The only dark surface is the terminal, plus code samples that show terminal output.

Layout: from 1100px the page has two columns. Content scrolls on the left. The terminal sits in a sticky right column that fills the viewport below the header. Every runnable thing on the page (examples, exit-code rows, the command reference) types its command into that terminal, so the page never scrolls to it. Below 1100px the terminal docks to the bottom of the screen as a collapsed bar labeled “Sandbox terminal”. Running anything opens it as a sheet. On small screens the hero puts installation right after the headline and independence line, so the install command clears the dock on a 390×664 screen.

Terminal: window chrome with neutral dots (no traffic-light colors) and a “sandbox — zsh — sample data” title. A `~ $` prompt turns red after a failed command, and failed commands show `exit N` on the right, like a zsh right prompt. A blinking block cursor is drawn over a hidden input that still handles real typing and caret movement. Fish-style ghost suggestions come from history; the first one is `jira --help`, and → accepts it. Sandbox notes print as `#` comments. A status line shows key hints and the last exit code. Commands triggered from the page type themselves in before running, and appear instantly under reduced motion. The blink stops under reduced motion too.

Exit-code rows now say what each example does and which code it exits with, for example “asks for an issue that doesn’t exist, so Jira answers 404, so it exits 1”.

Critique: the unfocused hollow cursor was too faint to signal input, so the cursor is now always solid. A wrapped command split from its prompt on mobile, and the status line clipped the exit code. Both are fixed. The shadcn outline button’s border lost to the base `border-transparent` because the project’s `cn` doesn’t merge Tailwind classes, so the outline border is marked important.

Brand and legal constraints are unchanged: CLI Toolkit first with a smaller “for Jira” at every width, the independence line above the fold, the full IP and AGPL-3.0-only notice, the FAQ wording, v2.5 labeled as planned, sample data labeled in the terminal title and the “Try it” section, the noscript content, and no og:image. Third-party notices list Geist and Geist Mono. The favicon mark is now black.

## Polish: dark mode, install block, mark and ASCII field (October 2026)

Feedback: the version pill above the headline looked cheap; the install block broke the URL mid-word under a redundant “Terminal” header; and the user asked for dark mode, a better favicon and a scroll-aware ASCII background. In a footer screenshot, the sticky terminal was sliding under the translucent header at the end of the page. That happened because the sticky column ended with `<main>` while the footer sat outside the grid.

- Removed the pill. The headline opens the page.
- The install block is a small dark terminal. Each command has its own line with a `$` prompt, or `PS>` for PowerShell, drawn by CSS so the copied text matches what’s shown exactly. Lines scroll sideways instead of breaking. The code stops short of the icon-only copy button and fades out under a mask, so text never collides with the button.
- The footer is now inside the scrolling column, so the terminal stays pinned below the header all the way to the end of the page.
- Dark mode uses shadcn’s `.dark` tokens. An inline script in `index.html` applies the saved choice, or the system setting, before first paint. The header toggle saves an explicit choice; without one, the page follows system changes. There are theme-color metas for both schemes. The terminal and install block stay dark in both themes.
- Mark: a chevron followed by the sandbox’s green block cursor, on a near-black tile. The favicon is SVG with a subtle edge for dark tab bars. The Apple touch icon is a full-bleed 180px PNG, and iOS rounds it.
- ASCII field: a fixed canvas behind the content, faded out toward the bottom. Three interfering waves, one of them radial around a drifting center, pick characters from a density ramp. Scrolling moves the field at a third of the page speed and shifts the wave phases, so it visibly answers the scroll. Each row is a single `fillText` call. It runs at about 15 frames a second, pauses in hidden tabs, and under reduced motion draws once and ignores scroll. It is `aria-hidden`, at 8% (light) or 6% (dark) opacity.
