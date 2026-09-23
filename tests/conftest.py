import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from sqlalchemy import event

import pytest


sys.path.append(os.getcwd())


def _worker_id() -> str:
    return os.environ.get("PYTEST_XDIST_WORKER", "master")


def _db_name() -> str:
    prefix = os.environ.get(
        "PYTEST_XDIST_WORKER_DB_PREFIX",
        "flowintel_test_",
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
        filename=f"tests_{_worker_id()}.log",
        filemode="w",
        level=logging.DEBUG,
    )


@pytest.fixture(scope="session")
def app():
    """
    Provide a Flask app for each test.
    - Ensures testing config flags.
    - Does NOT recreate schema (done in setup_database).
    """
    # This imports lands after the initialisation code above because build_db_uri() in config.py reads the env var at app-creation time 
    from app import create_app, db
    from app.utils.log_paths import resolve_log_file_path
    from app.utils.init_db import create_user_test

    database_name = _db_name()
    assert "_test_" in database_name, "Tests must never touch a real DB"
    
    # kept as a protection against potential previous crashes or during mid-test
    db_file = db_file_path()
    db_file.parent.mkdir(parents=True, exist_ok=True)
    if db_file.exists():
        db_file.unlink()


    # Own the env var here: set before create_app, restore after
    old_db_name = os.environ.get("DB_NAME")
    os.environ["DB_NAME"] = database_name

    app = create_app()
    app.config.update({
        "TESTING": True,
        "SERVER_NAME": f"{app.config.get('FLOWINTEL_APP_HOST')}:{app.config.get('FLOWINTEL_APP_PORT')}",
        "LIMIT_USER_VIEW_TO_ORG": True,
        "ENFORCE_PRIVILEGED_CASE": False
    })

    # Set FLOWINTEL_TEST_LOG=1 to write audit logs to logs/record.log during tests.
    if os.environ.get("FLOWINTEL_TEST_LOG") == "1":
        logs_folder = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_folder, exist_ok=True)
        log_file = app.config.get("LOG_FILE", "record.log")
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
        db.create_all()
        create_user_test()
        yield app
        db.session.remove()
        # Rollback all changes from this test
        db.drop_all()
        db.engine.dispose()
    
    # restore env after the session
    if old_db_name is None:
        os.environ.pop("DB_NAME", None)
    else:
        os.environ["DB_NAME"] = old_db_name


@pytest.fixture()
def db_session(app):
    """Per-test isolation: roll back everything the test wrote."""
    from app import db

    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Patch with recommended pattern https://github.com/pallets-eco/flask-sqlalchemy/discussions/1179
        original_engines = dict(db.engines)
        db.engines.update({key: connection for key in original_engines})

        db.session.remove()  # force FSA to build a session against the patched engine

        yield db.session

        db.session.remove()
        db.engines.clear()
        db.engines.update(original_engines)
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(app, db_session):
    return app.test_client()


@pytest.fixture()
def runner(app, db_session):
    return app.test_cli_runner()
