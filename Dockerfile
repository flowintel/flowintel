# Use the official Ubuntu Focal (20.04) as a parent image
FROM ubuntu:focal

# Needed to prevent tzdata to be interactive
RUN ln -fs /usr/share/zoneinfo/Europe/Luxembourg /etc/localtime

# Add support for Python 3.9 (deadsnakes PPA)
RUN apt update && apt install -y \
    sudo moreutils software-properties-common \
    git screen libolm-dev librsvg2-bin wget vim curl gnupg \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt update && apt install -y python3.9 python3.9-venv python3.9-distutils

# Symlink python3 and pip3 to Python 3.9
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1 && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.9 && \
    ln -s /usr/local/bin/pip /usr/bin/pip3

# Pandoc dependencies
RUN apt install -y texlive texlive-xetex texlive-fonts-extra

# Install pandoc from GitHub
RUN <<EOF
TMP=$(mktemp -d)
cd $TMP
wget https://github.com/jgm/pandoc/releases/download/3.2/pandoc-3.2-1-$(dpkg --print-architecture).deb
dpkg -i pandoc*.deb
rm -rf $TMP
EOF

# Dependencies for mermaid-cli / puppeteer
RUN apt install -y libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 libnss3 libgbm1

# Create a dedicated user and group
RUN groupadd -r flowintel && useradd -m -g flowintel flowintel

# Copy app source
COPY . /home/flowintel/app

# Set working directory
WORKDIR /home/flowintel/app

# Replace secret and update config
RUN RAND=$(tr -cd "[:alnum:]" < /dev/urandom | head -c 20) && sed "s/SECRET_KEY_ENV_VAR_NOT_SET/$RAND/" conf/config.py | sponge conf/config.py
RUN sed "s/127.0.0.1/0.0.0.0/" conf/config.py | sponge conf/config.py

# Set proper ownership
RUN chown -R flowintel:flowintel /home/flowintel/app

# Switch to the non-root user
USER flowintel

# Install pandoc Eisvogel template
RUN <<EOF
mkdir -p ~/.pandoc/templates
cd ~/.pandoc/templates
wget -q https://github.com/Wandmalfarbe/pandoc-latex-template/releases/latest/download/Eisvogel.tar.gz
tar -xf Eisvogel.tar.gz
cp Eisvogel-*/eisvogel.latex ~/.pandoc/templates
rm -r Eisvogel.tar.gz Eisvogel-*
EOF

# Install Node + Mermaid tools
RUN <<EOF
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
. ~/.profile
nvm install node 20
npm install --prefix $HOME mermaid-filter
npm install --prefix $HOME @mermaid-js/mermaid-cli
echo "export NVM_DIR=\"$NVM_DIR\"" >> ~/.bashrc
echo '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"' >> ~/.bashrc
echo "export PATH=\"\$PATH:$HOME/node_modules/.bin\"" >> ~/.bashrc
EOF

# Proxy mmdc with proper puppeteer config
RUN <<EOF
cd $HOME/node_modules/.bin
mv mmdc mmdc.orig
cat <<eof > puppeteer.json
{
    "args": [
        "--no-sandbox"
    ]
}
eof
cat <<eof > mmdc
#!/bin/bash
\$HOME/node_modules/.bin/mmdc.orig -p $(realpath $(dirname "\$0"))/puppeteer.json \$@
eof
chmod +x mmdc
EOF

# Install Python dependencies (Python 3.9 + pip)
RUN python3 --version && pip3 --version && pip3 install -r requirements.txt --timeout 240
ENV PATH="/home/flowintel/.local/bin:${PATH}"
# Init git submodules & app
RUN git submodule init && git submodule update && chmod +x launch.sh
RUN script -q -c "./launch.sh --init_db" /dev/null

# Cleanup dead screens (optional)
RUN screen -wipe || true

# Final permissions check (in case)
RUN chmod +x ./launch.sh


# Default command: interactive bash + launch
CMD ["bash", "-i", "./launch.sh", "-l"]
