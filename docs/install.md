# Native installers

The [README quick start](../README.md#get-started) installs the latest stable GitHub Release. Installers download over HTTPS, check SHA-256 checksums, and verify the binary’s version and help before placing it on PATH. They never read Jira credentials or change profiles. Checksums detect corrupted downloads; they are not publisher signatures.

## Supported platforms

| Platform | Native binary requirements | Destination |
| --- | --- | --- |
| macOS | macOS 15+, arm64 or x86_64 | `~/.local/bin/jira` |
| Linux | x86_64, glibc 2.39+, curl, sha256sum or shasum | `~/.local/bin/jira` |
| Windows | Windows 10+, x86_64, PowerShell 5.1+ | `%LOCALAPPDATA%\JiraCLI\bin\jira.exe` |

The POSIX installer prints PATH instructions; the quick-start command adds the default directory to the current shell. To make that persistent, add the export to your own shell startup file. Windows adds its directory to the user PATH without administrator access. Reopen your terminal if necessary.

Unsupported native systems, Linux ARM64, and musl systems should use the verified Python wheel with Python 3.10+. See the [manual installation and verification guide](migration/upgrade-to-v2.md). From 2.5.1 the package is published on PyPI as `jira-cli-toolkit` (`pipx install jira-cli-toolkit`); earlier releases were distributed as `jsup` wheels only.

## Pin a version or customize the directory

Download the script to inspect it before running it:

```bash
curl -fsSL https://raw.githubusercontent.com/User17745/jira-cli-toolkit/main/scripts/install.sh -o install-jira.sh
bash install-jira.sh --version 2.1.0 --install-dir "$HOME/bin"
export PATH="$HOME/bin:$PATH"
```

`JIRA_INSTALL_DIR` and `JIRA_INSTALL_VERSION` are equivalent defaults. Only stable `MAJOR.MINOR.PATCH` versions are accepted. No RC is selected by the latest installer.

PowerShell:

```powershell
Invoke-WebRequest -UseBasicParsing https://raw.githubusercontent.com/User17745/jira-cli-toolkit/main/scripts/install.ps1 -OutFile install-jira.ps1
& .\install-jira.ps1 -Version 2.1.0 -InstallDir "$env:LOCALAPPDATA\JiraCLI\bin"
```

`-NoPath` suppresses Windows PATH changes for custom integration/testing. Respect your organization’s script execution policy; the installer does not change it. Use a manual verified binary if scripts are blocked.

## Existing installations and updates

Installers refuse an existing destination, a symlink/junction installation directory, or a `jira`, `jsup`, or `jira-cli-toolkit` command on PATH. This prevents overwriting another Jira CLI or creating a second installation alongside a pipx/uv/Python-managed one. Use the [migration guide](migration/upgrade-to-v2.md) to update through the manager that owns your installation. Do not uninstall configuration or credentials to resolve a binary conflict.

For a standalone installation, use `jira update --check`, then `jira update --yes`. The updater preserves its previous binary and validates the new release; see [rollback instructions](migration/upgrade-to-v2.md). Fresh native installations contain only `jira`; Python wheels retain the two legacy aliases with stderr notices.

## Troubleshooting

- **Checksum or version mismatch:** installation stops before placing a binary. Retry, or inspect the pinned release manually. Do not skip verification.
- **Unsupported OS or architecture:** use the Python wheel rather than forcing the native installer.
- **Command not found:** add the printed installation directory to PATH, or open a new Windows terminal.
- **Existing command:** identify it with `command -v jira` (POSIX) or `Get-Command jira` (PowerShell), then use its owning installation’s updater.
- **Proxy/network failure:** downloads fail without installing. Configure your organization’s normal HTTPS proxy/trust settings; certificate verification stays enabled.

The scripts use public releases and need no GitHub or Jira token. Latest selection uses GitHub release URLs rather than the anonymous API quota. No background update check is scheduled.
