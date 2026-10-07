# Changelog

## 2.1.0

- Install `jira` as the primary command; retain `jira-cli-toolkit` and `jsup` aliases throughout v2.x.
- Legacy executables print a startup migration notice on stderr without changing JSON stdout or internal completion/update protocols.
- Native binaries now identify themselves as `jira`; release asset filenames remain compatible with existing updaters.
- Preserve configuration/profile paths and credential-store references, so v2.0 users need no auth migration.
- Update help, completion, installation and developer migration examples for the shorter command and public GitHub downloads.
- Make the GitHub repository public after reviewing reachable Git history and available Actions logs for credential leaks.

## 2.0.0

- Promote the tested v2 release candidate, including project-neutral commands, guided API-token auth, discovery, issue maintenance, native releases and verified updates.
- Record successful user acceptance of macOS Keychain migration and live credential retrieval in separate CLI invocations.
- Correct pipx recovery instructions for existing uv-backed environments: replace the managed environment with the verified wheel using the pip backend; an install-time backend override alone does not switch it.

Published as latest stable with four native binaries, wheel/sdist, manifest and checksums. Published-asset verification, actual RC-to-stable standalone update, pipx upgrade, both CLI entry points, config preservation and repeated no-op checks passed. The initial v2 release checklist is complete; generic authenticated API access remains planned for v2.5.

## 2.0.0rc1

- Introduce project-neutral resource commands and help with legacy jsup compatibility.
- Add guided API-token login, scoped-token routing, secure profiles, contexts, migration, auth health, and diagnostics.
- Add bounded safe-read retries, complete pagination, POST search, structured script errors, and uncertain-write reporting.
- Discover required creation/edit/transition fields and support typed/structured custom input.
- Add editing, assignment, relationships, attachments, comment maintenance, and richer searches.
- Add declarative templates, shell completion, CSV and selected columns.
- Add hash-locked cross-platform CI, native binaries, tag-triggered releases, and a verified installation-aware updater.

At candidate publication, live BUG acceptance, package bootstrap, publication and standalone update checks had passed. Interactive native-store acceptance and stable promotion were completed subsequently for 2.0.0.

## 0.2.0

Original support-oriented Jira Cloud CLI with flat commands and legacy configuration.
