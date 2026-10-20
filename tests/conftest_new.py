import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from sqlalchemy import select as sa_select
from sqlalchemy import func as sa_func

import pytest


sys.path.append(os.getcwd())


def _row_counts(app) -> dict:
    from app import db
    with db.engine.connect() as c:
        return {
            t.name: c.execute(sa_select(sa_func.count()).select_from(t)).scalar_one()
            for t in db.metadata.sorted_tables
        }

def _worker_id() -> str:
    return os.environ.get("PYTEST_XDIST_WORKER", "master")


def _db_name() -> str:
    prefix = os.environ.get(
        "PYTEST_XDIST_WORKER_DB_PREFIX",
        "newflowintel_test_",
    )
    return f"{prefix}{_worker_id()}"


def db_file_path():
    """
    Mirror the logic in config.py/build_db_uri() to compute the SQLite file path
    before create_app() is called.
    """
    name = _db_name()

    # In testing, we expect DIALECT to be unset or "sqlite"
    dialect = os.getenv("DB_DIALECT", "")

    if dialect == "sqlite":
        # Explicit SQLite: use SQLITE_PATH or default to {name}.sqlite
        db_path = os.getenv("SQLITE_PATH", f"instance/{name}.sqlite")
    else:
        # Implicit SQLite (development/testing fallback)
        db_path = f"instance/{name}.sqlite"

    return Path(db_path).resolve()


def pytest_configure(config):
    logging.basicConfig(
        filename=f"newtests_{_worker_id()}.log",
        filemode="w",
        level=logging.DEBUG,
    )


@pytest.fixture(scope="session")
def app():
    """
    Provide a Flask app for each test.
    - Ensures testing config flags.
    - The database with its schema is created once, in the setup phase. Here the data
    is cleared after each test using a rollback strategy
    """
    # This imports lands after the initialisation code above because build_db_uri() in config.py reads the env var at app-creation time 
    from app import create_app, db
    from app.utils.log_paths import resolve_log_file_path
    from app.utils.init_db import create_user_test

    assert "_test_" in _db_name(), "Tests must never touch a real DB"
    
    # kept as a protection against potential previous crashes or during mid-test
    db_file = db_file_path()
    db_file.parent.mkdir(parents=True, exist_ok=True)
    if db_file.exists():
        db_file.unlink()


    # Own the env var here: set before create_app, restore after
    old_db_name = os.environ.get("DB_NAME")
    old_app_env = os.environ.get("FLOWINTEL_APP_ENV")
    
    os.environ["FLOWINTEL_APP_ENV"] = "testing"

    # --- Worker isolation fix -------------------------------------------
    # worker_id is provided by pytest-xdist: "master" when run without -n,
    # otherwise "gw0", "gw1", ... one per parallel worker.
    # We give each worker its own database/schema name so concurrent
    # drop_all()/create_all() calls never collide across workers.
    # Adjust the env var name to whatever your build_db_uri()/config
    # actually reads for the DB name (e.g. FLOWINTEL_DB_NAME, DB_NAME...).
    os.environ["DB_NAME"] = _db_name()
    # ----------------------------------------------------------------------

    app = None
    file_handler = None

    # We let pytest fails "naturally" ...
    try:
        app = create_app()
        app.config.update({
            "TESTING": True,
            "SERVER_NAME": f"{app.config.get('FLOWINTEL_APP_HOST')}:{app.config.get('FLOWINTEL_APP_PORT')}",
            "LIMIT_USER_VIEW_TO_ORG": True,
            "ENFORCE_PRIVILEGED_CASE": False,
            "LOG_FILE": f"new_{app.config.get('LOG_FILE')}"
        })

        # Set FLOWINTEL_TEST_LOG=1 to write audit logs to logs/new_record.log during tests.
        if os.environ.get("FLOWINTEL_TEST_LOG") == "1":
            logs_folder = os.path.join(os.getcwd(), "logs")
            os.makedirs(logs_folder, exist_ok=True)
            log_file = "new_"
            log_file += f"test_record_{_worker_id()}.log"
            file_handler = RotatingFileHandler(
                resolve_log_file_path(log_file, logs_folder),
                mode="a",
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
            )
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(message)s", datefmt="%d/%b/%Y %H:%M:%S"
            ))
            file_handler.setLevel(logging.INFO)
            logging.getLogger().addHandler(file_handler)
            logging.getLogger().setLevel(logging.INFO)

        with app.app_context():
            db.drop_all()
            db.create_all()
            create_user_test()
   
        yield app

    # ... but teardown will run even if setup failed
    finally:  
        if app is not None:
            try:
                with app.app_context():
                    db.session.remove()
                    db.drop_all()
                    db.engine.dispose()
            except Exception:
                # Log but don’t re-raise: no hide the original failure
                logging.getLogger(__name__).exception("Teardown failed in app fixture")
            
        if file_handler is not None:
            logging.getLogger().removeHandler(file_handler)
            file_handler.close()

        if old_db_name is None:
            os.environ.pop("DB_NAME", None)
        else:
            os.environ["DB_NAME"] = old_db_name
        
        if old_app_env is None:
            os.environ.pop("FLOWINTEL_APP_ENV", None)
        else:
            os.environ["FLOWINTEL_APP_ENV"] = old_app_env
    

