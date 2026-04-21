#!/usr/bin/env sh
set -eu

VERSION="${VERSION:-latest}"
REPO="${REPO:-kenzot25/nexo}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
CHECKSUM="${CHECKSUM:-}"

python_cmd() {
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "python3"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    printf '%s' "python"
    return 0
  fi
  printf '%s' ""
}

bootstrap_python() {
  echo "Python not found. Bootstrapping Python..."

  if command -v pipx >/dev/null 2>&1; then
    echo "  Python bootstrap: pipx found, skipping Python install"
    return 0
  fi

  if command -v brew >/dev/null 2>&1; then
    echo "  trying: brew install python3"
    if brew install python3; then
      echo "Python bootstrap: complete (brew)"
      return 0
    fi
  fi

  if command -v apt-get >/dev/null 2>&1; then
    echo "  trying: apt-get install python3"
    if apt-get install -y python3 python3-pip; then
      echo "Python bootstrap: complete (apt-get)"
      return 0
    fi
  fi

  if command -v dnf >/dev/null 2>&1; then
    echo "  trying: dnf install python3"
    if dnf install -y python3; then
      echo "Python bootstrap: complete (dnf)"
      return 0
    fi
  fi

  if command -v pacman >/dev/null 2>&1; then
    echo "  trying: pacman -S python"
    if pacman -S --noconfirm python; then
      echo "Python bootstrap: complete (pacman)"
      return 0
    fi
  fi

  echo "  trying: pyenv (user-space install)"
  PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
  export PYENV_ROOT
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL https://pyenv.run | sh || true
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://pyenv.run | sh || true
  fi
  if [ -f "$PYENV_ROOT/bin/pyenv" ]; then
    export PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH"
    eval "$(pyenv init -)" 2>/dev/null || true
    if pyenv install -s 3.12 && pyenv global 3.12; then
      echo "Python bootstrap: complete (pyenv)"
      return 0
    fi
  fi

  echo "error: Python could not be installed automatically." >&2
  echo "Install Python 3.10+ manually from https://www.python.org/downloads/ and re-run this script." >&2
  exit 1
}

version_no_v() {
  printf '%s' "$1" | sed 's/^v//'
}

if [ "${1:-}" = "--help" ]; then
  cat <<'EOF'
Usage: sh scripts/install.sh

Environment variables:
  VERSION     Release tag (default: latest)
  REPO        GitHub repo owner/name (default: kenzot25/nexo)
  INSTALL_DIR Install destination (default: ~/.local/bin)
  CHECKSUM    Optional SHA256 checksum override for archive verification
EOF
  exit 0
fi

resolve_version_for_repo() {
  repo="$1"
  if command -v curl >/dev/null 2>&1; then
    latest_json=$(curl -fsSL -H "User-Agent: nexo-installer" "https://api.github.com/repos/$repo/releases/latest")
  elif command -v wget >/dev/null 2>&1; then
    latest_json=$(wget -qO- --header="User-Agent: nexo-installer" "https://api.github.com/repos/$repo/releases/latest")
  else
    echo "error: curl or wget is required" >&2
    exit 1
  fi

  tag=$(printf '%s' "$latest_json" | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)
  if [ -z "$tag" ]; then
    echo "error: failed to resolve latest release tag. Set VERSION=<tag>." >&2
    exit 1
  fi
  printf '%s' "$tag"
}

asset_names() {
  os=$(uname -s)
  arch=$(uname -m)

  case "$os" in
    Darwin)
      case "$arch" in
        arm64|aarch64) echo "nexo-macos-arm64.tar.gz" ;;
        x86_64) echo "nexo-macos-x64.tar.gz" ;;
        *) echo "error: unsupported macOS arch '$arch'" >&2; exit 1 ;;
      esac
      ;;
    Linux)
      case "$arch" in
        x86_64|amd64) echo "nexo-linux-x64.tar.gz" ;;
        aarch64|arm64) echo "nexo-linux-arm64.tar.gz" ;;
        *) echo "error: unsupported Linux arch '$arch'" >&2; exit 1 ;;
      esac
      ;;
    *)
      echo "error: unsupported OS '$os'. Use scripts/install.ps1 on Windows." >&2
      exit 1
      ;;
  esac
}

download_file() {
  url="$1"
  out="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$out"
  else
    wget -qO "$out" "$url"
  fi
}

expected_sha256() {
  repo="$1"
  version_tag="$2"
  asset="$3"

  if [ -n "$CHECKSUM" ]; then
    printf '%s' "$CHECKSUM"
    return 0
  fi

  checksums_url="https://github.com/$repo/releases/download/$version_tag/checksums.txt"
  if command -v curl >/dev/null 2>&1; then
    checksums=$(curl -fsSL "$checksums_url" 2>/dev/null || true)
  else
    checksums=$(wget -qO- "$checksums_url" 2>/dev/null || true)
  fi

  if [ -z "$checksums" ]; then
    printf '%s' ""
    return 0
  fi

  sha=$(printf '%s\n' "$checksums" | awk -v target="$asset" '$2==target {print $1}' | head -n 1)
  printf '%s' "$sha"
}

verify_sha256() {
  file="$1"
  expected="$2"

  if [ -z "$expected" ]; then
    echo "  checksum: skipped (no checksums.txt or CHECKSUM override)"
    return 0
  fi

  if command -v shasum >/dev/null 2>&1; then
    actual=$(shasum -a 256 "$file" | awk '{print $1}')
  elif command -v sha256sum >/dev/null 2>&1; then
    actual=$(sha256sum "$file" | awk '{print $1}')
  else
    echo "error: shasum or sha256sum is required for checksum verification" >&2
    exit 1
  fi

  if [ "$actual" != "$expected" ]; then
    echo "error: checksum mismatch for $file" >&2
    echo "expected: $expected" >&2
    echo "actual:   $actual" >&2
    exit 1
  fi
  echo "  checksum: verified"
}

