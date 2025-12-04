#!/bin/bash
VENV_DIR="${VENV_DIR:-env}"
if [ -f "$VENV_DIR/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
else
    echo "[WARN] Virtualenv '$VENV_DIR' not found; continuing without activation" >&2
fi

#!/bin/bash

# Default environment
FLASKENV="development"

# Function definitions
function migrate {
    flask db migrate
}

function upgrade {
    flask db upgrade
}

function downgrade {
    flask db downgrade
}

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
        -m|--migrate)
            ACTION="migrate"
            shift
            ;;
        -u|--upgrade)
            ACTION="upgrade"
            shift
            ;;
        -d|--downgrade)
            ACTION="downgrade"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 --env [development|production|docker] -m|-u|-d"
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

# Run action
if [[ -z "$ACTION" ]]; then
    echo "Error: No action specified. Use -m|--migrate, -u|--upgrade, or -d|--downgrade"
    exit 1
fi

case "$ACTION" in
    migrate) migrate ;;
    upgrade) upgrade ;;
    downgrade) downgrade ;;
esac
