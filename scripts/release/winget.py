"""Write winget manifests for a published release into OUT/manifests/u/User17745/JiraCliToolkit/VERSION.

Usage: python scripts/release/winget.py MANIFEST.json RELEASE_DATE OUT

The Windows binary's URL and SHA-256 come from the release manifest. The portable installer
exposes it as `jira`, which is the name the executable uses to choose the jira command.
"""
import json
import sys
from pathlib import Path

PACKAGE = "User17745.JiraCliToolkit"
REPO = "User17745/jira-cli-toolkit"
SCHEMA = "1.12.0"


def manifests(manifest: dict, release_date: str) -> dict[str, str]:
    if manifest.get("repository") != REPO or manifest.get("channel") != "stable":
        raise SystemExit("winget manifests are written only for stable releases of this repository.")
    windows = [a for a in manifest["artifacts"] if a.get("kind") == "binary" and a.get("os") == "windows" and a.get("arch") == "x86_64"]
    if len(windows) != 1 or len(windows[0].get("sha256", "")) != 64:
        raise SystemExit("Release manifest has no single Windows x86_64 binary.")
    version, binary = manifest["version"], windows[0]
    url = f"https://github.com/{REPO}/releases/download/{manifest['tag']}/{binary['name']}"

    def header(kind):
        return f"# yaml-language-server: $schema=https://aka.ms/winget-manifest.{kind}.{SCHEMA}.schema.json\n\n"

    return {
        f"{PACKAGE}.yaml": header("version") + f"""PackageIdentifier: {PACKAGE}
PackageVersion: {version}
DefaultLocale: en-US
ManifestType: version
ManifestVersion: {SCHEMA}
""",
        f"{PACKAGE}.installer.yaml": header("installer") + f"""PackageIdentifier: {PACKAGE}
PackageVersion: {version}
InstallerType: portable
# For a bare portable executable, winget names the PATH link after the first command.
Commands:
- jira
ReleaseDate: {release_date}
Installers:
- Architecture: x64
  InstallerUrl: {url}
  InstallerSha256: {binary['sha256'].upper()}
ManifestType: installer
ManifestVersion: {SCHEMA}
""",
        f"{PACKAGE}.locale.en-US.yaml": header("defaultLocale") + f"""PackageIdentifier: {PACKAGE}
PackageVersion: {version}
PackageLocale: en-US
Publisher: User17745
PublisherUrl: https://github.com/User17745
PublisherSupportUrl: https://github.com/{REPO}/issues
PackageName: CLI Toolkit for Jira
PackageUrl: https://jira.abhishekaggarwal.com/
License: AGPL-3.0-only
LicenseUrl: https://github.com/{REPO}/blob/{manifest['tag']}/LICENSE
ShortDescription: Independent command-line tool for Jira Cloud issues, sprints, service desks and REST APIs.
Description: |-
  The jira command lists, creates, edits and moves Jira Cloud issues, plans sprints, works with Jira Service Management requests, and calls any Jira REST endpoint with your saved profile. Output is JSON or CSV for scripts and coding agents.
  Independently maintained; not affiliated with or endorsed by Atlassian. Jira is a trademark of Atlassian.
Moniker: jira-cli-toolkit
Tags:
- cli
- jira
- jira-cloud
- automation
- agents
ReleaseNotesUrl: https://github.com/{REPO}/releases/tag/{manifest['tag']}
ManifestType: defaultLocale
ManifestVersion: {SCHEMA}
""",
    }


def main():
    source, release_date, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    manifest = json.loads(Path(source).read_text(encoding="utf-8"))
    folder = out / "manifests" / "u" / "User17745" / "JiraCliToolkit" / manifest["version"]
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in manifests(manifest, release_date).items():
        (folder / name).write_text(text, encoding="utf-8")
    print(folder)


if __name__ == "__main__":
    main()