install_from_wheel_asset() {
  repo="$1"
  version_tag="$2"
  tmp_dir="$3"
  wheel_version=$(version_no_v "$version_tag")
  wheel_asset="nexo-${wheel_version}-py3-none-any.whl"
  wheel_url="https://github.com/$repo/releases/download/$version_tag/$wheel_asset"
  wheel_path="$tmp_dir/$wheel_asset"
  py=$(python_cmd)

  if [ -z "$py" ]; then
    bootstrap_python
    py=$(python_cmd)
    if [ -z "$py" ]; then
      echo "error: Python bootstrap completed but python command still not found" >&2
      exit 1
    fi
  fi

  if ! download_file "$wheel_url" "$wheel_path"; then
    echo "error: neither native binary asset nor wheel asset is available for $version_tag" >&2
    exit 1
  fi

  echo "  fallback:  wheel"
  echo "  asset:     $wheel_asset"
  echo "  download:  $wheel_url"

  expected=$(expected_sha256 "$repo" "$version_tag" "$wheel_asset")
  verify_sha256 "$wheel_path" "$expected"

  if command -v pipx >/dev/null 2>&1; then
    pipx install "$wheel_path" --force
    return 0
  fi

  venv_dir="$HOME/.local/share/nexo/venv"
  mkdir -p "$venv_dir"
  "$py" -m venv "$venv_dir"
  "$venv_dir/bin/pip" install --upgrade "$wheel_path"

  mkdir -p "$INSTALL_DIR"
  cat > "$INSTALL_DIR/nexo" <<EOF
#!/usr/bin/env sh
exec "$venv_dir/bin/python" -m nexo "\$@"
EOF
  chmod +x "$INSTALL_DIR/nexo"
}

REPO_EFFECTIVE="$REPO"
VERSION_TAG="$VERSION"
LEGACY_REPO="kenzot25/nexo"

if [ "$VERSION" = "latest" ]; then
  VERSION_TAG=$(resolve_version_for_repo "$REPO" 2>/dev/null || true)
  if [ -z "$VERSION_TAG" ] && [ "$REPO" != "$LEGACY_REPO" ]; then
    REPO_EFFECTIVE="$LEGACY_REPO"
    VERSION_TAG=$(resolve_version_for_repo "$REPO_EFFECTIVE" 2>/dev/null || true)
  fi
  if [ -z "$VERSION_TAG" ]; then
    echo "error: failed to resolve latest release tag. Set VERSION=<tag> or REPO=<owner/name>." >&2
    exit 1
  fi
fi

ASSET=""
URL=""

TMP_DIR="${TMPDIR:-/tmp}/nexo-install"
ARCHIVE=""
EXTRACT_DIR="$TMP_DIR/extract"

echo "Installing nexo"
echo "  repo:      $REPO_EFFECTIVE"
echo "  version:   $VERSION_TAG"

mkdir -p "$TMP_DIR"
rm -rf "$EXTRACT_DIR"
mkdir -p "$EXTRACT_DIR"

for candidate in $(asset_names); do
  candidate_url="https://github.com/$REPO_EFFECTIVE/releases/download/$VERSION_TAG/$candidate"
  candidate_archive="$TMP_DIR/$candidate"
  if download_file "$candidate_url" "$candidate_archive"; then
    ASSET="$candidate"
    URL="$candidate_url"
    ARCHIVE="$candidate_archive"
    break
  fi
done

if [ -z "$ARCHIVE" ] || [ ! -f "$ARCHIVE" ]; then
  echo "  native binary not found, falling back to wheel install (requires Python)..."
  install_from_wheel_asset "$REPO_EFFECTIVE" "$VERSION_TAG" "$TMP_DIR"
  echo ""
  echo "Installed: $INSTALL_DIR/nexo (via Python venv)"
  case ":$PATH:" in
    *":$INSTALL_DIR:"*)
      echo "Run: nexo --help"
      ;;
    *)
      echo "Add this directory to your PATH:"
      echo "  $INSTALL_DIR"
      echo "Then open a new terminal and run: nexo --help"
      ;;
  esac
  echo ""
  echo "Next step: nexo install"
  exit 0
fi

echo "  asset:     $ASSET"
echo "  download:  $URL"

EXPECTED=$(expected_sha256 "$REPO_EFFECTIVE" "$VERSION_TAG" "$ASSET")
verify_sha256 "$ARCHIVE" "$EXPECTED"

tar -xzf "$ARCHIVE" -C "$EXTRACT_DIR"

BIN_PATH=""
# Look for the binary in the extract dir (handles various archive structures)
if [ -f "$EXTRACT_DIR/nexo" ]; then
  BIN_PATH="$EXTRACT_DIR/nexo"
else
  BIN_PATH=$(find "$EXTRACT_DIR" -type f -name "nexo*" | head -n 1 || true)
fi

if [ -z "$BIN_PATH" ] || [ ! -f "$BIN_PATH" ]; then
  echo "error: archive does not contain 'nexo' executable" >&2
  exit 1
fi

mkdir -p "$INSTALL_DIR"
cp "$BIN_PATH" "$INSTALL_DIR/nexo"
chmod +x "$INSTALL_DIR/nexo"

echo ""
echo "Installed: $INSTALL_DIR/nexo (standalone binary - zero dependencies)"
case ":$PATH:" in
  *":$INSTALL_DIR:"*)
    echo "Run: nexo --help"
    ;;
  *)
    echo "Add this directory to your PATH:"
    echo "  $INSTALL_DIR"
    echo "Then open a new terminal and run: nexo --help"
    ;;
esac

echo ""
echo "Next step: nexo install"
