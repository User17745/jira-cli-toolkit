# Upgrade jsup 0.2 to Jira CLI Toolkit 2.0

This guide upgrades an existing installation to the published stable **2.0.0** release and moves saved credentials into a named profile. For command and script changes, use the [developer migration guide](legacy-commands.md).

The Python distribution and import package remain `jsup`. V2 installs both `jsup` and `jira-cli-toolkit`; legacy command names remain available throughout v2.x. Upgrading the executable and migrating credentials are separate steps. Neither step changes Jira issues.

## 1. Identify your existing installation

Use the manager that owns your current installation:

| Installation | How to identify it | Upgrade route |
| --- | --- | --- |
| pipx | `pipx list` lists `jsup` | Install the verified release wheel through pipx |
| uv tool | `uv tool list` lists `jsup` | Install the verified wheel through `uv tool` |
| Python environment | `python -m pip show jsup` in the environment that runs the CLI | Upgrade through that same environment's Python |
| Standalone v2/RC executable | `jira-cli-toolkit update --info` reports `standalone` | Use the built-in updater |

Version 0.2 has no updater or `--version` flag. Do not start its upgrade with `jsup update`. The standalone/updater instructions below apply only after installing v2 or an RC. Preserve custom `PIPX_HOME`, `PIPX_BIN_DIR`, or uv tool directory settings when invoking your manager.

If you have a legacy config, retain a private backup before changing its schema. On macOS/Linux:

```sh
cp -p ~/.config/jsup/config.json ~/.config/jsup/config.pre-v2.json
chmod 600 ~/.config/jsup/config.pre-v2.json
```

Run this only when the legacy file exists, using a fresh backup filename so you do not overwrite an earlier pre-v2 copy. It can contain a plaintext token; keep it out of Git and shared folders. On Windows, use a private backup location with access restricted to your account. A backup of preferences after migration does not include the token held in the OS credential store.

## 2. Download and verify the stable wheel

