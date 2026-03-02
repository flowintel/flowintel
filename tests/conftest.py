import sys
import os
import logging
from logging.handlers import RotatingFileHandler
sys.path.append(os.getcwd())
from app import create_app, db
from app.utils.init_db import create_user_test
import pytest

@pytest.fixture(scope="function")
def app():
    os.environ.setdefault("FLASKENV", "testing")
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SERVER_NAME": f"{app.config.get('FLASK_URL')}:{app.config.get('FLASK_PORT')}",
        "LIMIT_USER_VIEW_TO_ORG": True
    })

    # Set FLOWINTEL_TEST_LOG=1 to write audit logs to logs/record.log during tests.
    if os.environ.get("FLOWINTEL_TEST_LOG") == "1":
        logs_folder = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_folder, exist_ok=True)
        log_file = app.config.get("LOG_FILE", "record.log")
        file_handler = RotatingFileHandler(
            os.path.join(logs_folder, log_file),
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
    
    # Cleanup after test
    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()