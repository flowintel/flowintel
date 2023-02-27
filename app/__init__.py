from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

from config import Config


db = SQLAlchemy()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config["FLASK_URL"] = '127.0.0.1'
    app.config["FLASK_PORT"] = 7006


    db.init_app(app)
    csrf.init_app(app)

    from .main.home import home_blueprint
    from .account.account import account_blueprint
    app.register_blueprint(home_blueprint, url_prefix="/")
    app.register_blueprint(account_blueprint, url_prefix="/account")

    return app
