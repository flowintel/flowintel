import os
class Config:
    SECRET_KEY = 'SECRET_KEY_ENV_VAR_NOT_SET'
    
    FLASK_URL = '127.0.0.1'
    FLASK_PORT = 7006
    SESSION_TYPE = "sqlalchemy"
    SESSION_SQLALCHEMY_TABLE = "flask_sessions"
    MISP_MODULE = '127.0.0.1:6666'


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///flowintel.sqlite"

    @classmethod
    def init_app(cls, app):
        print('THIS APP IS IN DEBUG MODE. \
                YOU SHOULD NOT SEE THIS IN PRODUCTION.')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///flowintel-test.sqlite"
    WTF_CSRF_ENABLED = False

    @classmethod
    def init_app(cls, app):
        print('THIS APP IS IN TESTING MODE.  \
                YOU SHOULD NOT SEE THIS IN PRODUCTION.')

class ProductionConfig(Config):
    # environment variables
    db_user = os.getenv('DB_USER', 'default_user')
    db_password = os.getenv('DB_PASSWORD', 'default_password')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'default_db')

    # Database URI
    SQLALCHEMY_DATABASE_URI = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    @classmethod
    def init_app(cls, app):
        print('THIS APP IS IN PRODUCTION MODE.')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
