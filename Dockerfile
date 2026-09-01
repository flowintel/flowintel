# A multistage image for Flowintel
# ---------- Stage 1: build Node + Mermaid ----------
FROM debian:bookworm-slim AS node-builder
#FROM debian:trixie-slim AS node-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Node
RUN set -eux; \
    NODE_VER=20.18.0; \
    ARCH=$(dpkg --print-architecture); \
    case "$ARCH" in \
      amd64) NODE_ARCH=x64 ;; \
      arm64) NODE_ARCH=arm64 ;; \
      *) echo "Unsupported arch: $ARCH" >&2; exit 1 ;; \
    esac; \
    cd /usr/local; \
    curl -sSL "https://nodejs.org/dist/v${NODE_VER}/node-v${NODE_VER}-linux-${NODE_ARCH}.tar.xz" \
      | tar xJ --strip-components=1; \
    npm install -g mermaid-filter @mermaid-js/mermaid-cli

# ---------- Stage 2: runtime ----------
FROM debian:bookworm-slim
#FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Europe/Luxembourg

# Needed to prevent tzdata to be interactive
RUN ln -fs /usr/share/zoneinfo/$TZ /etc/localtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    gnupg \
    python3 \
    python3-venv \
    python3-pip \
    libolm-dev \
    librsvg2-bin \
    moreutils \
    software-properties-common \
    screen \
    texlive texlive-xetex texlive-fonts-extra \
    && rm -rf /var/lib/apt/lists/*

# Install pandoc from GitHub
RUN set -eux; \
    TMP=$(mktemp -d); \
    cd "$TMP"; \
    ARCH=$(dpkg --print-architecture); \
    curl -sSL -o pandoc.deb "https://github.com/jgm/pandoc/releases/download/3.7/pandoc-3.7-1-${ARCH}.deb"; \
    dpkg -i pandoc.deb; \
    rm -rf "$TMP" pandoc.deb

# Create a dedicated user and group, fixing user range ids that should be unreserved and so usable in production
RUN groupadd --gid 10000 flowintel && \
    useradd --uid 10000 --gid 10000 -m -g flowintel flowintel

WORKDIR /home/flowintel/app

# Copy Node + Mermaid from builder
COPY --from=node-builder /usr/local/bin/node /usr/local/bin/node
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node-builder /usr/local/bin/mmdc* /usr/local/bin/
COPY --from=node-builder /usr/local/bin/mermaid-filter /usr/local/bin/

# Proxy mmdc with proper puppeteer config
RUN <<EOF
set -eux
cd /usr/local/bin
mv mmdc mmdc.orig

cat > puppeteer.json <<'PUPPETEER'
{
  "args": ["--no-sandbox"]
}
PUPPETEER

cat > mmdc <<'MMDC'
#!/bin/bash
exec /usr/local/bin/mmdc.orig -p "$(realpath "$(dirname "$0")")/puppeteer.json" "$@"
MMDC

chmod +x mmdc
EOF

# Python venv - Create it as root:
## Keep the virtual env untouchable by the non privileged user
# Install Python dependencies in a virtualenv
COPY requirements.txt requirements.in /home/flowintel/app/
RUN python3 -m venv /home/flowintel/venv
ENV PATH="/home/flowintel/venv/bin:${PATH}"
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install pandoc Eisvogel template
RUN mkdir -p /home/flowintel/.pandoc/templates && \
    cd /home/flowintel/.pandoc/templates && \
    curl -sSL "https://github.com/Wandmalfarbe/pandoc-latex-template/releases/latest/download/Eisvogel.tar.gz" \
      | tar xz && \
    cp Eisvogel-*/eisvogel.latex /home/flowintel/.pandoc/templates/ && \
    rm -rf Eisvogel-* Eisvogel.tar.gz

# Copy app source later to optimize layer caching
# TODO This can further be accelerated by using the src pattern for code location and adding separate copies of requirements
# and other important folders / files from king directory
# With proper ownership
COPY --chown=flowintel:flowintel . /home/flowintel/app

# Force proper ownership
RUN chown -R flowintel:flowintel /home/flowintel/app

    # Finally, switch to the non-root user
USER flowintel

# Init git submodules & update and Final permissions check (in case)
RUN git submodule init && git submodule update && \
    chmod +x launch.sh bin/wait-for-it.sh bin/entrypoint.sh

# Cleanup dead screens (optional)
RUN screen -wipe || true

ENTRYPOINT ["/home/flowintel/app/bin/entrypoint.sh"]

# Default command: interactive bash + launch
CMD ["bash", "./launch.sh", "-ld"]
