#!/usr/bin/env bash
# Install a verified stable native Jira CLI. Never reads Jira credentials.
set -euo pipefail
repo='User17745/jira-cli-toolkit'
install_dir="${JIRA_INSTALL_DIR:-$HOME/.local/bin}"
version="${JIRA_INSTALL_VERSION:-}"
fail() { printf 'jira installer: %s\n' "$*" >&2; exit 1; }
while (($#)); do
  case "$1" in
    --install-dir) (($# >= 2)) || fail '--install-dir needs a path'; install_dir="$2"; shift 2 ;;
    --version) (($# >= 2)) || fail '--version needs a stable version'; version="$2"; shift 2 ;;
    --help) printf 'Usage: bash install.sh [--install-dir PATH] [--version 2.1.0]\n'; exit 0 ;;
    *) fail "Unknown option: $1" ;;
  esac
done
command -v curl >/dev/null || fail 'Install curl first, or download a binary from GitHub Releases.'
case "$(uname -s)" in
  Darwin)
    os=macos
    major="$(sw_vers -productVersion | cut -d. -f1)"
    [[ "$major" =~ ^[0-9]+$ ]] && ((major >= 15)) || fail 'Native binaries require macOS 15+. Use the Python wheel on older systems.'
    ;;
  Linux)
    os=linux
    libc="$(getconf GNU_LIBC_VERSION 2>/dev/null || true)"
    [[ "$libc" == glibc\ * ]] || fail 'Native Linux binaries require glibc 2.39+. Use the Python wheel on musl systems.'
    libc_version="${libc#glibc }"
    printf '%s\n' "$libc_version" | awk -F. '{exit !(($1 > 2) || ($1 == 2 && $2 >= 39))}' || fail 'Native Linux binaries require glibc 2.39+. Use the Python wheel on older systems.'
    ;;
  *) fail 'This installer supports macOS and Linux. Use install.ps1 for Windows.' ;;
esac
case "$(uname -m)" in
  arm64|aarch64) arch=arm64 ;;
  x86_64|amd64) arch=x86_64 ;;
  *) fail 'Unsupported native architecture. Use the Python wheel.' ;;
esac
[[ "$os/$arch" != linux/arm64 ]] || fail 'No Linux ARM64 native binary is published. Use the Python wheel.'
if command -v sha256sum >/dev/null; then
  hash_file() { sha256sum "$1" | awk '{print $1}'; }
elif command -v shasum >/dev/null; then
  hash_file() { shasum -a 256 "$1" | awk '{print $1}'; }
else
  fail 'A SHA-256 tool (sha256sum or shasum) is required.'
fi
if [[ -n "$version" ]]; then
  tag="v${version#v}"
else
  resolved="$(curl --proto '=https' --proto-redir '=https' --tlsv1.2 -fsSL --connect-timeout 15 --max-time 120 -o /dev/null -w '%{url_effective}' "https://github.com/$repo/releases/latest")"
  prefix="https://github.com/$repo/releases/tag/"
  [[ "$resolved" == "$prefix"* ]] || fail 'Unexpected latest-release URL. Use the manual release page.'
  tag="${resolved#"$prefix"}"
fi
[[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail 'Choose a stable semantic version, for example 2.1.0.'
expected_version="${tag#v}"
target="$install_dir/jira"
[[ ! -e "$target" && ! -L "$target" ]] || fail "Already installed at $target. Use jira update --yes, or update through its owning package manager."
for command_name in jira jsup jira-cli-toolkit; do
  existing="$(command -v "$command_name" || true)"
  [[ -z "$existing" ]] || fail "A $command_name command already exists at $existing. Update its owning installation instead of creating a conflicting command."
done
[[ ! -L "$install_dir" ]] || fail 'The installation directory must not be a symbolic link.'
work="$(mktemp -d)"
staged=''
cleanup() { rm -rf "$work"; [[ -z "$staged" ]] || rm -f "$staged"; }
trap cleanup EXIT
base="https://github.com/$repo/releases/download/$tag"
asset="jira-cli-toolkit-$os-$arch"
fetch() { curl --proto '=https' --proto-redir '=https' --tlsv1.2 -fsSL --connect-timeout 15 --max-time 180 --retry 2 "$base/$1" -o "$work/$1"; }
printf 'Downloading Jira CLI %s for %s/%s…\n' "$expected_version" "$os" "$arch"
fetch SHA256SUMS
fetch manifest.json
fetch "$asset"
verify() {
  local name="$1" expected count actual
  count="$(awk -v name="$name" '$2 == name {n++} END {print n+0}' "$work/SHA256SUMS")"
  [[ "$count" == 1 ]] || fail "Missing or duplicate checksum for $name."
  expected="$(awk -v name="$name" '$2 == name {print $1}' "$work/SHA256SUMS" | tr 'A-F' 'a-f')"
  [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || fail "Invalid checksum for $name."
  actual="$(hash_file "$work/$name")"
  [[ "$actual" == "$expected" ]] || fail "Checksum mismatch for $name. Nothing was installed."
}
verify manifest.json
verify "$asset"
chmod 755 "$work/$asset"
reported="$("$work/$asset" --version)"
[[ "$reported" == "jira $expected_version" ]] || fail 'The verified binary reports an unexpected version.'
"$work/$asset" --help >/dev/null
mkdir -p "$install_dir"
staged="$(mktemp "$install_dir/.jira-install.XXXXXX")"
cp "$work/$asset" "$staged"
chmod 755 "$staged"
mv -n "$staged" "$target"
[[ ! -e "$staged" ]] || fail 'Another installation appeared. Nothing was overwritten.'
staged=''
printf 'Installed %s at %s\n' "$reported" "$target"
case ":$PATH:" in
  *":$install_dir:"*) ;;
  *) printf 'Add this directory to your shell PATH: %s\n' "$install_dir" ;;
esac
printf 'Next: jira auth login --profile work\nManual releases: https://github.com/%s/releases/latest\n' "$repo"
