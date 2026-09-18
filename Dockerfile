# A multistage image for Flowintel
# BASE_IMAGE options: ubuntu:noble, debian:bookworm-slim, debian:trixie-slim
# For Prod, you may want add the sha256 as follow:
# ARG BASE_IMAGE=ubuntu:noble@sha256:<digest>
ARG BASE_IMAGE=ubuntu:noble
ARG NODE_VER=24.21.0
ARG PANDOC_VER=3.7.0.2
ARG PANDOC_PATCH=1
ARG EISVOGEL_VER=3.4.0

# ---------- Stage 1: build Node + Mermaid ----------
FROM ${BASE_IMAGE} AS node-builder

ARG NODE_VER

ENV DEBIAN_FRONTEND=noninteractive

RUN set -eux \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        xz-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*;

# Install Node
RUN set -eux; \
    ARCH=$(dpkg --print-architecture); \
    case "$ARCH" in \
      amd64) NODE_ARCH=x64 ;; \
      arm64) NODE_ARCH=arm64 ;; \
      *) echo "Unsupported arch: $ARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VER}/node-v${NODE_VER}-linux-${NODE_ARCH}.tar.xz" \
      | tar xJ --strip-components=1 -C /usr/local; \
    npm install --global mermaid-filter @mermaid-js/mermaid-cli;

# ---------- Stage 2: resolve source submodules ----------
FROM ${BASE_IMAGE} AS source

ARG DEBIAN_FRONTEND=noninteractive

RUN set -eux \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*;

WORKDIR /src

# This must include the repository tree and .gitmodules.
COPY . .

# Init git submodules & update (public repos so no need for ssh and/or creds)
RUN set -eux; \
    git submodule sync --recursive; \
    git submodule update --init --recursive; \
    git rev-parse HEAD > /src/GIT_COMMIT; \
    git describe --tags --always > /src/GIT_VERSION 2>/dev/null || true;

# Strip Git metadata now that submodules are resolved —
# runtime never needs .git, only the resulting file tree.
RUN set -eux \
    && find /src -name ".git" -maxdepth 3 -exec rm -rf {} + \
    && rm -f /src/.gitmodules /src/.gitignore;

# ---------- Stage 3: Python dependencies ----------
FROM ${BASE_IMAGE} AS python-builder

ENV DEBIAN_FRONTEND=noninteractive \
    VIRTUAL_ENV=/opt/flowintel-venv \
    PATH="/opt/flowintel-venv/bin:${PATH}"

RUN set -eux \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
        python3 \
        python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*;

COPY requirements.txt /tmp/requirements.txt

# Python venv - Create it as root:
## Keep the virtual env untouchable by the non privileged user
# Install Python dependencies in a virtualenv
RUN set -eux \
    && python3 -m venv "$VIRTUAL_ENV" \
    && ${VIRTUAL_ENV}/bin/python3 -m pip install --upgrade pip \
    && ${VIRTUAL_ENV}/bin/python3 -m pip install \
        --no-cache-dir \
        -r /tmp/requirements.txt;

# ---------- Stage 4: Download other external packages ----------
FROM ${BASE_IMAGE} AS pkg-download

ARG PANDOC_VER
ARG PANDOC_PATCH
ARG EISVOGEL_VER

ENV DEBIAN_FRONTEND=noninteractive

RUN set -eux \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*;

# Download pandoc from GitHub
RUN set -eux; \
    ARCH=$(dpkg --print-architecture); \
    curl -fsSL \
        -o "/tmp/pandoc.deb" \
        "https://github.com/jgm/pandoc/releases/download/${PANDOC_VER}/pandoc-${PANDOC_VER}-${PANDOC_PATCH}-${ARCH}.deb";

# Download pandoc Eisvogel template
# Decision: We fix to 3.4.0 version of the template for avoiding the migration to sourcesans.tty before Ubuntu/Debian are ready
RUN set -eux; \
    TMP=$(mktemp -d); \
    curl -fsSL "https://github.com/Wandmalfarbe/pandoc-latex-template/releases/download/v${EISVOGEL_VER}/Eisvogel-${EISVOGEL_VER}.tar.gz" \
      | tar -xz -C "$TMP"; \
    cp "$TMP"/Eisvogel-3.4.0/eisvogel.latex /tmp/eisvogel.latex; \
    rm -rf "$TMP";

