#!/bin/bash -i
set -e

history_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Directory of the python virtualenv to use; can be overridden by env var
VENV_DIR="${VENV_DIR:-env}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAIL_PID=""


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


function get_app_url_port {
    # Get app URL and port from config
    # Refactored as a function in order to make it compatible both when a local venv exists (nondocker) and when it doesnot (docker)
    # This allows to run the test in the local dev environment venv
    FLOWINTEL_APP_HOST=$(PYTHONPATH=$SCRIPT_DIR python3 -c "from conf import config; print(config.Config.FLOWINTEL_APP_HOST)")
    FLOWINTEL_APP_PORT=$(PYTHONPATH=$SCRIPT_DIR python3 -c "from conf import config; print(config.Config.FLOWINTEL_APP_PORT)")
}


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

function start_misp_modules_screen {
    if ! command -v misp-modules >/dev/null 2>&1; then
        echo "[WARN] 'misp-modules' command not found." >&2
        echo "[WARN] MISP modules will not be started. Install it or add it to your PATH to enable this feature." >&2
        return 1
    fi

    screen -L -Logfile logs/misp.log -dmS "misp_mod_flowintel" bash -c "misp-modules -l 127.0.0.1"
}


function killscript {
    echo "Stopping existing sessions..."
    local isscripted_fcm
    local isscripted_misp_mod
    local isscripted_misp_sync

    isscripted_fcm=$(screen -ls | egrep '[0-9]+\.fcm' | cut -d. -f1 || true)
    isscripted_misp_mod=$(screen -ls | egrep '[0-9]+\.misp_mod_flowintel' | cut -d. -f1 || true)
    isscripted_misp_sync=$(screen -ls | egrep '[0-9]+\.misp_sync' | cut -d. -f1 || true)

    if [ -n "$isscripted_fcm" ]; then
        screen -X -S fcm quit || true
    fi
    if [ -n "$isscripted_misp_mod" ]; then
        screen -X -S misp_mod_flowintel quit || true
    fi
    if [ -n "$isscripted_misp_sync" ]; then
        screen -X -S misp_sync quit || true
    fi
}

function cleanup_launch_processes {
    trap - INT TERM EXIT

    if [ -n "${TAIL_PID:-}" ]; then
        echo
        echo "Stopping tail (PID $TAIL_PID)..."
        kill "$TAIL_PID" 2>/dev/null || true
        wait "$TAIL_PID" 2>/dev/null || true
        TAIL_PID=""
    fi

    killscript
}

function setup_launch_cleanup {
    trap cleanup_launch_processes EXIT
    trap 'cleanup_launch_processes; exit 130' INT TERM
}

function taxo_galaxy_update {
    prepare_app_run
    export FLOWINTEL_APP_ENV="${FLOWINTEL_APP_ENV:-development}"
    python3 app.py -utg
}

function misp_module_update {
    prepare_app_run
    export FLOWINTEL_APP_ENV="${FLOWINTEL_APP_ENV:-development}"
    start_misp_modules_screen || true
    sleep 3
    python3 app.py -mm
    killscript
}

function launch {
    prepare_app_run
    export FLOWINTEL_APP_ENV="development"
    export HISTORY_DIR=$history_dir/history
    killscript

    # Start screen sessions with logs
    screen -L -Logfile logs/fcm.log -dmS "fcm" bash -c "python3 startNotif.py"
    screen -L -Logfile logs/misp_sync.log -dmS "misp_sync" bash -c "python3 startMispSync.py"
    start_misp_modules_screen || true

    # Display logs
    tail -n 0 -F logs/fcm.log logs/misp_sync.log logs/misp.log &
    TAIL_PID=$!

    setup_launch_cleanup

    # Start our main application
    python3 app.py
}