Download these three assets from [v2.0.0](https://github.com/User17745/jira-cli-toolkit/releases/tag/v2.0.0):

- `jsup-2.0.0-py3-none-any.whl`
- `manifest.json`
- `SHA256SUMS`

The repository is private, so your GitHub account needs repository read access. This authentication is separate from your Jira token. If using GitHub CLI, authenticate the account that can access this repository, then run:

```sh
mkdir -p jira-cli-toolkit-v2
gh release download v2.0.0 --repo User17745/jira-cli-toolkit \
  --dir ./jira-cli-toolkit-v2 \
  --pattern 'jsup-2.0.0-py3-none-any.whl' \
  --pattern manifest.json --pattern SHA256SUMS
```

Use an empty download directory. Stop if downloading or verification fails. The paths below assume you remain in the directory containing `jira-cli-toolkit-v2`.

On macOS/Linux, verify the wheel's size/hash against the manifest and the manifest hash against `SHA256SUMS`:

```sh
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

root = Path('jira-cli-toolkit-v2')
manifest = json.loads((root / 'manifest.json').read_text())
assert manifest['repository'] == 'User17745/jira-cli-toolkit'
assert manifest['version'] == '2.0.0' and manifest['channel'] == 'stable'
wheel = root / 'jsup-2.0.0-py3-none-any.whl'
artifact = next(a for a in manifest['artifacts'] if a['name'] == wheel.name)
assert wheel.stat().st_size == artifact['size']
assert hashlib.sha256(wheel.read_bytes()).hexdigest() == artifact['sha256']
sums = dict(line.split('  ', 1)[::-1]
            for line in (root / 'SHA256SUMS').read_text().splitlines())
for path in (wheel, root / 'manifest.json'):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sums[path.name]
print('Verified stable wheel and manifest.')
PY
```

On Windows PowerShell, use `Get-FileHash` for the wheel and manifest, compare the wheel's hash/size with its manifest entry, and compare both hashes with `SHA256SUMS` (hexadecimal letter case does not matter):

```powershell
Get-FileHash ./jira-cli-toolkit-v2/jsup-2.0.0-py3-none-any.whl -Algorithm SHA256
Get-FileHash ./jira-cli-toolkit-v2/manifest.json -Algorithm SHA256
```

Checksums verify integrity against the downloaded release metadata. Publisher trust uses authenticated GitHub HTTPS; independent signature/attestation verification is described in the [release documentation](../../README.md#explicit-updates-and-releases).

## 3. Upgrade through your installation manager

Choose **one** route. Run each command separately and stop on failure. The Python package is not published to PyPI; a bare registry upgrade is not this release's installation route.

### pipx

```sh
pipx install --force ./jira-cli-toolkit-v2/jsup-2.0.0-py3-none-any.whl
```

If your existing environment uses pipx's **uv backend**, pipx 1.14.0 can fail with “a virtual environment already exists”. Adding `--backend pip` to that force-install command does **not** switch the existing environment's recorded backend. After confirming the verified wheel is available, recover with:

```sh
pipx uninstall jsup
pipx install --backend pip ./jira-cli-toolkit-v2/jsup-2.0.0-py3-none-any.whl
```

Manager uninstall removes the managed environment and command shims, while preserving `~/.config/jsup/config.json` and OS credential-store entries. The new installation supplies both commands. This recovery was tested from an actual uv-backed 0.2.0 installation. Do not manually delete the venv or replace its shims. `pipx reinstall jsup --backend pip` can change the backend, but reuses the original source and may reinstall an old checkout rather than this wheel.

If you already use the pip backend, including after upgrading to RC1 with the recovery above, this tested RC-to-stable command also works:

```sh
pipx install --force --backend pip ./jira-cli-toolkit-v2/jsup-2.0.0-py3-none-any.whl
```

### uv tool

```sh
uv tool install --force ./jira-cli-toolkit-v2/jsup-2.0.0-py3-none-any.whl
```

### Existing Python environment

Activate the environment that owns the old CLI, then use its Python:

```sh
python -m pip install --upgrade ./jira-cli-toolkit-v2/jsup-2.0.0-py3-none-any.whl
```

### Standalone v2/RC binary

Use the updater only when `update --info` reports `standalone`:

```sh
jira-cli-toolkit update --info
jira-cli-toolkit update --check
jira-cli-toolkit update --yes
```

Release lookup/downloads need a repository-read `GH_TOKEN` or an accessible account authenticated with `gh`. The updater verifies the compatible binary and retains `.previous`. Windows may report a pending helper/log; let it finish before checking the new executable. Package installations receive manager instructions instead of having their shims overwritten. For a first standalone installation, choose the binary matching your OS/architecture and the requirements in its release manifest.

### Verify installation

```sh
jira-cli-toolkit --version
jsup --version
jira-cli-toolkit --help
jira-cli-toolkit update --info
```

Both version commands should report `2.0.0`. Help and local update information require no Jira credentials. If the command is missing, check the manager's bin directory is on PATH and reopen your terminal. Do not reinstall through a different manager to work around PATH.

## 4. Migrate credentials once

For a saved 0.2 identity, run these directly in an interactive terminal:

```sh
jira-cli-toolkit config migrate --profile work --storage keyring
jira-cli-toolkit auth status --profile work
```

Migration validates your saved identity with Jira, reuses its token, stores it in the native OS credential store, and atomically replaces legacy preferences with schema-2 profiles. You do not need to paste a new token. Site, account and default project are retained. Failed validation/storage leaves the legacy config intact.

Approve any native credential-store prompt. On macOS, an OS password prompt uses your Mac login password. Successful status reports `authenticated: true` and `source: keyring`. Run status again from a new terminal to check persistence. During initial approval, omit `--json`, `--no-input`, and pipes: these suppress interaction.

If already on RC1/v2 with migrated profiles, **skip migration** and inspect `profile list`; use your existing profile name for status. Migration without `--profile` creates `default`, so do not assume every existing profile is called `work`. If your old credentials came only from environment variables, there is no saved identity to migrate; retain a complete environment identity or use `auth login` to create a profile.

Preferences remain at `~/.config/jsup/config.json`; schema-2 preferences contain credential references, not tokens. Native storage uses macOS Keychain, Windows Credential Manager, or a supported Linux wallet. Explicit POSIX `--storage file` stores plaintext separately in `~/.config/jsup/credentials.json` with mode 0600; it is never an automatic fallback and is unsupported on Windows. Scripted Linux wallet access is rejected; scripts use environment authentication or the explicit POSIX file option. See [script credential changes](legacy-commands.md#credentials-and-project-selection).

An invalid, expired or revoked token needs replacement. The CLI cannot refresh API tokens or infer their expiry; `expiry: unknown` is expected. If legacy migration fails authentication, use interactive `jira-cli-toolkit config init` to replace the invalid saved identity/token, then retry migration. This retains legacy plaintext storage until migration succeeds; `auth login` refuses to overwrite a legacy file. Already-migrated users replace a token with `auth login --profile work`. Setup links to token creation, hides token input, and explains permissions. Scoped tokens use `auth login --scoped` and the Atlassian API gateway; do not assume a saved legacy site/token is a scoped profile.

## 5. Select context and check access

Replace `ENG` and `123` with an accessible project and, optionally, a software board:

```sh
jira-cli-toolkit profile use work
jira-cli-toolkit context use --profile work --project ENG
jira-cli-toolkit doctor --profile work --project ENG
jira-cli-toolkit issue list --profile work --project ENG --open --limit 10
```

Set a board with `context use --profile work --project ENG --board 123`, or choose interactively with `context use --profile work --select`. Changing projects clears a stale default board. These checks read Jira data and update local context; they do not create or edit issues. A token uses your account's Jira permissions, so successful authentication does not guarantee permission to create, transition, or delete.

Your upgrade is complete when both commands report 2.0.0, status authenticates from the intended source, doctor can access the intended project, and a read-only issue query succeeds. Move scripts gradually using the [old-to-new command reference](legacy-commands.md#old-to-new-command-reference).

## Rollback and troubleshooting

| Symptom | Action |
| --- | --- |
| `jsup update` is unknown | Bootstrap 0.2 through its installation manager first |
| pipx force install reports an existing uv venv | Use the manager uninstall/fresh pip-backend install sequence above |
| Migration reports no complete saved identity | Check whether credentials were environment-only; use a complete environment identity or configure a new profile when no legacy config exists |
| Status needs OS approval | Run it interactively without JSON/pipes; a denied native store never silently becomes plaintext |
| Authentication fails | Replace invalid credentials using the reported recovery path; 401 does not prove expiry |
| Project/operation returns 403 | Check Jira account permissions and, for scoped tokens, operation scopes |
| Script rejects a partial identity | Choose an explicit profile or supply all three environment identity variables |
| Old command/output expectations differ | Follow the [developer behavior notes](legacy-commands.md#behavior-changes-that-affect-scripts) |

Standalone updates retain `.previous` for executable recovery; POSIX replacement automatically restores the old executable if post-install validation fails. Do not interfere with a pending Windows helper or remove its lock/staged files. Package rollback uses the owning manager and a verified older wheel.

**Executable rollback does not roll back credentials.** Version 0.2 cannot read schema-2 profiles. Prefer v2's supported legacy commands; if you must restore 0.2, restore a privately retained pre-v2 config as part of that rollback. Its old plaintext token must still be valid. Delete an unnecessary plaintext backup after successful migration, retaining only what your rollback policy requires.

V2 targets Jira Cloud standard issue APIs. Data Center and Service Management customer-request APIs are outside this release. Native binaries have specific OS/runtime requirements in the manifest. [Acceptance evidence](../sprints/v2-upgrade/acceptance.md) records tested platforms and remaining wallet/validator limitations.
