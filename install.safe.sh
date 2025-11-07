#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Safer, idempotent installer for FlowIntel development environment
# - Detects apt/dnf
# - Updates package caches
# - Installs system packages idempotently
# - Downloads and verifies artifacts more safely
# - Installs nvm/node idempotently
# - Installs npm tools locally under $HOME
# - Creates a python venv (.venv) and installs requirements using the venv's pip
# - Adds idempotent lines to ~/.bashrc
# - Provides clear logging and failures

info(){ printf '\033[1;34m[INFO]\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
err(){ printf '\033[1;31m[ERROR]\033[0m %s\n' "$*"; exit 1; }

# Configurable variables
VENV_DIR=".venv"
NODE_VERSION="${NODE_VERSION:-20.19.2}"
NVM_VERSION="v0.40.3"
PANDOC_VERSION="3.7"
# detect arch safely (dpkg may not exist on dnf systems; we'll fallback)
if command -v dpkg >/dev/null 2>&1; then
  ARCH="$(dpkg --print-architecture)"
else
  ARCH="$(uname -m)"
fi
PANDOC_DEB_URL="https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-1-${ARCH}.deb"

# helper: check command exists
require_cmd(){ command -v "$1" >/dev/null 2>&1 || err "Required command '$1' not found. Please install it and re-run."; }

# detect package manager
detect_pkg_mgr(){
  if command -v apt-get >/dev/null 2>&1; then echo "apt"; return; fi
  if command -v dnf >/dev/null 2>&1; then echo "dnf"; return; fi
  err "Unsupported package manager (need apt-get or dnf).";
}
PKG_MGR=$(detect_pkg_mgr)
info "Detected package manager: ${PKG_MGR}"

# ensure sudo available for system installations (if not root)
if [ "$EUID" -ne 0 ]; then
  if ! command -v sudo >/dev/null 2>&1; then
    err "Script requires sudo for system package installs. Install sudo or run as root."
  fi
fi

# update/install system packages idempotently
if [ "$PKG_MGR" = "apt" ]; then
  info "Updating apt cache and installing system packages..."
  sudo apt-get update -y
  sudo apt-get install -y python3-venv git screen libolm-dev librsvg2-bin wget valkey texlive texlive-xetex texlive-fonts-extra
elif [ "$PKG_MGR" = "dnf" ]; then
  info "Installing system packages via dnf..."
  sudo dnf install -y epel-release || warn "epel-release may already be installed"
  sudo dnf --refresh -y install pandoc python3 git screen libolm librsvg2 wget valkey || warn "dnf install reported warnings"
fi

# install pandoc .deb safely (only on apt systems)
if [ "$PKG_MGR" = "apt" ]; then
  if ! command -v pandoc >/dev/null 2>&1; then
    info "Downloading pandoc ${PANDOC_VERSION}"
    tmp="$(mktemp)"
    curl -fsSL -o "$tmp" "$PANDOC_DEB_URL" || { rm -f "$tmp"; err "Failed to download pandoc"; }
    info "Installing pandoc (.deb)"
    sudo dpkg -i "$tmp" || sudo apt-get install -f -y
    rm -f "$tmp"
  else
    info "pandoc already installed; skipping"
  fi
fi

# nvm + node installation (safer: download script then run)
if [ -s "$HOME/.nvm/nvm.sh" ]; then
  info "nvm already installed"
else
  info "Installing nvm ${NVM_VERSION}"
  nvm_installer_tmp="$(mktemp)"
  curl -fsSL "https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_VERSION}/install.sh" -o "$nvm_installer_tmp" || { rm -f "$nvm_installer_tmp"; err "Failed to download nvm installer"; }
  bash "$nvm_installer_tmp" || { rm -f "$nvm_installer_tmp"; err "nvm installer failed"; }
  rm -f "$nvm_installer_tmp"
fi

# Load nvm for this shell session if present
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck source=/dev/null
  . "$NVM_DIR/nvm.sh"
else
  warn "nvm not available in this shell; ensure your shell loads nvm via ~/.bashrc or similar"
fi

# install/use node version if nvm loaded
if command -v nvm >/dev/null 2>&1; then
  if ! nvm ls "$NODE_VERSION" >/dev/null 2>&1; then
    info "Installing node ${NODE_VERSION} via nvm"
    nvm install "$NODE_VERSION"
  fi
  nvm use "$NODE_VERSION" >/dev/null 2>&1 || true
else
  warn "nvm not found; skipping node/npm installs. If you have node already, ensure it's >= ${NODE_VERSION}."
fi

# ensure local npm tools installed under $HOME
export PATH="$HOME/node_modules/.bin:$PATH"
info "Installing mermaid tools locally (mermaid-filter and mermaid-cli)"
# use npm only if available
if command -v npm >/dev/null 2>&1; then
  npm install --no-audit --no-fund --prefix "$HOME" mermaid-filter @mermaid-js/mermaid-cli || warn "npm install had warnings"
else
  warn "npm not available; skipping mermaid installs"
fi

# Idempotent additions to ~/.bashrc
add_line_if_missing(){
  local line="$1" file="$2"
  touch "$file"
  grep -qxF "$line" "$file" || printf '%s\n' "$line" >> "$file"
}
add_line_if_missing "export NVM_DIR=\"$NVM_DIR\"" "$HOME/.bashrc"
add_line_if_missing '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"  # This loads nvm' "$HOME/.bashrc"
add_line_if_missing 'export PATH="$PATH:$HOME/node_modules/.bin"' "$HOME/.bashrc"

# safer mmdc wrapper: create wrapper that calls original if present
MM_BIN_DIR="$HOME/node_modules/.bin"
mkdir -p "$MM_BIN_DIR"
MMDC_ORIG="$MM_BIN_DIR/mmdc.orig"
MMDC_BIN="$MM_BIN_DIR/mmdc"

# move original if needed (only if original exists and orig not present)
if [ -x "$MM_BIN_DIR/mmdc" ] && [ ! -x "$MMDC_ORIG" ]; then
  mv "$MM_BIN_DIR/mmdc" "$MMDC_ORIG" || warn "Failed to move existing mmdc to mmdc.orig"
fi

cat > "$MM_BIN_DIR/puppeteer.json" <<'JSON'
{
  "args": [
    "--no-sandbox"
  ]
}
JSON

cat > "$MMDC_BIN" <<'SH'
#!/usr/bin/env bash
HERE="$(dirname "$0")"
ORIG="$HERE/mmdc.orig"
if [ -x "$ORIG" ]; then
  "$ORIG" -p "$HERE/puppeteer.json" "$@"
else
  echo "mmdc original binary not found; ensure @mermaid-js/mermaid-cli is installed" >&2
  exit 1
fi
SH
chmod +x "$MMDC_BIN" || warn "chmod on mmdc wrapper failed"

# Python venv and requirements
if [ ! -d "$VENV_DIR" ]; then
  info "Creating python venv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
else
  info "Using existing python venv at $VENV_DIR"
fi
# Activate venv for the rest of the script
# shellcheck disable=SC1091
. "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip setuptools wheel
if [ -f "requirements.txt" ]; then
  python -m pip install -r requirements.txt
else
  warn "requirements.txt not found; skipping pip install"
fi

# init submodules robustly
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git submodule update --init --recursive
else
  warn "Not in a git repo; skipping submodule init"
fi

# make launch script executable and run initial setup
if [ -f ./launch.sh ]; then
  chmod +x ./launch.sh || warn "chmod launch.sh failed"
  if ./launch.sh -i; then
    info "Ran ./launch.sh -i successfully"
  else
    warn "./launch.sh -i returned non-zero exit code"
  fi
else
  warn "launch.sh not found; skipping"
fi

info "install.safe.sh completed successfully"
