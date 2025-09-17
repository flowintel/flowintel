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
    config_name = os.environ.get("FLASKENV")

    app.config.from_object(Config[config_name])

    Config[config_name].init_app(app)

    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    if not config_name == 'testing':
        app.config["SESSION_REDIS"] = redis.from_url('redis://127.0.0.1:6379')
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


    from .case.case_api import api_case_blueprint
    from .case.task_api import api_task_blueprint
    from .admin.admin_api import api_admin_blueprint
    from .templating.templating_api import api_templating_blueprint
    from .tools.tools_api import api_importer_blueprint
    from .tools.tools_api import api_case_misp_blueprint
    from .my_assignment.my_assignment_api import api_assignment_blueprint
    from .analyzer.analyzer_api import api_analyzer_blueprint
    from .custom_tags.custom_tags_api import api_custom_tags_blueprint
    from .connectors.connectors_api import api_connectors_blueprint
    csrf.exempt(api_case_blueprint)
    csrf.exempt(api_task_blueprint)
    csrf.exempt(api_admin_blueprint)
    csrf.exempt(api_templating_blueprint)
    csrf.exempt(api_importer_blueprint)
    csrf.exempt(api_case_misp_blueprint)
    csrf.exempt(api_assignment_blueprint)
    csrf.exempt(api_analyzer_blueprint)
    csrf.exempt(api_custom_tags_blueprint)
    csrf.exempt(api_connectors_blueprint)
    app.register_blueprint(api_case_blueprint, url_prefix="/api/case")
    app.register_blueprint(api_task_blueprint, url_prefix="/api/task")
    app.register_blueprint(api_admin_blueprint, url_prefix="/api/admin")
    app.register_blueprint(api_templating_blueprint, url_prefix="/api/template")
    app.register_blueprint(api_importer_blueprint, url_prefix="/api/importer")
    app.register_blueprint(api_case_misp_blueprint, url_prefix="/api/case_from_misp")
    app.register_blueprint(api_assignment_blueprint, url_prefix="/api/my_assignment")
    app.register_blueprint(api_analyzer_blueprint, url_prefix="/api/analyzer")
    app.register_blueprint(api_custom_tags_blueprint, url_prefix="/api/custom_tags")
    app.register_blueprint(api_connectors_blueprint, url_prefix="/api/connectors")

    return app
