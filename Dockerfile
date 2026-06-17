# Use the official Ubuntu noble (24.04) as a parent image
FROM ubuntu:noble

# Needed to prevent tzdata to be interactive
RUN ln -fs /usr/share/zoneinfo/Europe/Luxembourg /etc/localtime

RUN apt update && apt install -y \
    sudo moreutils software-properties-common \
    git screen libolm-dev librsvg2-bin wget vim curl gnupg python3-venv python3-pip \
    texlive texlive-xetex texlive-fonts-extra # Pandoc dependencies

# Install pandoc from GitHub
RUN <<EOF
TMP=$(mktemp -d)
cd $TMP
wget https://github.com/jgm/pandoc/releases/download/3.7/pandoc-3.7-1-$(dpkg --print-architecture).deb
dpkg -i pandoc*.deb
rm -rf $TMP
EOF

# Create a dedicated user and group
RUN groupadd -r flowintel && useradd -m -g flowintel flowintel

WORKDIR /home/flowintel/app

# Copy on top only files that affect dependency resolution
COPY requirements.txt requirements.in /home/flowintel/app/

## Keep the virtual env untouchable by the non privileged user
# Install Python dependencies in a virtualenv
RUN python3 -m venv /home/flowintel/venv
ENV PATH="/home/flowintel/venv/bin:${PATH}"
RUN pip install --upgrade pip && \
    pip install -r requirements.txt --timeout 240

# Switch to the non-root user
USER flowintel

## npm installed moved upper to optimize cache layers - check that there are no strong coupling with Python code updates !
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
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
. ~/.profile
nvm install node 20
npm install --prefix $HOME mermaid-filter
npm install --prefix $HOME @mermaid-js/mermaid-cli
echo "export NVM_DIR=\"$NVM_DIR\"" >> ~/.bashrc
echo '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"' >> ~/.bashrc
echo "export PATH=\"\$PATH:$HOME/node_modules/.bin\"" >> ~/.bashrc
EOF

# We need again to be root, though not sure it is needed due to the chown done in the next steps !
USER root

# Copy app source
# TODO This can further be accelerated by using the src pattern for code location and adding separate copies of requirements
# and other important folders / files from king directory
COPY . /home/flowintel/app

# Replace secret and update config
COPY conf/config.py.default conf/config.py
COPY template.env .env

RUN RAND=$(tr -cd "[:alnum:]" < /dev/urandom | head -c 20) && sed "s/SECRET_KEY_ENV_VAR_NOT_SET/$RAND/" conf/config.py | sponge conf/config.py
RUN sed "s/FLASK_URL *= *'.*'/FLASK_URL = '0.0.0.0'/" conf/config.py | sponge conf/config.py

# Set proper ownership
RUN chown -R flowintel:flowintel /home/flowintel/app

# Switch to the non-root user
USER flowintel

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

# Init git submodules & update
# TODO maybe this would be better it is done outside the container and just copied, to avoid to keep a living git repo inside
RUN git submodule init && git submodule update

# Cleanup dead screens (optional)
RUN screen -wipe || true

# Final permissions check (in case)
RUN chmod +x launch.sh bin/wait-for-it.sh bin/entrypoint.sh

ENTRYPOINT ["/home/flowintel/app/bin/entrypoint.sh"]

# Default command: interactive bash + launch
CMD ["bash", "./launch.sh", "-ld"]
