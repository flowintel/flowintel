# Use the official Ubuntu Focal (20.04) as a parent image
FROM ubuntu:focal


# Needed to prevent tzdata to be interactive
RUN ln -fs /usr/share/zoneinfo/Europe/Luxembourg /etc/localtime
# Utils needed by installer
RUN apt update && apt install -y sudo moreutils python3
# apt commands from install.sh so that docker can cache images
# of long apt installation steps
RUN apt install -y python3-pip python3-venv git screen libolm-dev librsvg2-bin wget vim

# install pandoc from git 
# pandoc dependencies
RUN apt install -y texlive texlive-xetex texlive-fonts-extra
RUN <<EOF
TMP=$(mktemp -d)
cd $TMP
wget https://github.com/jgm/pandoc/releases/download/3.2/pandoc-3.2-1-$(dpkg --print-architecture).deb
dpkg -i pandoc*.deb
rm -rf $TMP
EOF

# dependencies needed for mermaid-cli and more specifically puppeteer running under the hood
RUN apt install -y libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 libnss3 libgbm1

# put here all flowintel-cm related install
# this way all above steps can be cached by docker build

# Create a dedicated user and group
RUN groupadd -r flowintel-cm && useradd -m -g flowintel-cm flowintel-cm

# Copy the current directory contents into the container at /app
COPY . /home/flowintel-cm/app

# Set the working directory inside the container
WORKDIR /home/flowintel-cm/app

# Configuring flowintel-cm to be used in Docker
RUN RAND=$(tr -cd "[:alnum:]" < /dev/urandom | head -c 20) && sed "s/SECRET_KEY_ENV_VAR_NOT_SET/$RAND/" conf/config.py | sponge conf/config.py
RUN sed "s/127.0.0.1/0.0.0.0/" conf/config.py | sponge conf/config.py

# Change ownership of the /app directory to the appuser
RUN chown -R flowintel-cm:flowintel-cm /home/flowintel-cm/app

# Switch to the non-root user
USER flowintel-cm

# Install a template for the export of notes in pdf
RUN <<EOF
mkdir -p ~/.pandoc/templates
cd ~/.pandoc/templates
wget -q https://github.com/Wandmalfarbe/pandoc-latex-template/releases/latest/download/Eisvogel.tar.gz 
tar -xf Eisvogel.tar.gz eisvogel.latex
EOF

# install node and mmdc command
RUN <<EOF
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
. ~/.profile
nvm install node 20
# needed for docx export
npm install --prefix $HOME mermaid-filter
# needed for PDF export
npm install --prefix $HOME @mermaid-js/mermaid-cli
echo "export NVM_DIR=\"$NVM_DIR\"" >> ~/.bashrc
echo '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"  # This loads nvm' >> ~/.bashrc
# this is to include the path to our fake mmdc
echo "export PATH=\"\$PATH:$HOME/node_modules/.bin\"" >> ~/.bashrc
EOF

# proxifying mmdc so that by default any tool relying
# on it will use the proper puppeteer configuration
RUN <<EOF
cd $HOME/node_modules/.bin
# we rename mmdc
mv mmdc mmdc.orig
# WARNING: this is probably not recommended to use this setting in production 
cat <<eof > puppeteer.json
{
    "args": [
        "--no-sandbox"
    ]
}
eof

# we create a proxy mmdc with proper puppeteer config
cat <<eof > mmdc
#!/bin/bash

\$HOME/node_modules/.bin/mmdc.orig -p $(realpath $(dirname "\$0"))/puppeteer.json \$@
eof

chmod +x mmdc
EOF

# initialize flowintel-cm
RUN <<EOF
# install python requirements
python3 -m venv env
. env/bin/activate
pip install -r requirements.txt
# init submodules
git submodule init && git submodule update
# make launch script executable
chmod +x launch.sh
./launch.sh -i
EOF

# Specify the command to run on container start
# Example: if you have a script called run.sh in the current directory
RUN chmod +x ./launch.sh

# we need to set -i so that bash loads .bashrc where we source nvm
# and where we export PATH to our tools
CMD ["bash", "-i", "./launch.sh", "-l"]

# If your application exposes a port, you can specify it using the EXPOSE instruction
EXPOSE 7006