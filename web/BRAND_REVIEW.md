# Independent website review — 7 October 2026

An independent agent reviewed the published desktop and 390px mobile site, website source, social/noscript metadata, third-party notices, and read-only credential/installer implementation. It suggested website edits; the tool, commands, repository name, installers, release assets and README were excluded from changes.

The review found the current toolkit-first identity substantially clearer. It found no reason to rename the command, replace the terminal mark, redesign the page, or treat its palette and generic board layout as evidence of infringement. The earlier official-logo cover is already absent from the current website.

## Suggestions and decisions

- [x] Replace the absolute “Any Jira Cloud project” claim with “Within your Jira permissions”; preserve the FAQ’s edition/API limitations.
- [x] Replace “Connect once” with “Choose your account and context.” Describe native storage as the login default and identify explicit environment/POSIX plaintext alternatives.
- [x] Identify the board as an original workflow illustration using sample data; identify the profile as an example. The CLI remains a terminal tool.
- [x] Include independence in hero, FAQ, metadata and JavaScript-disabled content. Identify the independent maintainer through the FAQ link.
- [x] Replace the generic apple-fruit pictogram in the macOS tab with a neutral laptop. This is a precaution against contextual ambiguity; the old pictogram was licensed Lucide artwork, not the official Apple logo.
- [x] Add Apple/Microsoft compatibility-name attribution to the existing third-party notices and make the footer link descriptive.
- [x] Preserve full font/component/icon license notices. No concrete omission was found among the inspected notices; this was not a comprehensive legal audit of every transitive package.
- [x] Keep accurate release-checksum wording. Do not imply signed-publisher authentication; changing the tool’s release verification was outside scope.

The first-fold independence line and explicit official-tool FAQ go beyond the initial agent suggestions to make the maintainer relationship easy to find. Existing typography, terminal artwork, layout, OS requirements, supported commands and planned-v2.5 labeling remain appropriate.

## Primary sources

- [Atlassian trademark guidelines](https://www.atlassian.com/legal/trademark): necessary product references, differentiated identity, naming/endorsement, website/artwork guidance. Naming examples for partners are useful design guidance, not evidence that this independent project is an authorized partner.
- [Apple third-party trademark guidelines](https://www.apple.com/legal/intellectual-property/guidelinesfor3rdparties.html): compatibility references, graphic symbols and attribution.
- [Microsoft trademark guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks): referential names, endorsement and attribution.
- [Lucide brand-logo statement](https://lucide.dev/brand-logo-statement) and [license](https://lucide.dev/license): distinction between pictograms and brand logos, artwork licensing.
- [SIL Open Font License](https://openfontlicense.org/): font license context; deployed full license text remains available in third-party notices.

This is a source-informed presentation review, not legal clearance or a finding of infringement. Source/controller attribution, command identifiers and formal trademark permissions were not adjudicated.

## Follow-up and verification

The reviewing agent checked the implemented website sources and this report in a second pass. It confirmed all meaningful findings were addressed and identified no further concrete correction. Local validation passes lint/type/build, 14 desktop/mobile production browser checks (including JavaScript disabled), 320–1440px overflow and first-fold installation, 141 CLI regressions, wheel/sdist builds and all three installed entry-point smoke checks. Only website files were modified in that initial review phase. The later, separately authorized disclaimer/license phase also changes the README, license/notice files and package metadata.

## Requested full disclaimer and repository license

The user requested a fuller closing notice for the landing page and README and selected GNU AGPL version 3. The reviewing agent drafted the three-paragraph independence/descriptive-use/intellectual-property statement now used in both places. Its non-infringement statement expresses intent and expressly does not promise legal clearance or substitute for required permission. It adds no licensing restrictions.

The repository uses **AGPL-3.0-only**, not an automatic upgrade to later licenses. The full, unmodified text was successfully downloaded from GNU’s canonical HTTPS text endpoint (`https://www.gnu.org/licenses/agpl-3.0.txt`); [SPDX’s AGPL-3.0-only entry](https://spdx.org/licenses/AGPL-3.0-only.html) verifies the identifier distinction and notice requirements. LICENSE remains verbatim, including its illustrative appendix; NOTICE and package metadata state the version-3-only choice. Original-code copyright, license, source and absence-of-warranty notices are visible; separately identified third-party terms are preserved. Existing immutable release assets are not replaced.
