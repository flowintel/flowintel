import sys
import os
sys.path.append(os.getcwd())
from app import create_app, db
from app.utils.init_db import create_user_test
import pytest

@pytest.fixture
def app():
    os.environ.setdefault("FLASKENV", "testing")
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SERVER_NAME": f"{app.config.get('FLASK_URL')}:{app.config.get('FLASK_PORT')}",
        "LIMIT_USER_VIEW_TO_ORG": True
    })

    with app.app_context():
        db.drop_all()
        db.create_all()
        create_user_test()

    yield app

@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()