# ---------- Stage 5: runtime ----------
FROM ${BASE_IMAGE} AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    VIRTUAL_ENV=/opt/flowintel-venv \
    TZ=Europe/Luxembourg \
    PATH="/opt/flowintel-venv/bin:${PATH}"

# Needed to prevent tzdata to be interactive
RUN ln -fs /usr/share/zoneinfo/$TZ /etc/localtime

# We have 2 apt-get install RUN in the runtime layer, we clean only on the last one to reduce processing
RUN set -eux \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        # Essential to send signed emails
        gnupg \
        #
        # end-to-end encryption (Matrix for example)
        libolm-dev \
        # render svg diagrams in PDF reports
        librsvg2-bin \
        # screen is kept for now, but we should question the idea of using screen inside the launch_docker as it smells antipatternistic
        # Currently it is required by launch.sh: runs startNotif.py and startMispSync.py (as detached background sessions alongside gunicorn)
        # The alternative would be to have different service but this is an architectural implication for Flowintel
        screen \
        #
        # LaTeX
        texlive-latex-extra \
        texlive-xetex \
        texlive-fonts-recommended \
        texlive-fonts-extra \
        texlive-lang-cjk \
        # baseline LaTeX PDF hygiene:
        # guarantee scalable, embeddable outline fonts are available as a fallback,
        # even when your body text is overridden to Source Sans
        lmodern;

# Create a dedicated user and group, fixing user range ids that should be unreserved and so usable in production
RUN set -eux \
    && groupadd --gid 10000 flowintel \
    && useradd --uid 10000 --gid 10000 -m -g flowintel flowintel;

WORKDIR /home/flowintel/app

# Copy Node + Mermaid from builder
COPY --from=node-builder \
    /usr/local/bin/mmdc* \
    /usr/local/bin/mermaid-filter \
    /usr/local/bin/
COPY --from=node-builder /usr/local/bin/node /usr/local/bin/node
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules

# Copy Python3 venv from python-builder
COPY --from=python-builder /opt/flowintel-venv /opt/flowintel-venv

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

# Install pandoc and Eisvogel template
RUN --mount=type=bind,from=pkg-download,source=/tmp/pandoc.deb,target=/tmp/pandoc.deb \
    --mount=type=bind,from=pkg-download,source=/tmp/eisvogel.latex,target=/tmp/eisvogel.latex \
    set -eux \
    && apt-get install -y --no-install-recommends /tmp/pandoc.deb \
    && mkdir -p /home/flowintel/.pandoc/templates \
    && cp /tmp/eisvogel.latex /home/flowintel/.pandoc/templates/ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*;

# Copy app source and MISP submodule from source
# With forced proper ownership
COPY --from=source --chown=flowintel:flowintel /src/ /home/flowintel/app/

# Make relevant script executables and link the Python3 venv to make it reachable from the legacy location
RUN set -eux \
    && chown flowintel:flowintel /home/flowintel/app \    
    && chmod 0755 \
        /home/flowintel/app/launch.sh \
        /home/flowintel/app/bin/wait-for-it.sh \
        /home/flowintel/app/bin/entrypoint.sh \
    && chown -R flowintel:flowintel /home/flowintel/.pandoc \
    && ln -s /opt/flowintel-venv /home/flowintel/venv;

# Some people may want this hardening as a 1st step towards distroless image (before even a noshell variant)
# But this will blind the Vulnerability scanners...
# Might be acceptable with the SBOM output proposed in the Makefile
# RUN apt-get purge -y --auto-remove apt \
#     && rm -rf /var/lib/apt /var/cache/apt /etc/apt

# Finally, switch to the non-root user
USER flowintel

ENTRYPOINT ["/home/flowintel/app/bin/entrypoint.sh"]

# Default command: interactive bash + launch
CMD ["bash", "./launch.sh", "-ld"]
