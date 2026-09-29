#!/usr/bin/env bash
# Install imprint + imprint-mcp into experiment/bin/ for CI or local runs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BIN="$ROOT/experiment/bin"
VERSION="${IMPRINT_VERSION:-1.3.1}"

os="$(uname -s | tr '[:upper:]' '[:lower:]')"
arch="$(uname -m)"
case "$arch" in
  x86_64|amd64) goarch=amd64 ;;
  arm64|aarch64) goarch=arm64 ;;
  *)
    echo "unsupported arch: $arch" >&2
    exit 1
    ;;
esac
case "$os" in
  darwin) goos=darwin; ext=tar.gz ;;
  linux) goos=linux; ext=tar.gz ;;
  *)
    echo "unsupported OS: $os (use Windows zip manually)" >&2
    exit 1
    ;;
esac

archive="imprint-${VERSION}-${goos}-${goarch}.${ext}"
url="https://github.com/SteamedBread2333/imprint/releases/download/v${VERSION}/${archive}"
sums="$BIN/SHA256SUMS"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "Downloading $url"
curl -fsSL -o "$tmp/$archive" "$url"

expected="$(grep -F "  $archive" "$sums" | awk '{print $1}')"
if [[ -z "$expected" ]]; then
  echo "no checksum for $archive in $sums" >&2
  exit 1
fi
if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "$tmp/$archive" | awk '{print $1}')"
else
  actual="$(shasum -a 256 "$tmp/$archive" | awk '{print $1}')"
fi
if [[ "$expected" != "$actual" ]]; then
  echo "checksum mismatch for $archive" >&2
  exit 1
fi

mkdir -p "$BIN"
tar -xzf "$tmp/$archive" -C "$BIN"
chmod +x "$BIN/imprint" "$BIN/imprint-mcp"
echo "Installed to $BIN/imprint and $BIN/imprint-mcp"
