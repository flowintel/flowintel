class Config:
    SECRET_KEY = 'SECRET_KEY_ENV_VAR_NOT_SET'
    SQLALCHEMY_DATABASE_URI = "sqlite:///flowintel-cm.sqlite"
    
    FLASK_URL = '127.0.0.1'
    FLASK_PORT = 7006
    
    DEBUG = True
