# Upgrading from jsup 0.2 to Jira CLI Toolkit v2

Choose the guide for your migration:

- [Install/upgrade from 0.2 or RC1 to stable v2](../../migration/upgrade-to-v2.md): identify the installer, download and verify the release, recover pipx upgrades, migrate credentials, verify access, and plan rollback.
- [Migrate old commands and developer scripts](../../migration/legacy-commands.md): complete old/new command mapping, query and output changes, metadata-aware writes, identity precedence, and a script migration checklist.

The sections below are a compact reference. The detailed guides use implemented v2.0.0 commands and portable download paths.

The Python package remains `jsup`. Both `jsup` and `jira` executables ship throughout v2.x. The repository is now `User17745/jira-cli-toolkit`; old GitHub URLs redirect.

## One-time bootstrap

Version 0.2 has no updater. Download the wheel from the desired GitHub Release, verify its SHA-256 against the release manifest, then install it using the same manager that owns your existing installation:

```sh
pipx install --force /path/to/jsup-VERSION-py3-none-any.whl
uv tool install --force /path/to/jsup-VERSION-py3-none-any.whl
# Or, inside the existing Python environment:
python -m pip install --upgrade /path/to/jsup-VERSION-py3-none-any.whl
```

Choose the command for your installation. Release downloads are public; Jira credentials are not needed. Installing from a checked-out tag with `pipx install --force .` is another supported bootstrap. The package is not published to PyPI, so a bare registry upgrade is not the distribution path.

If pipx’s uv backend reports that the environment already exists during force installation, `install --force --backend pip` does **not** switch the existing environment’s recorded backend in pipx 1.14.0. Download and verify the desired wheel first, then replace the managed environment:

```sh
pipx uninstall jsup
pipx install --backend pip /path/to/jsup-VERSION-py3-none-any.whl
jsup --version
jira --version
```

Run these one at a time and stop if installation fails. Uninstalling removes the pipx environment and command shims; it preserves `~/.config/jsup/config.json`, including existing Jira credentials. V2.1 supplies `jira` and the `jira-cli-toolkit`/`jsup` compatibility commands. This recovery was verified starting from a 0.2.0 installation whose recorded backend was uv, with config bytes and permissions unchanged. Older pipx versions using the pip backend do not need the backend option. Do not manually delete the environment or overwrite its shims. `pipx reinstall jsup --backend pip` switches the backend but reuses the original recorded source; it does not necessarily install the downloaded release wheel.

All three package commands support `--version`, `help`, and `update --info`. `update --check` checks published stable releases, currently 2.1.0. A release candidate must be requested explicitly with `update --version VERSION --prerelease --check`; selecting an older version also requires `--allow-downgrade`. Checks never alter the installation. Package users receive manager-specific instructions; standalone users can install with `update --yes` after manifest/checksum and candidate checks.

## Credentials and contexts

Existing `~/.config/jsup/config.json` files remain usable. Run `config migrate` to validate the old identity, store its token in the native OS credential store, and atomically replace preferences with schema-2 profiles. If storage fails, the original file remains intact. Headless users can use a complete `JIRA_SITE`, `JIRA_EMAIL`, `JIRA_API_TOKEN` identity; explicit `--storage file` migration is available on POSIX. File storage is plaintext and is never an automatic fallback.

Approve native-store access through interactive login. Scripted macOS commands suppress Keychain dialogs; a locked or unapproved store fails explicitly. Linux native wallets are interactive only; choose environment authentication or `--storage file` for scripts. A failed native-store migration leaves the legacy config intact.

New users run `auth login --profile work`; token entry is hidden, and setup explains creation, scopes and project permissions. Scoped tokens use `--scoped` and a cloud ID/API gateway. `auth status` validates credentials; `doctor` also checks the selected project. API tokens cannot refresh automatically. Interactive replacement retains the selected site/account and never replays the original write; scripts receive an actionable failure.

Use `profile list/use/remove`, `context use --project ENG --board 123`, or interactive `context use --select`. Changing projects clears a stale default board. Root/context display works locally without opening the credential store. Logout removes the local credential; revoke the token separately at Atlassian if needed. Externally supplied credentials are unaffected.

Schema-2 identity selection is atomic: an explicit profile selects the whole identity; otherwise complete flags, complete environment identity, then the active profile are considered. Partial flags/environment identities are rejected instead of mixing site/account/token sources. Project overrides remain independent. Legacy files retain per-setting precedence until migrated.

## Command and behavior changes

The [developer command table](../../migration/legacy-commands.md#old-to-new-command-reference) maps every original command to the grouped interface. Legacy spellings remain accepted.

- New `jira` root shows local context; `jsup` root retains the dashboard. Dashboard projects must now be selected explicitly; RP/RD/BUG are never implicit.
- Grouped `issue create` discovers project/type metadata. Scripts pass a type and required fields; interactive creation guides selection. Legacy `issue-create` retains Task/default payload behavior.
- Grouped `issue transition` supports required transition fields; legacy `issue-move` retains its old interface.
- `issue list` includes Done unless `--open` is supplied. Full `--jql` ignores the default project and cannot be mixed with generated filters. Legacy `open --jql` appends an additional filter as before.
- Limits bound total fetched results across pages; `--all` follows every page. Enhanced search uses POST/cursors and no deprecated-search fallback. Paged API objects include `fetched`; exact totals are shown only when Jira supplies them.
- Callback assumptions exist only in the explicit callback template/legacy intake. Explicit template overrides take precedence, and generic template creation checks project compatibility.
- New grouped JSON commands return structured runtime errors; legacy aliases/jsup retain stderr errors. Argparse usage errors remain stderr/exit 2. `--json` and `--no-input` never permit interactive prompts or bypass deletion/update confirmation.

## Rollback and release limitations

A successful standalone update retains `.previous`; POSIX replacement rolls back automatically if post-install validation fails. Windows reports a pending helper/log path and completes after the old process exits. Do not remove a pending lock or stage while its helper is active. Preserve/remove an old backup deliberately before another update. Executable rollback does not undo a completed config migration: schema-2 preferences require v2, so keep v2 for migrated profiles or restore an independently retained legacy config securely.

Native requirements are in the manifest. CI validates its specific Linux/macOS/Windows runners; older OS versions, app-specific Jira validators, JSM customer requests, and Data Center are not certified by this release. Checksums detect corruption; publisher trust currently uses GitHub HTTPS, with no independent client-side signature/attestation verification. The initial stable v2.0.0 release is published; v2.1 introduces the shorter `jira` command and public distribution; [acceptance evidence](acceptance.md) records release/update checks and platform limitations.
