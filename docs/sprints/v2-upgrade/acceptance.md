# v2 release acceptance evidence

Evidence collected: 6–7 October 2026. Initial stable: `v2.0.0`, commit `cdb0c0f00cd719ea1c7492e40487a9594a8d5605`. Earlier candidate evidence: `v2.0.0rc1`, commit `d0640607c7e58c99d804dedb54f7871ed2e21369`.

## Automated and packaged checks

- [x] 128 deterministic parser, config/auth, transport, metadata, maintenance, template and updater tests pass locally on Python 3.14.5.
- [x] Candidate commit passes CI on Linux Python 3.10/3.14, macOS Python 3.12 and Windows Python 3.12.
- [x] Candidate commit builds wheel/sdist and native macOS arm64/x86_64, Linux x86_64 and Windows x86_64 artifacts with locked dependencies.
- [x] Native binaries pass local help/version/context/template/completion/update-discovery checks; Windows also exercises the deferred replacement helper.
- [x] Wheel-installed `jsup` and `jira-cli-toolkit` pass clean-home smoke checks.
- [x] Bash/zsh completion scripts pass shell syntax checks; fish generation is covered by deterministic tests.
- [x] Actual original 0.2.0 source is built and installed, then upgraded to the candidate in an isolated Python environment; config remains byte-identical.
- [x] Original-to-candidate pipx 1.14.0 and uv 0.11.11 upgrades, both executables, custom-directory manager discovery and manager uninstall pass in isolated homes.
- [x] pipx uv-backend force-install failure is reproduced. Follow-up recovery starts with an actual uv-backed 0.2.0 environment: force installation ignores `--backend pip`, then manager uninstall plus a fresh pip-backend install of the published RC wheel succeeds. Both entry points, pipx receipt detection, config bytes and mode 0600 are verified.

The original pipx upgrade check started with the pip backend and did not prove that an install-time backend override switches an existing uv environment. User acceptance exposed that gap. Recovery instructions are corrected in stable 2.0.0 documentation and updater guidance; the immutable published RC1 still contains the earlier guidance.