function test {
    prepare_app_run
    export FLOWINTEL_APP_ENV="testing"
    export HISTORY_DIR=$history_dir/history_test
    
    set +e
    # worth noting that now we try to use coverage, with the src pattern it would much clear to cover
    python3 -m pytest -n 0 \
        -p no:randomly \
        --cov=./app \
        --cov-report=term-missing \
        --durations=0

    pytest_exit_code=$?
    set -e

    # Clean up only on success
    if [ $pytest_exit_code -eq 0 ]; then
        rm -rf "$HISTORY_DIR"
        rm -f instance/flowintel_test_*
    else
        echo "[WARN] Tests failed ($pytest_exit_code). History preserved in $HISTORY_DIR for debugging" >&2
        echo "[WARN] Test databases preserved for inspection:" >&2
        ls -lh instance/flowintel_test_* 2>/dev/null || true
    fi
    
    return $pytest_exit_code
}


function test_parallel {
    prepare_app_run
    export FLOWINTEL_APP_ENV="testing"
    export HISTORY_DIR="$history_dir/history_test"
	export PYTEST_XDIST_WORKER_DB_PREFIX=flowintel_test_
    
    # Run tests but do not exit on failure to preserve test artefacts
    set +e
    # worth noting that now we try to use coverage, with the src pattern it would much clear to cover
    python3 -m pytest -n 4 \
        -p no:randomly \
		--cov=./app \
        --cov-report=term-missing \
        --dist loadfile \
		-m "not slow" \
		-v --capture=no \
        -s \
        --durations=0

    pytest_exit_code=$?
    set -e
    # Further doc:
    # https://brilliantbrains.me/blog/fix-test-db-commits-ensure
    # https://qaskills.sh/blog/pytest-best-practices-2026

    # Optional: drop test database after all workers complete
    # This should be outside the parallel execution
    # Comment it out if debug is needed at database level
        # Clean up only on success
    if [ $pytest_exit_code -eq 0 ]; then
        rm -rf "$HISTORY_DIR"
        rm -f "instance/${PYTEST_XDIST_WORKER_DB_PREFIX}*"
    else
        echo "[WARN] Tests failed ($pytest_exit_code). History preserved in $HISTORY_DIR for debugging" >&2
        echo "[WARN] Test databases preserved for inspection:" >&2
        ls -lh "instance/${PYTEST_XDIST_WORKER_DB_PREFIX}*" 2>/dev/null || true
    fi
    
    return $pytest_exit_code
}

