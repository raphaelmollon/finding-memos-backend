import os
import datetime

# Load environment variables from .env file in development
from dotenv import load_dotenv
load_dotenv()

LIFETIME_DELAY = int(os.getenv('LIFETIME_DELAY', 15))  # in days
TIMEOUT_DELAY = int(os.getenv('TIMEOUT_DELAY', 24*3600))  # 1 day in seconds

# Use SECRET_KEY from environment, fallback to generated key (not recommended for production)
SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = False  # no HTTPS in dev mode
SESSION_COOKIE_DOMAIN = None
PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=LIFETIME_DELAY)

SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', "sqlite:///memos.db")

# Email configuration from environment variables
MAIL_SERVER = os.getenv('MAIL_SERVER')
MAIL_PORT = int(os.getenv('MAIL_PORT', 465))
MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'True').lower() in ('true', '1', 'yes')
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'False').lower() in ('true', '1', 'yes')
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
FRONTEND_URL = os.getenv('FRONTEND_URL_DEV', 'http://localhost:8080')