@pytest.fixture(autouse=True)
def db_session(app):
    """
    Per-test isolation: roll back everything the test wrote.
    Check that there are no residual lines after rollback.
    """
    from app import db

    with app.app_context():
        before = _row_counts(app)

        logging.getLogger(__name__).info(
            "Before runing test: %s", before
        )

        connection = db.engine.connect()
        transaction = connection.begin()
            
        # Patch with recommended pattern https://github.com/pallets-eco/flask-sqlalchemy/discussions/1179
        original_engines = dict(db.engines)
        try:
            db.engines.update({key: connection for key in original_engines})
            
            db.session.remove()  # force Flask-SQL Alchemy to build a session against the patched engine

            yield db.session

            # Cannot use the helper _row_counts() because a connection object is already established -> must reuse it
            during = {
                t.name: connection.execute(sa_select(sa_func.count()).select_from(t)).scalar_one()
                for t in db.metadata.sorted_tables
            }
            diff = {t: (before[t], during[t]) for t in during if during[t] != before.get(t)}
            logging.getLogger(__name__).info(
                f"DB rows written during test: {diff}",
            )

        finally:
            db.session.remove()

            db.engines.clear()
            db.engines.update(original_engines)
            
            # Always roll back, even if the transaction looks inactive
            try:
                # Kept this debug line for legacy on verbose debug, but normally outputting the situation before test
                # and the diff is enough
                #logging.getLogger(__name__).info(
                #    "Before rollback: %s", _row_counts(app)
                #)
                transaction.rollback()
                # Kept this debug line for legacy on verbose debug, but normally outputting the situation before test
                # and the diff is enough
                #logging.getLogger(__name__).info(
                #    "After rollback: %s", _row_counts(app)
                #)
            except Exception:
                # Don’t let a failed rollback hide the real test result
                logging.getLogger(__name__).exception("Rollback failed in db_session")
            
            connection.close()
        
        after = _row_counts(app)

    if after != before:
        diff = {t: (before[t], after[t]) for t in after if after[t] != before.get(t)}
        pytest.fail(
            f"DB isolation leak detected: {diff} (before, after)",
            pytrace=False,
        )


@pytest.fixture(autouse=True)
def _log_test_id(request):
    """Log test ID / node ID at test start."""
    nodeid = request.node.nodeid          # e.g. "tests/case/test_case_admin.py::test_create_case"
    test_id = request.node.name           # e.g. "test_create_case"

    logging.getLogger(__name__).info(
        f"Starting test: nodeid=%s, test_id=%s", nodeid, test_id,
    )

    yield

    logging.getLogger(__name__).info(
        f"Finished test: nodeid=%s, test_id=%s", nodeid, test_id,
    )


@pytest.fixture()
def client(app, db_session):
    return app.test_client()


@pytest.fixture()
def runner(app, db_session):
    return app.test_cli_runner()
