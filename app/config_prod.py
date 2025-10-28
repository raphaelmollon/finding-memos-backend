import os
import datetime


LIFETIME_DELAY = 15     # in days
TIMEOUT_DELAY = 24*3600 # 1 day in seconds

SECRET_KEY = os.urandom(24)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True  
PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=LIFETIME_DELAY)  # Adjust as needed

SQLALCHEMY_DATABASE_URI = "sqlite:///memos.db"

# config_email.py has to be created and populated with the correct info
# For obvious reasons, it's not available on the repo
from app import config_email

MAIL_SERVER = config_email.MAIL_SERVER
MAIL_PORT = config_email.MAIL_PORT
MAIL_USE_SSL = config_email.MAIL_USE_SSL
MAIL_USE_TLS = config_email.MAIL_USE_TLS
MAIL_USERNAME = config_email.MAIL_USERNAME
MAIL_PASSWORD = config_email.MAIL_PASSWORD
MAIL_DEFAULT_SENDER = config_email.MAIL_DEFAULT_SENDER
FRONTEND_URL = config_email.FRONTEND_URL_PROD
