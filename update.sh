#!/bin/bash
set -e
VENV_DIR="${VENV_DIR:-env}"
if [ -f "$VENV_DIR/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
else
    echo "[WARN] Virtualenv '$VENV_DIR' not found; continuing without activation" >&2
fi

./launch.sh -ks

# Default environment
FLASKENV="development"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)
            if [[ -z "$2" ]]; then
                echo "Error: --env requires a value (development|production|docker)"
                exit 1
            fi
            FLASKENV="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 --env [development|production|docker]"
            exit 1
            ;;
    esac
done

# Validate environment
if [[ "$FLASKENV" != "development" && "$FLASKENV" != "production" && "$FLASKENV" != "docker" ]]; then
    echo "Error: Invalid environment '$FLASKENV'. Must be development, production, or docker."
    exit 1
fi

export FLASKENV

echo "##########"
echo "Git pull"
echo "##########"
git pull

echo ""
echo "##########"
echo "Database Backup & Migration"
echo "##########"

# Create backup folder if missing
if [ ! -d "instance/backup" ]; then
    mkdir -p instance/backup
fi

if [[ "$FLASKENV" == "development" ]]; then
    # SQLite backup
    cp instance/flowintel.sqlite instance/backup/$(date +"%Y_%m_%d").sqlite
else
    # PostgreSQL backup
    PGDATABASE=${PGDATABASE:-"flowintel"}
    BACKUP_FILE="instance/backup/$(date +"%Y_%m_%d")_pg.sql"
    echo "Backing up PostgreSQL database to $BACKUP_FILE"
    sudo -u postgres pg_dump -F c -b -v "$PGDATABASE" > "$BACKUP_FILE"
fi

# Run migration script
./migrate.sh --env "$FLASKENV" -u

echo ""
echo "##########"
echo "Python Dependencies"
echo "##########"
pip install -r requirements.txt

echo ""
echo "##########"
echo "Submodule Update"
echo "##########"
git submodule update --remote

python3 app.py -utg
python3 app.py -py

screen -dmS "misp_mod_flowintel"
screen -S "misp_mod_flowintel" -X screen -t "misp_modules_server" bash -c "misp-modules -l 127.0.0.1; read x"

echo "Waiting for MISP modules to start..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:6666/modules > /dev/null 2>&1; then
        echo "MISP modules are ready."
        break
    fi
    sleep 1
done

python3 app.py -mm

./launch.sh -ks