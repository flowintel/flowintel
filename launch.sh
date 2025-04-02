#!/bin/bash -i
isscripted_fcm=`screen -ls | egrep '[0-9]+.fcm' | cut -d. -f1`
isscripted_misp_mod=`screen -ls | egrep '[0-9]+.misp_mod_flowintel' | cut -d. -f1`
source env/bin/activate
history_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

function killscript {
    if  [ $isscripted_fcm ]; then
		screen -X -S fcm quit
    fi
    if  [ $isscripted_misp_mod ]; then
		screen -X -S misp_mod_flowintel quit
    fi
}

function db_upgrade {
    export FLASKENV="development"
    python3 app.py -tg
    python3 app.py -mm
}

function launch {
    export FLASKENV="development"
    export HISTORY_DIR=$history_dir/history
    killscript
    screen -dmS "fcm"
    screen -S "fcm" -X screen -t "recurring_notification" bash -c "python3 startNotif.py; read x"
    screen -dmS "misp_mod_flowintel"
    screen -S "misp_mod_flowintel" -X screen -t "misp_modules_server" bash -c "misp-modules -l 127.0.0.1; read x"
    python3 app.py
}

function test {
    export FLASKENV="testing"
    export HISTORY_DIR=$history_dir/history_test
    pytest
    rm -r $HISTORY_DIR
}

function production {
    export FLASKENV="development"
    export HISTORY_DIR=$history_dir/history
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
	export HISTORY_DIR=$history_dir/history

	screen -dmS "misp_mod_flowintel"
    screen -S "misp_mod_flowintel" -X screen -t "misp_modules_server" bash -c "misp-modules -l 127.0.0.1; read x"

	python3 app.py -i
	python3 app.py -tg
}

function reload_db {
    export HISTORY_DIR=$history_dir/history
	python3 app.py -r
}


if [ "$1" ]; then
    case $1 in
        -l | --launch )             launch;
                                        ;;
		-i | --init_db )            init_db;
                                        ;;
		-r | --reload_db )          reload_db;
                                        ;;
        -p | --production )         production;
                                        ;;
        -t | --test )               test;
                                        ;;
        -ks | --killscript )        killscript;
                                        ;;
        -u | --db_upgrade )         db_upgrade;
    esac
    shift
else
	launch
fi