function test_new {
    prepare_app_run
    export FLOWINTEL_APP_ENV="testing"
    export HISTORY_DIR="$history_dir/newhistory_test"
    
    # worth noting that now we try to use coverage, with the src pattern it would much clear to cover
    set +e
    python3 -m pytest -n 0 \
        --cov=./app \
        --cov-report=term-missing \
        --durations=0 \
        --noconftest -p tests.conftest_new

    # Quick batch of 10 random tests:
    # Kept for legacy as a first step of stress testing with "randomity"
    #for i in {1..10};do
    #  echo "=== Run $i ==="
    #  python3 -m pytest -n 0 \
    #      --cov=./app \
    #      --cov-report=term-missing \
    #      --durations=0 \
    #      --noconftest -p tests.conftest_new | grep " passed in "
    #done
    # This particular order was breaking database isolation in between tests before I turned to:
    # autouse=True
    # in
    # @pytest.fixture(autouse=True)
    # def db_session(app):
    # Kept for legacy as a reminder on how to reproduce isolation problems
    #python3 -m pytest \
    #    tests/admin/test_org_user_readonly.py \
    #    tests/case/test_case_read.py \
    #    tests/templating/test_template.py \
    #    tests/case/test_enforce_privileged_case.py \
    #    tests/admin/test_org_user_editor.py \
    #    tests/case/test_case_links_api.py \
    #    tests/case/test_case_caseadmin.py \
    #    tests/test_case_misp.py \
    #    tests/case/test_case_admin.py \
    #    tests/case/test_case_queuer.py \
    #    tests/calendar_feed/test_calendar.py \
    #    tests/custom_tags/test_custom_tags.py \
    #    tests/case/test_case_template_editor.py \
    #    tests/case/test_case_editor_not_in_case.py \
    #    tests/case/test_case_editor.py \
    #    tests/case/test_case_url_tools.py \
    #    tests/admin/test_role.py \
    #    tests/case/test_case_merge.py \
    #    tests/templating/test_template_url_tools.py \
    #    tests/tools/test_importer.py \
    #    tests/case/test_case_note_templates.py \
    #    tests/admin/test_org_user_orgadmin.py \
    #    tests/case/test_case_delete_cleanup.py \
    #    tests/case/test_task_api_extras.py \
    #    tests/connectors/test_connectors.py \
    #    tests/case/test_case_files.py \
    #    tests/admin/test_org_user_admin.py \
    #    tests/alerts/test_alert_ingest.py \
    #    tests/notification/test_notification_metadata.py \
    #    tests/templating/test_template_connectors.py \
    #    tests/case/test_case_admin_not_in_case.py \
    #    tests/case/test_case_history_audit_guard.py \
    #    tests/case/test_case_workflow.py \
    #    -n 0 \
    #    -p no:randomly \
    #    --cov=./app \
    #    --cov-report=term-missing \
    #    --durations=0 \
    #    --noconftest -p tests.conftest_new
    pytest_exit_code=$?
    set -e

    # Clean up only on success
    if [ $pytest_exit_code -eq 0 ]; then
        rm -rf "$HISTORY_DIR"
        rm -f instance/newflowintel_test_*
    else
        echo "[WARN] Tests failed ($pytest_exit_code). History preserved in $HISTORY_DIR for debugging" >&2
        echo "[WARN] Test databases preserved for inspection:" >&2
        ls -lh instance/newflowintel_test_* 2>/dev/null || true
    fi
    
    return $pytest_exit_code
}


function test_new_stress {
    prepare_app_run
    export FLOWINTEL_APP_ENV="testing"
    export HISTORY_DIR="$history_dir/newstresshistory_test"
    
    # worth noting that now we try to use coverage, with the src pattern it would much clear to cover
    set +e
    for i in {1..100};do
      echo "=== Run $i ==="
      python3 -m pytest -n 0 \
          --cov=./app \
          --cov-report=term-missing \
          --durations=0 \
          --noconftest -p tests.conftest_new | grep " passed in "
    done
    set -e

    # Always clean up
    rm -rf "$HISTORY_DIR"
    rm -f instance/newstressflowintel_test_*
}


function test_new_non_random {
    prepare_app_run
    export FLOWINTEL_APP_ENV="testing"
    export HISTORY_DIR="$history_dir/newnonrandomhistory_test"
    export PYTEST_XDIST_WORKER_DB_PREFIX=newnonrandomflowintel_test_
    
    # worth noting that now we try to use coverage, with the src pattern it would much clear to cover
    set +e
    python3 -m pytest -n 0 \
        -p no:randomly \
        --cov=./app \
        --cov-report=term-missing \
        --durations=0 \
        --noconftest -p tests.conftest_new
    pytest_exit_code=$?
    set -e

    # Clean up only on success
    if [ $pytest_exit_code -eq 0 ]; then
        rm -rf "$HISTORY_DIR"
        rm -f instance/newnonrandomflowintel_test_*
    else
        echo "[WARN] Tests failed ($pytest_exit_code). History preserved in $HISTORY_DIR for debugging" >&2
        echo "[WARN] Test databases preserved for inspection:" >&2
        ls -lh instance/newnonrandomflowintel_test_* 2>/dev/null || true
    fi
    
    return $pytest_exit_code
}


