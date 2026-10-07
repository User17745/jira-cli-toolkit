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
