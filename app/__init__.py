from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from flask_login import LoginManager

from config import config as Config
import os


db = SQLAlchemy()
csrf = CSRFProtect()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    config_name = os.environ.get("FLASKENV")

    app.config.from_object(Config[config_name])

    Config[config_name].init_app(app)

    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
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
    app.register_blueprint(home_blueprint, url_prefix="/")
    app.register_blueprint(account_blueprint, url_prefix="/account")
    app.register_blueprint(case_blueprint, url_prefix="/case")
    app.register_blueprint(admin_blueprint, url_prefix="/admin")
    app.register_blueprint(calendar_blueprint, url_prefix="/calendar")
    app.register_blueprint(notification_blueprint, url_prefix="/notification")
    app.register_blueprint(tools_blueprint, url_prefix="/tools")
    app.register_blueprint(my_assignment_blueprint, url_prefix="/my_assignment")


    from .case.case_api import api_case_blueprint
    from .admin.admin_api import api_admin_blueprint
    from .tools.templating_api import api_templating_blueprint
    from .tools.importer_api import api_importer_blueprint
    csrf.exempt(api_case_blueprint)
    csrf.exempt(api_admin_blueprint)
    csrf.exempt(api_templating_blueprint)
    csrf.exempt(api_importer_blueprint)
    app.register_blueprint(api_case_blueprint, url_prefix="/api/case")
    app.register_blueprint(api_admin_blueprint, url_prefix="/api/admin")
    app.register_blueprint(api_templating_blueprint, url_prefix="/api/template")
    app.register_blueprint(api_importer_blueprint, url_prefix="/api/importer")

    return app
