#!/bin/bash
isscripted=`screen -ls | egrep '[0-9]+.fcm' | cut -d. -f1`
source env/bin/activate

function killscript {
    if  [ $isscripted ]; then
		screen -X -S fcm quit
    fi
}

function db_upgrade {
    flask db upgrade
}

function launch {
    export FLASKENV="development"
    killscript
    db_upgrade
    python app.py -t
    python app.py -g
    screen -dmS "fcm"
    screen -S "fcm" -X screen -t "recurring_notification" bash -c "python startNotif.py; read x"
    python app.py
}

function test {
    export FLASKENV="testing"
    pytest
}

function production {
    export FLASKENV="development"
    killscript
    db_upgrade
    screen -dmS "fcm"
    screen -S "fcm" -X screen -t "recurring_notification" bash -c "python startNotif.py; read x"
    gunicorn -w 4 'app:create_app()' -b 127.0.0.1:7006 --access-logfile -
}


function init_db {
	python app.py -i
}

function reload_db {
	python app.py -r
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
    esac
    shift
else
	launch
fi
