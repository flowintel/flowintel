#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

info(){ printf '\033[1;34m[INFO]\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
err(){ printf '\033[1;31m[ERROR]\033[0m %s\n' "$*"; exit 1; }

# Installation mode (default: development)
# Can be overridden with --production flag
INSTALL_MODE="development"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -p|--production)
      INSTALL_MODE="production"
      info "Installation mode: PRODUCTION"
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  -p, --production    Install for production (uses PostgreSQL, production settings)"
      echo "  -h, --help          Show this help message"
      echo ""
      echo "Default: Install for development (uses SQLite, development settings)"
      exit 0
      ;;
    *)
      err "Unknown option: $1. Use --help for usage information."
      ;;
  esac
done

if [ "$INSTALL_MODE" = "development" ]; then
  info "Installation mode: DEVELOPMENT (default)"
fi

# Install variables
VENV_DIR="env"
NODE_VERSION="${NODE_VERSION:-20.19.2}"
NVM_VERSION="v0.40.3"
PANDOC_RELEASE="3.7"
PANDOC_VERSION="3.7-1"
# Get arch safely
if command -v dpkg >/dev/null 2>&1; then
  ARCH="$(dpkg --print-architecture)"
else
  ARCH="$(uname -m)"
fi
PANDOC_DEB_URL="https://github.com/jgm/pandoc/releases/download/${PANDOC_RELEASE}/pandoc-${PANDOC_VERSION}-${ARCH}.deb"

# require_cmd: check command exists
require_cmd(){ command -v "$1" >/dev/null 2>&1 || err "Required command '$1' not found. Please install it and re-run."; }

# detect_pkg_mgr: detect apt or dnf
detect_pkg_mgr(){
  if command -v apt-get >/dev/null 2>&1; then echo "apt"; return; fi
  if command -v dnf >/dev/null 2>&1; then echo "dnf"; return; fi
  err "Unsupported package manager (need apt-get or dnf).";
}
PKG_MGR=$(detect_pkg_mgr)
info "Detected package manager: ${PKG_MGR}"

# do we have sudo? (if not root)
if [ "$EUID" -ne 0 ]; then
  if ! command -v sudo >/dev/null 2>&1; then
    err "Script requires sudo for system package installs. Install sudo or run as root."
  fi
fi

# system packages
if [ "$PKG_MGR" = "apt" ]; then
  info "Updating apt cache and installing system packages..."
  sudo apt-get update -y
  sudo apt-get install -y python3-venv git screen libolm-dev librsvg2-bin wget valkey texlive texlive-xetex texlive-fonts-extra
elif [ "$PKG_MGR" = "dnf" ]; then
  info "Installing system packages via dnf..."
  sudo dnf install -y epel-release || warn "epel-release may already be installed"
  sudo crb enable || warn "crb may already be enabled"
  sudo dnf --refresh -y install pandoc python3 git screen libolm librsvg2 wget valkey || warn "dnf install reported warnings"
fi

# pandoc
if [ "$PKG_MGR" = "apt" ]; then
  if ! command -v pandoc >/dev/null 2>&1; then
    info "Get pandoc ${PANDOC_VERSION}"
    tmp="$(mktemp)"
    curl -fsSL -o "$tmp" "$PANDOC_DEB_URL" || { rm -f "$tmp"; err "Failed to download pandoc"; }
    info "Install pandoc (.deb)"
    sudo dpkg -i "$tmp" || sudo apt-get install -f -y
    rm -f "$tmp"
  else
    info "pandoc already installed; skipping"
  fi
fi

# nvm + node
if [ -s "$HOME/.nvm/nvm.sh" ]; then
  info "nvm already installed"
else
  info "Installing nvm ${NVM_VERSION}"
  nvm_installer_tmp="$(mktemp)"
  curl -fsSL "https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_VERSION}/install.sh" -o "$nvm_installer_tmp" || { rm -f "$nvm_installer_tmp"; err "Failed to download nvm installer"; }
  bash "$nvm_installer_tmp" || { rm -f "$nvm_installer_tmp"; err "nvm installer failed"; }
  rm -f "$nvm_installer_tmp"
fi

# Load nvm
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  . "$NVM_DIR/nvm.sh"
else
  warn "nvm not available in this shell"
fi

# install/use node
if command -v nvm >/dev/null 2>&1; then
  if ! nvm ls "$NODE_VERSION" >/dev/null 2>&1; then
    info "Installing node ${NODE_VERSION} via nvm"
    nvm install "$NODE_VERSION"
  fi
  nvm use "$NODE_VERSION" >/dev/null 2>&1 || true
else
  warn "nvm not found; skipping node/npm installs. Ensure it's >= ${NODE_VERSION}."
fi

export PATH="$HOME/node_modules/.bin:$PATH"
info "Installing mermaid tools locally (mermaid-filter and mermaid-cli)"
# use npm only if available
if command -v npm >/dev/null 2>&1; then
  npm install --no-audit --no-fund --prefix "$HOME" mermaid-filter @mermaid-js/mermaid-cli || warn "npm install had warnings"
else
  warn "npm not available; skipping mermaid installs"
fi

# Update ~/.bashrc
add_line_if_missing(){
  local line="$1" file="$2"
  touch "$file"
  grep -qxF "$line" "$file" || printf '%s\n' "$line" >> "$file"
}
add_line_if_missing "export NVM_DIR=\"$NVM_DIR\"" "$HOME/.bashrc"
add_line_if_missing '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"  # This loads nvm' "$HOME/.bashrc"
add_line_if_missing 'export PATH="$PATH:$HOME/node_modules/.bin"' "$HOME/.bashrc"

# mmdc wrapper
MM_BIN_DIR="$HOME/node_modules/.bin"
mkdir -p "$MM_BIN_DIR"
MMDC_ORIG="$MM_BIN_DIR/mmdc.orig"
MMDC_BIN="$MM_BIN_DIR/mmdc"

# move original if needed
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

# init submodules
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git submodule update --init --recursive
else
  warn "Not in a git repo; skipping submodule init"
fi

# make launch script executable and run initial setup
if [ -f ./launch.sh ]; then
  chmod +x ./launch.sh || warn "chmod launch.sh failed"
  
  if [ "$INSTALL_MODE" = "production" ]; then
    info "Running production database initialization..."
    if ./launch.sh -ip; then
      info "Ran ./launch.sh -ip (production init) successfully"
    else
      warn "./launch.sh -ip returned non-zero exit code"
    fi
  else
    info "Running development database initialization..."
    if ./launch.sh -i; then
      info "Ran ./launch.sh -i (development init) successfully"
    else
      warn "./launch.sh -i returned non-zero exit code"
    fi
  fi
else
  warn "launch.sh not found; skipping"
fi

info "install.safe.sh completed successfully"
if [ "$INSTALL_MODE" = "production" ]; then
  info ""
  info "Production installation complete!"
  info "To start Flowintel in production mode, run:"
  info "  bash launch.sh -p"
  info ""
  info "Or configure as a systemd service (see installation manual)."
else
  info ""
  info "Development installation complete!"
  info "To start Flowintel, run:"
  info "  bash launch.sh -l"
fi
