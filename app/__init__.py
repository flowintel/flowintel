from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from flask_session import Session
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

from conf.config import config as Config
import os
import logging
from logging.handlers import RotatingFileHandler

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
    
    if not app.debug and not app.testing:
        logs_folder = os.path.join(os.getcwd(), "logs")
        if not os.path.isdir(logs_folder):
            os.mkdir(logs_folder)
        
        log_file = app.config.get('LOG_FILE', 'record.log')
        file_handler = RotatingFileHandler(
            f"{logs_folder}/{log_file}", 
            mode='a', 
            maxBytes=10*1024*1024,
            backupCount=5
        )
        
        log_formatter = logging.Formatter(
            '%(asctime)s - %(message)s', 
            datefmt='%d/%b/%Y %H:%M:%S'
        )
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(logging.INFO)
        
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)

    # Warn early if Entra ID is enabled but credentials are missing.
    if app.config.get('ENTRA_ID_ENABLED'):
        _missing_entra = [
            k for k in ('ENTRA_TENANT_ID', 'ENTRA_CLIENT_ID', 'ENTRA_CLIENT_SECRET')
            if not app.config.get(k)
        ]
        if _missing_entra:
            app.logger.warning(
                "ENTRA_ID_ENABLED is True but the following settings are missing "
                "or empty: %s — Entra ID login will not work until these are "
                "configured.", ', '.join(_missing_entra)
            )

    # ProxyFix for reverse proxy deployments
    if app.config.get('BEHIND_PROXY', False):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config.get('PROXY_X_FOR', 1),
            x_proto=app.config.get('PROXY_X_PROTO', 1),
            x_host=app.config.get('PROXY_X_HOST', 1),
            x_prefix=app.config.get('PROXY_X_PREFIX', 0)
        )

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
