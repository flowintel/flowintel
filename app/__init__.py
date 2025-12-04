from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from flask_session import Session
from flask_login import LoginManager

from conf.config import config as Config
import os

import redis


db = SQLAlchemy()
csrf = CSRFProtect()
migrate = Migrate()
session = Session()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    config_name = os.environ.get("FLASKENV", "development")

    app.config.from_object(Config[config_name])

    Config[config_name].init_app(app)

    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    if not config_name == 'testing':
        app.config["SESSION_REDIS"] = redis.from_url(f'redis://{app.config.get("VALKEY_IP")}:{app.config.get("VALKEY_PORT")}')
        session.init_app(app)
    login_manager.login_view = "account.login"
    login_manager.init_app(app)

    from .main.home import home_blueprint
    from .account.account import account_blueprint
    from .case.case import case_blueprint
    from .admin.admin import admin_blueprint
    from .calendar.calendar import calendar_blueprint
    from .notification.notification import notification_blueprint
    from .tools.tools import tools_blueprint
    from .my_assignment.my_assignment import my_assignment_blueprint
    from .connectors.connectors import connector_blueprint
    from .analyzer.misp_modules import analyzer_blueprint
    from .custom_tags.custom_tags import custom_tags_blueprint
    from .templating.templating import templating_blueprint
    app.register_blueprint(home_blueprint, url_prefix="/")
    app.register_blueprint(account_blueprint, url_prefix="/account")
    app.register_blueprint(case_blueprint, url_prefix="/case")
    app.register_blueprint(admin_blueprint, url_prefix="/admin")
    app.register_blueprint(calendar_blueprint, url_prefix="/calendar")
    app.register_blueprint(notification_blueprint, url_prefix="/notification")
    app.register_blueprint(tools_blueprint, url_prefix="/tools")
    app.register_blueprint(templating_blueprint, url_prefix="/templating")
    app.register_blueprint(my_assignment_blueprint, url_prefix="/my_assignment")
    app.register_blueprint(connector_blueprint, url_prefix="/connectors")
    app.register_blueprint(analyzer_blueprint, url_prefix="/analyzer")
    csrf.exempt(analyzer_blueprint)
    app.register_blueprint(custom_tags_blueprint, url_prefix="/custom_tags")

    from .api import api_blueprint
    csrf.exempt(api_blueprint)
    app.register_blueprint(api_blueprint)

    return app
