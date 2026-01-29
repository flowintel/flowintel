#!/bin/bash -i
set -e

isscripted_fcm=`screen -ls | egrep '[0-9]+.fcm' | cut -d. -f1`
isscripted_misp_mod=`screen -ls | egrep '[0-9]+.misp_mod_flowintel' | cut -d. -f1`

history_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Directory of the python virtualenv to use; can be overridden by env var
VENV_DIR="${VENV_DIR:-env}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/$(basename "${BASH_SOURCE[0]}")"


# Configuration files
CONF_DIR="$(dirname "$0")/conf"
CONFIG_FILE="$CONF_DIR/config.py"
DEFAULT_FILE="$CONF_DIR/config.py.default"

# Check if config.py exists
if [ ! -f "$CONFIG_FILE" ]; then
    if [ -f "$DEFAULT_FILE" ]; then
        echo "config.py not found. Creating one from config.py.default..."
        cp "$DEFAULT_FILE" "$CONFIG_FILE"
    else
        echo "No default config file found in $CONF_DIR"
        exit 1
    fi
fi

CONF_DIR="$(dirname "$0")/conf"
CONFIG_MODULE_FILE="$CONF_DIR/config_module.py"
DEFAULT_MODULE_FILE="$CONF_DIR/config_module.py.default"

if [ ! -f "$CONFIG_MODULE_FILE" ]; then
    if [ -f "$DEFAULT_MODULE_FILE" ]; then
        echo "config_module.py not found. Creating one from config_module.py.default..."
        cp "$DEFAULT_MODULE_FILE" "$CONFIG_MODULE_FILE"
    else
        echo "No default config file found in $CONF_DIR"
        exit 1
    fi
fi

# Get app URL and port from config
APP_URL=$(PYTHONPATH=$SCRIPT_DIR python3 -c "from conf import config; print(config.Config.FLASK_URL)")
APP_PORT=$(PYTHONPATH=$SCRIPT_DIR python3 -c "from conf import config; print(config.Config.FLASK_PORT)")

function prepare_app_run {
    # This function is to avoid having problem with the env for test
    # Activate the configured virtualenv if present
    if [ -f "$VENV_DIR/bin/activate" ]; then
        # shellcheck source=/dev/null
        source "$VENV_DIR/bin/activate"
    else
        echo "[WARN] Virtualenv '$VENV_DIR' not found; continuing without activation" >&2
    fi
    mkdir -p logs  # Directory for log files
}


function killscript {
    echo "Stopping existing sessions..."
    if  [ $isscripted_fcm ]; then
        screen -X -S fcm quit
    fi
    if  [ $isscripted_misp_mod ]; then
        screen -X -S misp_mod_flowintel quit
    fi
}

function taxo_galaxy_update {
    prepare_app_run
    export FLASKENV="development"
    python3 app.py -tg
}

function misp_module_update {
    prepare_app_run
    export FLASKENV="development"
    screen -L -Logfile logs/misp.log -dmS "misp_mod_flowintel" bash -c "misp-modules -l 127.0.0.1"
    sleep 3
    python3 app.py -mm
    killscript
}

function launch {
    prepare_app_run
    #export FLASKENV="development"
    export HISTORY_DIR=$history_dir/history
    killscript

    # Start screen sessions with logs
    screen -L -Logfile logs/fcm.log -dmS "fcm" bash -c "python3 startNotif.py"
    screen -L -Logfile logs/misp.log -dmS "misp_mod_flowintel" bash -c "misp-modules -l 127.0.0.1"

    # Display logs
    tail -n 0 -F logs/fcm.log logs/misp.log &
    TAIL_PID=$!

    trap "echo; echo 'Stopping tail (PID $TAIL_PID)...'; kill $TAIL_PID 2>/dev/null; $SCRIPT_PATH -ks" INT TERM EXIT

    # Start our main application
    python3 app.py
}

function test {
    export FLASKENV="testing"
    export HISTORY_DIR=$history_dir/history_test
    pytest
    rm -r $HISTORY_DIR
}

function production {
    prepare_app_run
    export FLASKENV="production"
    export HISTORY_DIR=$history_dir/history
    killscript

    screen -L -Logfile logs/fcm.log -dmS "fcm" bash -c "python3 startNotif.py"
    screen -L -Logfile logs/misp.log -dmS "misp_mod_flowintel" bash -c "misp-modules -l 127.0.0.1"

    tail -n 0 -F logs/fcm.log logs/misp.log &
    TAIL_PID=$!

    trap "echo; echo 'Stopping tail (PID $TAIL_PID)...'; kill $TAIL_PID 2>/dev/null; $SCRIPT_PATH -ks" INT TERM EXIT

    gunicorn -w 4 'app:create_app()' -b $APP_URL:$APP_PORT --access-logfile -
}

function init_db {
    prepare_app_run
    export FLASKENV="development"
    export HISTORY_DIR=$history_dir/history

    screen -L -Logfile logs/misp.log -dmS "misp_mod_flowintel" bash -c "misp-modules -l 127.0.0.1"

    python3 app.py -i
    python3 app.py -tg
    python3 app.py -mm
    python3 app.py -td

    killscript
}

function init_db_prod {
    prepare_app_run
    export FLASKENV="production"
    export HISTORY_DIR=$history_dir/history

    screen -L -Logfile logs/misp.log -dmS "misp_mod_flowintel" bash -c "misp-modules -l 127.0.0.1"

    python3 app.py -i
    python3 app.py -tg
    python3 app.py -mm
    python3 app.py -td
}

function reload_db {
    prepare_app_run
    export HISTORY_DIR=$history_dir/history
    python3 app.py -r
}

function launch_docker {
    mkdir -p logs
    export FLASKENV="docker"
    export HISTORY_DIR=$history_dir/history

    # Start screen sessions with logs
    screen -L -Logfile logs/fcm.log -dmS "fcm" bash -c "python3 startNotif.py"
    screen -L -Logfile logs/misp.log -dmS "misp_mod_flowintel" bash -c "misp-modules -l 127.0.0.1"

    # Display logs
    tail -n 0 -F logs/fcm.log logs/misp.log &
    TAIL_PID=$!

    trap "echo; echo 'Stopping tail (PID $TAIL_PID)...'; kill $TAIL_PID 2>/dev/null; $SCRIPT_PATH -ks" INT TERM EXIT

    gunicorn -w 4 'app:create_app()' -b $APP_URL:$APP_PORT --access-logfile -
}

function init_db_docker {
    mkdir -p logs
    export FLASKENV="docker"
    export HISTORY_DIR=$history_dir/history

    screen -L -Logfile logs/misp.log -dmS "misp_mod_flowintel" bash -c "misp-modules -l 127.0.0.1"

    python3 app.py -i
    python3 app.py -tg
    python3 app.py -mm
    python3 app.py -td
}

if [ "$1" ]; then
    case $1 in
        -l | --launch )             launch;;
        -ld | --launch_docker )     launch_docker;;
        -i | --init_db )            init_db;;
        -id | --init_db_docker )    init_db_docker;;
        -ip | --init_db_prod )      init_db_prod;;
        -r | --reload_db )          reload_db;;
        -p | --production )         production;;
        -t | --test )               test;;
        -ks | --killscript )        killscript;;
        -tg | --taxo_galaxy )       taxo_galaxy_update;;
        -mm | --misp_modules )      misp_module_update;;
    esac
    shift
else
    launch
fi
