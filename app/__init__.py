from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from flask_login import LoginManager

from config import Config


db = SQLAlchemy()
csrf = CSRFProtect()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config["FLASK_URL"] = '127.0.0.1'
    app.config["FLASK_PORT"] = 7006

    app.config["DEBUG"] = True


    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    login_manager.login_view = "account.login"
    login_manager.init_app(app)

    from .main.home import home_blueprint
    from .account.account import account_blueprint
    from .case.case import case_blueprint
    from .admin.admin import admin_blueprint
    app.register_blueprint(home_blueprint, url_prefix="/")
    app.register_blueprint(account_blueprint, url_prefix="/account")
    app.register_blueprint(case_blueprint, url_prefix="/case")
    app.register_blueprint(admin_blueprint, url_prefix="/admin")

    from .case.case_api import api_case_blueprint
    from .admin.admin_api import api_admin_blueprint
    csrf.exempt(api_case_blueprint)
    csrf.exempt(api_admin_blueprint)
    app.register_blueprint(api_case_blueprint, url_prefix="/api/case")
    app.register_blueprint(api_admin_blueprint, url_prefix="/api/admin")

    return app