function test_new_parallel {
    prepare_app_run
    export FLOWINTEL_APP_ENV="testing"
    export HISTORY_DIR="$history_dir/newhistory_test"
	export PYTEST_XDIST_WORKER_DB_PREFIX=newflowintel_test_
    
    # Run tests but do not exit on failure to preserve test artefacts
    set +e
    # worth noting that now we try to use coverage, with the src pattern it would much clear to cover
    python3 -m pytest -n 2 \
		--cov=./app \
        --cov-report=term-missing \
        --dist loadfile \
		-m "not slow" \
		-v --capture=no \
        -s \
        --durations=0 \
        --noconftest -p tests.conftest_new

    pytest_exit_code=$?
    set -e
    # Further doc:
    # https://brilliantbrains.me/blog/fix-test-db-commits-ensure
    # https://qaskills.sh/blog/pytest-best-practices-2026

    # Optional: drop test database after all workers complete
    # This should be outside the parallel execution
    # Comment it out if debug is needed at database level
    # Clean up only on success
    if [ $pytest_exit_code -eq 0 ]; then
        rm -rf "$HISTORY_DIR"
        rm -f "instance/${PYTEST_XDIST_WORKER_DB_PREFIX}*"
    else
        echo "[WARN] Tests failed ($pytest_exit_code). History preserved in $HISTORY_DIR for debugging" >&2
        echo "[WARN] Test databases preserved for inspection:" >&2
        ls -lh "instance/${PYTEST_XDIST_WORKER_DB_PREFIX}*" 2>/dev/null || true
    fi
    
    return $pytest_exit_code
}

function production {
    prepare_app_run
    get_app_url_port
    export FLOWINTEL_APP_ENV="production"
    export HISTORY_DIR=$history_dir/history
    killscript

    screen -L -Logfile logs/fcm.log -dmS "fcm" bash -c "python3 startNotif.py"
    screen -L -Logfile logs/misp_sync.log -dmS "misp_sync" bash -c "python3 startMispSync.py"
    start_misp_modules_screen || true

    tail -n 0 -F logs/fcm.log logs/misp_sync.log logs/misp.log &
    TAIL_PID=$!

    setup_launch_cleanup

    gunicorn -w 4 'app:create_app()' -b $FLOWINTEL_APP_HOST:$FLOWINTEL_APP_PORT --access-logfile -
}

function init_db {
    prepare_app_run
    export FLOWINTEL_APP_ENV="development"
    export HISTORY_DIR=$history_dir/history

    start_misp_modules_screen || true

    echo "Initialise the db if it not exist. Wait for Done..."
    python3 app.py -i
    echo "Done"
    echo "Add taxonomies and galaxies. Wait for Done..."
    python3 app.py -tg
    echo "Done"
    echo "Add or update misp-modules. Wait for Done..."
    python3 app.py -mm
    echo "Done"
    echo "Create default test cases. Wait for Done..."
    python3 app.py -td
    echo "Done"

    killscript
}

function init_db_prod {
    prepare_app_run
    export FLOWINTEL_APP_ENV="production"
    export HISTORY_DIR=$history_dir/history

    start_misp_modules_screen || true

    echo "Initialise the db if it not exist. Wait for Done..."
    python3 app.py -i
    echo "Done"
    echo "Add taxonomies and galaxies. Wait for Done..."
    python3 app.py -tg
    echo "Done"
    echo "Add or update misp-modules. Wait for Done..."
    python3 app.py -mm
    echo "Done"
    # don't import test data for prod 
    #echo "Create default test cases"
    #python3 app.py -td

    killscript
}

function reload_db {
    prepare_app_run
    export FLOWINTEL_APP_ENV="${FLOWINTEL_APP_ENV:-development}"
    export HISTORY_DIR=$history_dir/history
    python3 app.py -r
}

