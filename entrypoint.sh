#!/bin/bash
set -e

MARKER="/home/flowintel/app/.initialized"

/home/flowintel/app/wait-for-it.sh postgresql:5432 --timeout=30 --strict -- echo "Postgres is up"

# Run initialization only once
if [ ! -f "$MARKER" ]; then
    echo "[flowintel] First-time initialization..."
    bash -i /home/flowintel/app/launch.sh -id
    touch "$MARKER"
    echo "[flowintel] Initialization complete."
fi

echo "[flowintel] Starting normally..."
exec bash -i /home/flowintel/app/launch.sh -ld