# A multistage image for Flowintel
ARG BASE_IMAGE=ubuntu:noble # debian:bookworm-slim
                            # debian:trixie-slim

# ---------- Stage 1: build Node + Mermaid ----------
FROM ${BASE_IMAGE} AS node-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
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
    curl -fsSL "https://nodejs.org/dist/v${NODE_VER}/node-v${NODE_VER}-linux-${NODE_ARCH}.tar.xz" \
      | tar xJ --strip-components=1 -C /usr/local; \
    npm install --global mermaid-filter @mermaid-js/mermaid-cli

# ---------- Stage 2: resolve source submodules ----------
FROM ${BASE_IMAGE} AS source

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

# This must include the repository tree and .gitmodules.
COPY . .

# Init git submodules & update (public repos so no need for ssh and/or creds)
RUN set -eux; \
    git submodule sync --recursive; \
    git submodule update --init --recursive

# ---------- Stage 3: Python dependencies ----------
FROM ${BASE_IMAGE} AS python-builder

ENV DEBIAN_FRONTEND=noninteractive \
    VIRTUAL_ENV=/opt/flowintel-venv \
    PATH="/opt/flowintel-venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
        python3 \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

# Python venv - Create it as root:
## Keep the virtual env untouchable by the non privileged user
# Install Python dependencies in a virtualenv
RUN python3 -m venv "$VIRTUAL_ENV" \
    && ${VIRTUAL_ENV}/bin/python3 -m pip install --upgrade pip \
    && ${VIRTUAL_ENV}/bin/python3 -m pip install \
        --no-cache-dir \
        -r /tmp/requirements.txt

# ---------- Stage 4: Download other external packages ----------
FROM ${BASE_IMAGE} AS pkg-download

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Download pandoc from GitHub
RUN set -eux; \
    ARCH=$(dpkg --print-architecture); \
    curl -fsSL \
        -o "/tmp/pandoc.deb" \
        "https://github.com/jgm/pandoc/releases/download/3.7/pandoc-3.7-1-${ARCH}.deb";

# Download pandoc Eisvogel template
# TODO the glob -* here is a bit fragile, we may need to think of parametrising the version, the same goes for the version of pandoc above
RUN set -eux; \
    TMP=$(mktemp -d); \
    curl -fsSL "https://github.com/Wandmalfarbe/pandoc-latex-template/releases/latest/download/Eisvogel.tar.gz" \
      | tar -xz -C "$TMP"; \
    cp "$TMP"/Eisvogel-*/eisvogel.latex "/tmp/eisvogel.latex"; \
    rm -rf "$TMP";

# ---------- Stage 5: runtime ----------
FROM ${BASE_IMAGE} AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    VIRTUAL_ENV=/opt/flowintel-venv \
    TZ=Europe/Luxembourg \
    PATH="/opt/flowintel-venv/bin:${PATH}"

# Needed to prevent tzdata to be interactive
RUN ln -fs /usr/share/zoneinfo/$TZ /etc/localtime

# screen is kept for now, but we should question the idea of using screen inside the launch_docker as it smells antipatternistic
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gnupg \
        python3 \
        libolm-dev \
        librsvg2-bin \
        screen \
        texlive texlive-xetex texlive-fonts-extra \
    && rm -rf /var/lib/apt/lists/*

# Create a dedicated user and group, fixing user range ids that should be unreserved and so usable in production
RUN groupadd --gid 10000 flowintel && \
    useradd --uid 10000 --gid 10000 -m -g flowintel flowintel

WORKDIR /home/flowintel/app

# Copy Python3 venv from python-builder
COPY --from=python-builder /opt/flowintel-venv /opt/flowintel-venv

# Copy Node + Mermaid from builder
COPY --from=node-builder \
    /usr/local/bin/mmdc* \
    /usr/local/bin/mermaid-filter \
    /usr/local/bin/
COPY --from=node-builder /usr/local/bin/node /usr/local/bin/node
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules

# Import pandoc artefacts here
COPY --from=pkg-download /tmp/pandoc.deb /tmp/eisvogel.latex /tmp/

# Proxy mmdc with proper puppeteer config
RUN <<'EOF'
set -eux

cd /usr/local/bin
mv mmdc mmdc.orig

cat > puppeteer.json <<'PUPPETEER'
{
  "args": ["--no-sandbox"]
}
PUPPETEER

cat > mmdc <<'MMDC'
#!/bin/sh
set -eu
exec /usr/local/bin/mmdc.orig \
    -p /usr/local/bin/puppeteer.json \
    "$@"
MMDC

chmod 0755 mmdc
EOF

# Install pandoc
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends "/tmp/pandoc.deb"; \
    rm -rf "/tmp/pandoc.deb" /var/lib/apt/lists/*

# Install pandoc Eisvogel template
RUN mkdir -p /home/flowintel/.pandoc/templates \
    && cd /home/flowintel/.pandoc/templates \
    && cp /tmp/eisvogel.latex /home/flowintel/.pandoc/templates/ \
    && rm -rf /tmp/eisvogel.latex

# Copy app source and MISP submodule from source
# With forced proper ownership
COPY --from=source --chown=flowintel:flowintel /src/ /home/flowintel/app/

    # Make relevant script executables
RUN chmod 0755 \
        /home/flowintel/app/launch.sh \
        /home/flowintel/app/bin/wait-for-it.sh \
        /home/flowintel/app/bin/entrypoint.sh \
    && chown -R flowintel:flowintel /home/flowintel/.pandoc

# Finally, switch to the non-root user
USER flowintel

ENTRYPOINT ["/home/flowintel/app/bin/entrypoint.sh"]

# Default command: interactive bash + launch
CMD ["bash", "./launch.sh", "-ld"]