function launch_docker {
    get_app_url_port
    mkdir -p logs
    export FLOWINTEL_APP_ENV="${FLOWINTEL_APP_ENV:-production}"
    export HISTORY_DIR=$history_dir/history

    # Start screen sessions with logs
    screen -L -Logfile logs/fcm.log -dmS "fcm" bash -c "python3 startNotif.py"
    screen -L -Logfile logs/misp_sync.log -dmS "misp_sync" bash -c "python3 startMispSync.py"
    start_misp_modules_screen || true

    # Display logs
    tail -n 0 -F logs/fcm.log logs/misp_sync.log logs/misp.log &
    TAIL_PID=$!

    setup_launch_cleanup

    gunicorn -w 4 'app:create_app()' \
        -b "$FLOWINTEL_APP_HOST:$FLOWINTEL_APP_PORT" \
        --access-logfile - \
        --error-logfile - \
        --capture-output
}

function init_db_docker {
    # Run Python unbuffered so we see progress when the app.py inits
    mkdir -p logs
    export FLOWINTEL_APP_ENV="${FLOWINTEL_APP_ENV:-production}"
    export HISTORY_DIR=$history_dir/history

    start_misp_modules_screen || true

    echo "Initialise the db if it not exist. Wait for Done..."
    python3 -u app.py -i
    echo "Done"
    echo "Add taxonomies and galaxies. Wait for Done..."
    python3 -u app.py -tg
    echo "Done"
    echo "Add or update misp-modules. Wait for Done..."
    python3 -u app.py -mm
    echo "Done"
    # don't import test data for prod 
    #echo "Create default test cases"
    #python3 app.py -td
}

function test_data_community {
    local api_key="$1"
    if [ -z "$api_key" ]; then
        echo "Usage: launch.sh -tdc <admin_api_key>"
        exit 1
    fi
    prepare_app_run
    get_app_url_port
    python3 tests/testdata/init_community_data.py create --api-key "$api_key" --url "http://$FLOWINTEL_APP_HOST:$FLOWINTEL_APP_PORT"
}

function delete_test_data_community {
    local api_key="$1"
    if [ -z "$api_key" ]; then
        echo "Usage: launch.sh -dtdc <admin_api_key>"
        exit 1
    fi
    prepare_app_run
    get_app_url_port
    python3 tests/testdata/init_community_data.py delete --api-key "$api_key" --url "http://$FLOWINTEL_APP_HOST:$FLOWINTEL_APP_PORT"
}

function test_data_cases {
    prepare_app_run
    get_app_url_port
    python3 tests/testdata/init_community_cases.py create --url "http://$FLOWINTEL_APP_HOST:$FLOWINTEL_APP_PORT"
}

function delete_test_data_cases {
    prepare_app_run
    get_app_url_port
    python3 tests/testdata/init_community_cases.py delete --url "http://$FLOWINTEL_APP_HOST:$FLOWINTEL_APP_PORT"
}

if [ "$1" ]; then
    case $1 in
        -l | --launch )                 launch;;
        -ld | --launch_docker )         launch_docker;;
        -i | --init_db )                init_db;;
        -id | --init_db_docker )        init_db_docker;;
        -ip | --init_db_prod )          init_db_prod;;
        -r | --reload_db )              reload_db;;
        -p | --production )             production;;
        -tn | --test-new )              test_new;;
        -tnnr | --test-new-non-random ) test_new_non_random;;
        -tns | --test-new-stress )      test_new_stress;;
        -tnp | --test-new-parallel )    test_new_parallel;;
        -t | --test )                   test;;
        -tp | --test-parallel )         test_parallel;;
        -ks | --killscript )            killscript;;
        -tg | --taxo_galaxy )           taxo_galaxy_update;;
        -mm | --misp_modules )          misp_module_update;;
        -tdc | --test_data_community )         test_data_community "$2";;
        -dtdc | --delete_test_data_community ) delete_test_data_community "$2";;
        -tdcc | --test_data_cases )            test_data_cases;;
        -dtdcc | --delete_test_data_cases )    delete_test_data_cases;;
    esac
    shift
else
    launch
fi
