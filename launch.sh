#!/bin/bash
isscripted=`screen -ls | egrep '[0-9]+.fcm' | cut -d. -f1`
source env/bin/activate

function killscript {
    if  [ $isscripted ]; then
		screen -X -S fcm quit
    fi
}

function launch {
    export FLASKENV="development"
    killscript
    python3 app.py -tg
    screen -dmS "fcm"
    screen -S "fcm" -X screen -t "recurring_notification" bash -c "python3 startNotif.py; read x"
    python3 app.py
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
    screen -S "fcm" -X screen -t "recurring_notification" bash -c "python3 startNotif.py; read x"
    gunicorn -w 4 'app:create_app()' -b 127.0.0.1:7006 --access-logfile -
}


function init_db {
	export FLASKENV="development"
	python3 app.py -i
	python3 app.py -tg
}

function reload_db {
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
    esac
    shift
else
	launch
fi
