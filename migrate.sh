#!/bin/bash

# TODO Add an argument or rely on conf.py to identify dialect and so the migrations branch name ?
# TODO Regarding migration creation: It should be noted that the first migration needs to be already existed, derived from base and in a specific folder

VENV_DIR="${VENV_DIR:-env}"
if [ -f "$VENV_DIR/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
else
    echo "[WARN] Virtualenv '$VENV_DIR' not found; continuing without activation" >&2
fi

# Function definitions
function migrate {
    flask db migrate -m "$MESSAGE" "${MIGRATE_OPTS[@]}"
}

function upgrade {
    flask db upgrade "${UPGRADE_TARGET}"
}

function downgrade {
    flask db downgrade
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --message)
            if [[ -z "$2" ]]; then
                echo "Error: --message requires a migration message"
                exit 1
            fi
            MESSAGE="$2"
            shift 2
            ;;
        --migration_branch)
            if [[ -z "$2" ]]; then
                MIGRATION_BRANCH="Postgres"
                # Kept in case we need to revert to branching
                # echo "Error: --migration_branch requires a value (postgres|sqlite|mariadb)"
                # exit 1
                #
            fi
            MIGRATION_BRANCH="$2"
            shift 2
            ;;
        --env)
            if [[ -z "$2" ]]; then
                echo "Error: --env requires a value (development|production|testing)"
                exit 1
            fi
            export FLOWINTEL_APP_ENV="$2"
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
if [[ "$FLOWINTEL_APP_ENV" != "development" && "$FLOWINTEL_APP_ENV" != "production" && "$FLOWINTEL_APP_ENV" != "docker" ]]; then
    echo "Error: Invalid environment '$FLOWINTEL_APP_ENV'. Must be development, production, or testing."
    exit 1
fi

case "$MIGRATION_BRANCH" in
  postgres)
    UPGRADE_TARGET="head"
    MIGRATE_OPTS=(--head head --version-path migrations/versions)
    # Kept in case we need to revert to branching
    # UPGRADE_TARGET="postgres@head"
    # MIGRATE_OPTS=(--head postgres@head --version-path migrations/versions)
    #
    ;;
  mariadb)
    UPGRADE_TARGET="head"
    MIGRATE_OPTS=(--head head --version-path migrations/versions)
    # Kept in case we need to revert to branching
    # UPGRADE_TARGET="mariadb@head"
    # MIGRATE_OPTS=(--head mariadb@head --version-path migrations/versions_mariadb)
    #
    ;;
  sqlite)
    # The following assumption is based on the observation that postgres (prod) and sqlite (dev) were apparently working
    # with the same models, same migration files at v3.3.0
    UPGRADE_TARGET="head"
    MIGRATE_OPTS=(--head head --version-path migrations/versions)
    # Kept in case we need to revert to branching
    # UPGRADE_TARGET="postgres@head"
    # MIGRATE_OPTS=(--head postgres@head --version-path migrations/versions)
    #
    ;;
  *)
    UPGRADE_TARGET="head"
    MIGRATE_OPTS=(--head head --version-path migrations/versions)
    # Kept in case we need to revert to branching
    # echo "Error: Invalid migration branch '$MIGRATION_BRANCH'. Must be postgres, sqlite, or mariadb."
    # exit 1
    #
    ;;
esac

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
