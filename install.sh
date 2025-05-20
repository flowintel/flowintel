# https://github.com/flowintel/flowintel
sudo apt install -y python3-venv git screen libolm-dev librsvg2-bin wget

# install pandoc from git 
# pandoc dependencies
sudo apt install -y texlive texlive-xetex texlive-fonts-extra
wget https://github.com/jgm/pandoc/releases/download/3.7/pandoc-3.7-1-$(dpkg --print-architecture).deb
sudo dpkg -i pandoc*.deb
rm pandoc*

# Install a template for the export of notes in pdf

mkdir -p ~/.pandoc/templates
wget -q https://github.com/Wandmalfarbe/pandoc-latex-template/releases/latest/download/Eisvogel.tar.gz 
tar -xf Eisvogel.tar.gz
cp Eisvogel-*/eisvogel.latex ~/.pandoc/templates
rm -r Eisvogel.tar.gz Eisvogel-*


# install node and mmdc command
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
export NVM_DIR="$HOME/.nvm"
source $NVM_DIR/nvm.sh
nvm install node 20.19.2
# needed for docx export
npm install --prefix $HOME mermaid-filter
# needed for PDF export
npm install --prefix $HOME @mermaid-js/mermaid-cli
echo "export NVM_DIR=\"$NVM_DIR\"" >> ~/.bashrc
echo '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"  # This loads nvm' >> ~/.bashrc
# this is to include the path to our fake mmdc
echo "export PATH=\"\$PATH:$HOME/node_modules/.bin\"" >> ~/.bashrc


# proxifying mmdc so that by default any tool relying
# on it will use the proper puppeteer configuration

# we rename mmdc
mv $HOME/node_modules/.bin/mmdc $HOME/node_modules/.bin/mmdc.orig
# WARNING: this is probably not recommended to use this setting in production 
cat <<eof > $HOME/node_modules/.bin/puppeteer.json
{
    "args": [
        "--no-sandbox"
    ]
}
eof

# we create a proxy mmdc with proper puppeteer config
cat <<eof > $HOME/node_modules/.bin/mmdc
#!/bin/bash

\$HOME/node_modules/.bin/mmdc.orig -p \$HOME/node_modules/.bin/puppeteer.json \$@
eof

chmod +x $HOME/node_modules/.bin/mmdc

# initialize flowintel

# install python requirements
python3 -m venv env
. env/bin/activate
pip install -r requirements.txt
# init submodules
git submodule init && git submodule update
# make launch script executable
./launch.sh -i
