#!/bin/bash

sudo apt-get update -y
sudo apt-get install python3-pip screen virtualenv pandoc npm texlive-full -y

virtualenv env
source env/bin/activate

# Install nvm then update or install nodejs and install mermaid-filter
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm
nvm install node
sudo npm install --global mermaid-filter

# Install a template for the export of notes in pdf
wget -q https://github.com/Wandmalfarbe/pandoc-latex-template/releases/latest/download/Eisvogel.tar.gz 
mkdir Eisvogel
tar -xf Eisvogel.tar.gz -C Eisvogel
sudo mv Eisvogel/eisvogel.latex /usr/share/pandoc/data/templates/
rm -r Eisvogel

pip install -r requirements.txt
python app.py -i
deactivate