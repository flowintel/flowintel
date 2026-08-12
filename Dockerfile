# Use the official Ubuntu noble (24.04) as a parent image
FROM ubuntu:noble

# Needed to prevent tzdata to be interactive
RUN ln -fs /usr/share/zoneinfo/Europe/Luxembourg /etc/localtime

RUN apt update && apt install -y \
    sudo moreutils software-properties-common \
    git screen libolm-dev librsvg2-bin wget vim curl gnupg python3-venv python3-pip \
    libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core

# Create a dedicated user and group
RUN groupadd -r flowintel && useradd -m -g flowintel flowintel

# Copy app source
COPY . /home/flowintel/app

# Set working directory
WORKDIR /home/flowintel/app

# Replace secret and update config
COPY conf/config.py.default conf/config.py
COPY template.env .env

RUN RAND=$(tr -cd "[:alnum:]" < /dev/urandom | head -c 20) && sed "s/SECRET_KEY_ENV_VAR_NOT_SET/$RAND/" conf/config.py | sponge conf/config.py
RUN sed "s/FLOWINTEL_APP_HOST *= *'.*'/FLOWINTEL_APP_HOST = '0.0.0.0'/" conf/config.py | sponge conf/config.py


# Set proper ownership
RUN chown -R flowintel:flowintel /home/flowintel/app

# Switch to the non-root user
USER flowintel

# Install Node + Mermaid CLI
RUN <<EOF
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
. ~/.profile
nvm install node 20
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

# Install Python dependencies in a virtualenv
RUN python3 -m venv /home/flowintel/venv
ENV PATH="/home/flowintel/venv/bin:${PATH}"
RUN pip install --upgrade pip && \
    pip install -r requirements.txt --timeout 240
# Init git submodules & update
RUN git submodule init && git submodule update

# Cleanup dead screens (optional)
RUN screen -wipe || true

# Final permissions check (in case)
RUN chmod +x launch.sh bin/wait-for-it.sh bin/entrypoint.sh /home/flowintel/venv/bin/activate

ENTRYPOINT ["/home/flowintel/app/bin/entrypoint.sh"]

# Default command: interactive bash + launch
CMD ["bash", "-i", "./launch.sh", "-ld"]
