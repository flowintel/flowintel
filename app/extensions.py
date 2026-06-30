from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from flask_session import Session
from flask_login import LoginManager

db = SQLAlchemy()
csrf = CSRFProtect()
migrate = Migrate()
session = Session()
login_manager = LoginManager()
