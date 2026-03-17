#!/bin/zsh

# === Styling ===
RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
CYAN=$(tput setaf 6)
BOLD=$(tput bold)
RESET=$(tput sgr0)

print_step() {
  echo "${BOLD}${CYAN}➡️  $1${RESET}"
}

print_success() {
  echo "${GREEN}✅ $1${RESET}"
}

print_warning() {
  echo "${RED}⚠️  $1${RESET}"
}

# === Script starts ===

print_step "Checking for Homebrew..."
if ! command -v brew >/dev/null 2>&1; then
  print_warning "Homebrew is not installed. Please install it from https://brew.sh and re-run this script."
  exit 1
fi

print_step "Updating Homebrew and installing required packages... 🍺"
brew update
brew install python git screen wget olm librsvg

print_step "Installing Pandoc via Homebrew 📝"
brew install pandoc

# NOTE 2: LaTeX — using lightweight BasicTeX
print_step "Installing BasicTeX (lightweight LaTeX distribution) 📦"
brew install --cask basictex

# NOTE: tlmgr is not available until we add TeX binaries to the PATH
print_step "Adding TeX binaries to PATH..."

# Optional: Add to shell config permanently
echo 'export PATH="/Library/TeX/texbin:$PATH"' >> "$HOME/.zshrc"

source "$HOME/.zshrc"

print_step "Installing required LaTeX packages via tlmgr... ✨"
sudo tlmgr update --self
sudo tlmgr install collection-latexextra collection-fontsrecommended xetex

print_step "Installing Eisvogel template for PDF export 🧊"
mkdir -p ~/.pandoc/templates
wget -q https://github.com/Wandmalfarbe/pandoc-latex-template/releases/latest/download/Eisvogel.tar.gz
tar -xf Eisvogel.tar.gz
cp Eisvogel-*/eisvogel.latex ~/.pandoc/templates
rm -rf Eisvogel.tar.gz Eisvogel-*

print_step "Installing nvm and Node.js... 🧙‍♂️"
export NVM_DIR="$HOME/.nvm"
if [ ! -d "$NVM_DIR" ]; then
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi

# Reload nvm
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  . "$NVM_DIR/nvm.sh"
else
  print_warning "nvm script not found!"
  exit 1
fi

nvm install --lts
nvm use --lts

print_step "Installing Node.js tools for export 📦"
npm install --prefix "$HOME" mermaid-filter
npm install --prefix "$HOME" @mermaid-js/mermaid-cli

# NOTE 3: Add to zsh config (macOS default shell)
print_step "Adding nvm and node_modules to PATH in ~/.zshrc 🛠️"
PROFILE_FILE="$HOME/.zshrc"
{
  echo ""
  echo "# nvm config and node_modules/.bin path"
  echo "export NVM_DIR=\"$NVM_DIR\""
  echo "[ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\""
  echo "export PATH=\"\$PATH:$HOME/node_modules/.bin\""
} >> "$PROFILE_FILE"

print_success "Environment config added to $PROFILE_FILE"

print_step "Configuring mmdc proxy for Puppeteer 🕸️"
if [ -f "$HOME/node_modules/.bin/mmdc" ]; then
  mv "$HOME/node_modules/.bin/mmdc" "$HOME/node_modules/.bin/mmdc.orig"
fi

cat <<EOF > "$HOME/node_modules/.bin/puppeteer.json"
{
    "args": [
        "--no-sandbox"
    ]
}
EOF

# NOTE 4: "--no-sandbox" disables browser isolation protections — ⚠️ not for production
cat <<EOF > "$HOME/node_modules/.bin/mmdc"
#!/bin/bash
"\$HOME/node_modules/.bin/mmdc.orig" -p "\$HOME/node_modules/.bin/puppeteer.json" "\$@"
EOF

chmod +x "$HOME/node_modules/.bin/mmdc"

print_step "Creating Python virtual environment 🐍"
python3 -m venv env
source env/bin/activate

print_step "Installing Python requirements... 📄"
pip install -r requirements.txt

print_step "Initializing Git submodules... 🔁"
git submodule init && git submodule update

print_step "Making launch.sh executable and running it 🚀"
chmod +x launch_macos.sh
./launch_macos.sh -i

print_success "All done! 🎉 flowintel is now ready to use."