CI: [package/compatibility](https://github.com/User17745/jira-cli-toolkit/actions/runs/37496642208), [native builds](https://github.com/User17745/jira-cli-toolkit/actions/runs/37496642748).

## Live Jira checks

Writes were authorized only in BUG. Discovery was read-only in other projects.

| Project | Capability | Result |
| --- | --- | --- |
| BUG | Team-managed software | Issue-type/field discovery and issue-operation acceptance passed |
| PRD | Company-managed software | Project-specific issue-type discovery passed |
| TEST | Team-managed business | Project-specific issue-type discovery passed |
| LDSUP | Company-managed service desk | Standard issue-type discovery passed; customer-request operations are outside scope |

- [x] Scripted Bug creation with description file, UTF-8 content, label and typed custom Start date.
- [x] View/edit summary and description; add label; assign current user and unassign.
- [x] Comment add/list/edit/delete.
- [x] Discover and apply a project workflow transition.
- [x] Create and remove a directed issue relationship.
- [x] Upload/list/download/delete attachment; compare downloaded bytes with source.
- [x] Paginated search JSON and parseable selected-column CSV.
- [x] Installed-wheel CLI updates cleanup descriptions on the two test issues.
- [x] Permission preflight detects missing Delete Issues permission before creating anything; user explicitly authorizes leaving up to two issues.

**Manual cleanup:** BUG-703 and BUG-704 remain labeled `jira-cli-v2-acceptance`, with descriptions explaining that they are temporary acceptance evidence and safe to delete after review. No other issues were modified.

## Authentication and secret handling

- [x] Live login, identity status, context selection, doctor, profile listing, logout, and legacy migration pass using explicit POSIX file storage in an isolated home.
- [x] Preference files omit tokens; credential files use mode 0600; captured login/status/error output contains no submitted token. Original user config is preserved.
- [x] Native macOS scripted login fails with actionable instructions when OS access approval is needed; no silent plaintext fallback or profile write occurs.
- [x] Regression tests verify Keychain interaction suppression/restoration on failure and prevent Linux scripted wallet unlock dialogs.
- [x] User completes interactive macOS migration with `--storage keyring`; a separate `auth status --profile work` invocation reports `source: keyring` and `authenticated: True`, validating native credential persistence/retrieval and live Jira acceptance on 7 October 2026.

The macOS check used the published RC wheel installed through pipx and reused the existing token. Native interactive login/logout and wallet behavior on Linux/Windows were not live-tested; OS-specific behavior remains bounded by the documented limitations and deterministic/native build checks. No token or personal identity details are recorded in this evidence.

API-token expiry cannot be queried reliably and API tokens do not refresh. Interactive 401 replacement keeps the selected account and does not replay mutations. Linux native wallets are interactive only; scripts use environment authentication or explicit protected file storage. Windows file storage is intentionally unsupported without ACL protection.

## Published release and updater

- [x] Complete the tag-triggered release workflow, including full compatibility/native matrix and publication permissions.
- [x] Download the published eight-asset release; verify commit, manifest, sizes, SHA-256 checksums and prerelease designation.
- [x] Update an actual earlier standalone CI binary to the published candidate; confirm previous binary retention, byte-identical config and no-op checks.
- [x] Confirm the candidate is excluded from latest stable.
- [x] Rerun publication against the existing candidate; matching complete assets are preserved.
- [x] Stable tag pipeline passes all ten required compatibility/native/package/publication jobs.
- [x] Download and verify all eight stable assets, including manifest commit/version/channel, sizes and SHA-256 hashes; confirm latest stable resolves to v2.0.0.
- [x] Update the published standalone RC1 through default latest-stable discovery to 2.0.0 in an isolated home; verify exact candidate bytes, previous binary retention, schema-2 config bytes/mode 0600 preservation, and repeated no-op behavior.
- [x] Install the published stable wheel and smoke both CLI entry points; upgrade an isolated pipx/pip RC1 environment with the stable wheel and verify commands, manager receipt detection, and migrated config bytes/permissions.

Published [release candidate](https://github.com/User17745/jira-cli-toolkit/releases/tag/v2.0.0rc1); [tag-triggered pipeline](https://github.com/User17745/jira-cli-toolkit/actions/runs/37497037819) passed all ten required jobs. The downloaded wheel also passed isolated installed-entry-point checks.

Published [stable release](https://github.com/User17745/jira-cli-toolkit/releases/tag/v2.0.0); [stable tag pipeline](https://github.com/User17745/jira-cli-toolkit/actions/runs/37569094482) passed all ten required jobs. The merged main tree matches the tested PR head; [main CI](https://github.com/User17745/jira-cli-toolkit/actions/runs/37568928087) and [main native builds](https://github.com/User17745/jira-cli-toolkit/actions/runs/37568928341) passed before tagging. Release/update tests used temporary installations and did not change the user's installed RC or Keychain profile.

GitHub attestations remain optional and disabled. The repository becomes public for v2.1; enabling and verifying public-release provenance is tracked as remaining work. When enabled, publication depends on attestation success; verification uses `gh attestation verify` separately from updater integrity checks. No code-signing or notarization claim is made.

## Stable promotion

- [x] Complete the interactive native-store manual gate through user-verified macOS migration and live status retrieval.
- [x] Merge the reviewed v2 PR into main, bump the package/runtime/lock version to 2.0.0, rerun required checks, and tag the tested main commit.
- [x] Verify complete stable assets and latest-stable discovery after publication.

Required fields, duplicate names, stale metadata, disallowed operations and transition validators are additionally covered by fixtures. Live writes in company-managed/non-software projects were not authorized. App-specific validators, old OS versions, Data Center, and Service Management customer-request APIs are not certified by this candidate.

## V2.1 public command release

- [x] Package/runtime/lock versions agree on 2.1.0; 132 regressions and package/native smoke checks pass.
- [x] `jira` is the primary command; both existing aliases remain functional and print a legacy-support notice on stderr, including version/help. JSON stdout is unchanged and internal completion/update protocols remain quiet.
- [x] Review 181 reachable Git blobs, all 57 available Actions run logs and public PR metadata before switching repository visibility. Flagged URL credentials are synthetic rejection fixtures; no credential leaks detected.
- [x] Repository is public; anonymous repository/release pages, direct manifest and v2.1 wheel downloads pass. Anonymous API verification hit the shared-IP rate limit; optional GitHub auth works and is documented.
- [x] [PR #3](https://github.com/User17745/jira-cli-toolkit/pull/3), main and all required [v2.1 tag jobs](https://github.com/User17745/jira-cli-toolkit/actions/runs/37574959673) pass. Tag `v2.1.0` points to `0675d21bbb1d303e1fe5a503ec74e7b4e4918cb4`, with a tree identical to the tested PR head.
- [x] Latest stable is v2.1.0; all eight assets match manifest/checksums, sizes and commit/version/channel. The documented verifier succeeds against the published wheel and rejects corruption.
- [x] The user’s actual pipx installation upgrades to 2.1.0; all three entry points pass version/help, both legacy warnings are confirmed, and the existing `work` profile authenticates from keyring with unchanged config bytes/permissions.
- [x] An actual published v2.0 standalone binary updates via default stable discovery to `jira 2.1.0`, preserves its previous executable and config bytes/mode, and reports no update on a repeat check.

Native asset filenames and credential-store service/config paths remain unchanged for upgrade compatibility. No new Jira issues or write operations were needed. V2.5, release hardening and broader platform/transport acceptance remain future work.
