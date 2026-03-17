#!/bin/zsh -i

# Retrieve screen session IDs for fcm and misp_mod_flowintel
isscripted_fcm=$(screen -ls | grep -E '[0-9]+\.fcm' | cut -d. -f1)
isscripted_misp_mod=$(screen -ls | grep -E '[0-9]+\.misp_mod_flowintel' | cut -d. -f1)

# Activate the Python virtual environment
source env/bin/activate

# Determine the directory of this script (history directory)
history_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )

function killscript {
    if [ "$isscripted_fcm" ]; then
        screen -X -S fcm quit
    fi
    if [ "$isscripted_misp_mod" ]; then
        screen -X -S misp_mod_flowintel quit
    fi
}

function taxo_galaxy_update {
    export FLASKENV="development"
    python3 app.py -tg
}

function misp_module_update {
    export FLASKENV="development"

    screen -dmS "misp_mod_flowintel"
    screen -S "misp_mod_flowintel" -X screen -t "misp_modules_server" bash -c "misp-modules -l 127.0.0.1; read x"

    sleep 3
    python3 app.py -mm

    killscript
}

function launch {
    export FLASKENV="development"
    export HISTORY_DIR="$history_dir/history"
    killscript
    screen -dmS "fcm"
    screen -S "fcm" -X screen -t "recurring_notification" bash -c "python3 startNotif.py; read x"
    screen -dmS "misp_mod_flowintel"
    screen -S "misp_mod_flowintel" -X screen -t "misp_modules_server" bash -c "misp-modules -l 127.0.0.1; read x"
    python3 app.py
}

function test {
    export FLASKENV="testing"
    export HISTORY_DIR="$history_dir/history_test"
    pytest
    rm -r "$HISTORY_DIR"
}

function production {
    export FLASKENV="development"
    export HISTORY_DIR="$history_dir/history"
    killscript
    db_upgrade
    screen -dmS "fcm"
    screen -S "fcm" -X screen -t "recurring_notification" bash -c "python3 startNotif.py; read x"
    screen -dmS "misp_mod_flowintel"
    screen -S "misp_mod_flowintel" -X screen -t "misp_modules_server" bash -c "misp-modules -l 127.0.0.1; read x"
    gunicorn -w 4 'app:create_app()' -b 127.0.0.1:7006 --access-logfile -
}

function init_db {
    export FLASKENV="development"
    export HISTORY_DIR="$history_dir/history"

    screen -dmS "misp_mod_flowintel"
    screen -S "misp_mod_flowintel" -X screen -t "misp_modules_server" bash -c "misp-modules -l 127.0.0.1; read x"

    python3 app.py -i
    python3 app.py -tg
    python3 app.py -mm

    killscript
}

function reload_db {
    export HISTORY_DIR="$history_dir/history"
    python3 app.py -r
}

if [ "$1" ]; then
    case $1 in
        -l|--launch )
            launch;
            ;;
        -i|--init_db )
            init_db;
            ;;
        -r|--reload_db )
            reload_db;
            ;;
        -p|--production )
            production;
            ;;
        -t|--test )
            test;
            ;;
        -ks|--killscript )
            killscript;
            ;;
        -tg|--taxo_galaxy )
            taxo_galaxy_update;
            ;;
        -mm|--misp_modules )
            misp_module_update;
            ;;
    esac
    shift
else
    launch
fi