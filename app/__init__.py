import os
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import redis


from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from markupsafe import Markup, escape
from .utils.log_paths import resolve_log_file_path, validate_log_file_name

from app.extensions import db, csrf, migrate, session, login_manager

from conf.config import config as Config # This will also parse the .env

def vue_escape(value):
    """Render server text safely inside DOM regions later compiled by Vue."""
    if value is None:
        return ""
    escaped = escape(value)
    return Markup(str(escaped).replace("[[", "[<!---->[").replace("]]", "]<!---->]"))

def load_saml_into_app_config(app):
    saml_path = app.config.get("SIMPLESAML_PYTHON3_SAML_PATH")
    if not saml_path:
        raise RuntimeError("SIMPLESAML_PYTHON3_SAML_PATH is not configured")

    settings_file = os.path.join(saml_path, "settings.json")
    advanced_file = os.path.join(saml_path, "advanced_settings.json")

    with open(settings_file, "r", encoding="utf-8") as f:
        saml_settings = json.load(f)

    advanced_settings = {}
    if os.path.exists(advanced_file):
        with open(advanced_file, "r", encoding="utf-8") as f:
            advanced_settings = json.load(f)

    app.config["SIMPLESAML_SETTINGS"] = {
        "strict": saml_settings.get("strict", True),
        "debug": saml_settings.get("debug", False),
        "sp": saml_settings.get("sp", {}),
        "idp": saml_settings.get("idp", {}),
        "security": advanced_settings.get("security", {}),
    }

    app.config["SIMPLESAML_SP_ENTITY_ID"] = saml_settings.get("sp", {}).get("entityId")
    app.config["SIMPLESAML_ACS_URL"] = (
        saml_settings.get("sp", {})
        .get("assertionConsumerService", {})
        .get("url")
    )
    app.config["SIMPLESAML_IDP_ENTITY_ID"] = saml_settings.get("idp", {}).get("entityId")
    app.config["SIMPLESAML_IDP_SSO_URL"] = (
        saml_settings.get("idp", {})
        .get("singleSignOnService", {})
        .get("url")
    )
    app.config["SIMPLESAML_IDP_SLO_URL"] = (
        saml_settings.get("idp", {})
        .get("singleLogoutService", {})
        .get("url")
    )
    app.config["SIMPLESAML_HAS_IDP_CERT"] = bool(
        saml_settings.get("idp", {}).get("x509cert")
    )
    app.config["SIMPLESAML_HAS_SP_CERT"] = bool(
        saml_settings.get("sp", {}).get("x509cert")
    )

def create_app():
    app = Flask(__name__)
    config_name = os.environ.get("FLOWINTEL_APP_ENV", "development").strip().lower()

    if config_name not in Config:
        raise ValueError(f"Unknown config environment: {config_name}")

    config_class = Config[config_name]
    app.config.from_object(config_class)
    app.config['LOG_FILE'] = validate_log_file_name(app.config.get('LOG_FILE', 'record.log'))
    config_class.init_app(app)
    app.jinja_env.filters["vue_escape"] = vue_escape

    @app.after_request
    def set_security_headers(resp):
        resp.headers.setdefault(
            "Content-Security-Policy",
            "form-action 'self'; frame-src 'self'; img-src 'self' data:; "
            "frame-ancestors 'self'; base-uri 'self'; object-src 'none'",
        )
        return resp
    if app.config.get("SIMPLESAML_ENABLED"):
        load_saml_into_app_config(app)
    
    if not app.debug and not app.testing:
        logs_folder = Path.cwd() / "logs"
        logs_folder.mkdir(exist_ok=True)
        
        file_handler = RotatingFileHandler(
            resolve_log_file_path(app.config['LOG_FILE'], logs_folder),
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

    # Enable WAL mode and a 30-second busy timeout for SQLite so concurrent
    # requests queue rather than immediately raising "database is locked".
    if app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('sqlite'):
        from sqlalchemy import event as _sa_event
        with app.app_context():
            @_sa_event.listens_for(db.engine, 'connect')
            def _set_sqlite_pragmas(dbapi_conn, _rec):
                cur = dbapi_conn.cursor()
                cur.execute('PRAGMA foreign_keys=ON')
                cur.execute('PRAGMA journal_mode=WAL')
                cur.execute('PRAGMA busy_timeout=30000')
                cur.close()
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
    from .tools.audit_logs import audit_logs_blueprint
    from .my_assignment.my_assignment import my_assignment_blueprint
    from .connectors.connectors import connector_blueprint
    from .analyzer.misp_modules import analyzer_blueprint
    from .custom_tags.custom_tags import custom_tags_blueprint
    from .templating.templating import templating_blueprint
    from .alerts import alerts_blueprint
    from .alerting import alerting_blueprint
    app.register_blueprint(home_blueprint, url_prefix="/")
    app.register_blueprint(account_blueprint, url_prefix="/account")
    app.register_blueprint(case_blueprint, url_prefix="/case")
    app.register_blueprint(admin_blueprint, url_prefix="/admin")
    app.register_blueprint(calendar_blueprint, url_prefix="/calendar")
    app.register_blueprint(notification_blueprint, url_prefix="/notification")
    app.register_blueprint(tools_blueprint, url_prefix="/tools")
    app.register_blueprint(audit_logs_blueprint, url_prefix="/tools/audit_logs")
    app.register_blueprint(templating_blueprint, url_prefix="/templating")
    app.register_blueprint(my_assignment_blueprint, url_prefix="/my_assignment")
    app.register_blueprint(connector_blueprint, url_prefix="/connectors")
    app.register_blueprint(analyzer_blueprint, url_prefix="/analyzer")
    app.register_blueprint(custom_tags_blueprint, url_prefix="/custom_tags")
    app.register_blueprint(alerts_blueprint, url_prefix="/alerts")
    app.register_blueprint(alerting_blueprint, url_prefix="/alerting")

    if app.config.get("ENABLE_CHATBOT", False):
        # Import lazily so the heavy chatbot dependencies (dspy, litellm, mcp)
        # are not loaded when the feature is disabled.
        from .chatbot.chatbot import chatbot_blueprint
        app.register_blueprint(chatbot_blueprint, url_prefix="/chatbot")

    from .api import api_blueprint
    csrf.exempt(api_blueprint)
    app.register_blueprint(api_blueprint)

    return app
