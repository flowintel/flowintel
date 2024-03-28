#!/bin/bash

sudo apt-get update -y
sudo apt-get install python3-pip git screen libolm-dev pandoc npm librsvg2-bin texlive-full virtualenv -y

virtualenv env
source env/bin/activate

# Install nvm then update or install nodejs and install mermaid-filter
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm
nvm install node
# sudo npm install --global mermaid-filter
sudo npm install --global @mermaid-js/mermaid-cli

# Install a template for the export of notes in pdf
wget -q https://github.com/Wandmalfarbe/pandoc-latex-template/releases/latest/download/Eisvogel.tar.gz 
mkdir Eisvogel
tar -xf Eisvogel.tar.gz -C Eisvogel
sudo mv Eisvogel/eisvogel.latex /usr/share/pandoc/data/templates/
rm -r Eisvogel
rm Eisvogel.tar.gz

pip install -r requirements.txt
pip install git+https://github.com/DavidCruciani/pandoc-mermaid-filter

git submodule init && git submodule update

python app.py -i
deactivate
