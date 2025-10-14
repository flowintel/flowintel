#!/bin/bash -i
set -e

isscripted_fcm=`screen -ls | egrep '[0-9]+.fcm' | cut -d. -f1`
isscripted_misp_mod=`screen -ls | egrep '[0-9]+.misp_mod_flowintel' | cut -d. -f1`

history_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

function prepare_app_run {
    # This function is to avoid having problem with the env for test
    source env/bin/activate
    mkdir -p logs  # pour les fichiers de log
}

function killscript {
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
    export FLASKENV="development"
    export HISTORY_DIR=$history_dir/history
    killscript

    # Sessions screen avec logs
    screen -L -Logfile logs/fcm.log -dmS "fcm" bash -c "python3 startNotif.py"
    screen -L -Logfile logs/misp.log -dmS "misp_mod_flowintel" bash -c "misp-modules -l 127.0.0.1"

    # Afficher les logs à l'écran
    tail -n 0 -F logs/fcm.log logs/misp.log &

    # Lancer le serveur principal (en avant-plan pour Docker)
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

    gunicorn -w 4 'app:create_app()' -b 127.0.0.1:7006 --access-logfile -
}

function init_db {
    prepare_app_run
    export FLASKENV="development"
    export HISTORY_DIR=$history_dir/history

    screen -L -Logfile logs/misp.log -dmS "misp_mod_flowintel" bash -c "misp-modules -l 127.0.0.1"

    python3 app.py -i
    python3 app.py -tg
    python3 app.py -mm

    killscript
}

function reload_db {
    prepare_app_run
    export HISTORY_DIR=$history_dir/history
    python3 app.py -r
}

if [ "$1" ]; then
    case $1 in
        -l | --launch )             launch;;
        -i | --init_db )            init_db;;
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
