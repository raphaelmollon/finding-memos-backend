import os
import datetime

# Load environment variables from .env file (if present)
from dotenv import load_dotenv
load_dotenv()

LIFETIME_DELAY = int(os.getenv('LIFETIME_DELAY', 15))  # in days
TIMEOUT_DELAY = int(os.getenv('TIMEOUT_DELAY', 24*3600))  # 1 day in seconds

# Generate a new key every time the server restarts to force users to log in again
SECRET_KEY = os.urandom(24)

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True
PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=LIFETIME_DELAY)

SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')

# Validate database URI in production
if not SQLALCHEMY_DATABASE_URI:
    raise ValueError("SQLALCHEMY_DATABASE_URI environment variable must be set in production")

if SQLALCHEMY_DATABASE_URI.startswith('sqlite'):
    raise ValueError("Production environment must use MariaDB, not SQLite")

# Database connection pool settings for production
SQLALCHEMY_POOL_SIZE = int(os.getenv('SQLALCHEMY_POOL_SIZE', 20))
SQLALCHEMY_POOL_RECYCLE = int(os.getenv('SQLALCHEMY_POOL_RECYCLE', 3600))
SQLALCHEMY_POOL_PRE_PING = os.getenv('SQLALCHEMY_POOL_PRE_PING', 'True').lower() in ('true', '1', 'yes')
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': SQLALCHEMY_POOL_SIZE,
    'pool_recycle': SQLALCHEMY_POOL_RECYCLE,
    'pool_pre_ping': SQLALCHEMY_POOL_PRE_PING,
}

# Email configuration from environment variables - REQUIRED in production
MAIL_SERVER = os.getenv('MAIL_SERVER')
MAIL_PORT = int(os.getenv('MAIL_PORT', 465))
MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'True').lower() in ('true', '1', 'yes')
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'False').lower() in ('true', '1', 'yes')
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
FRONTEND_URL = os.getenv('FRONTEND_URL_PROD')

# CORS origins - comma-separated list in environment variable (REQUIRED in production)
CORS_ORIGINS = os.getenv('CORS_ORIGINS_PROD')
if not CORS_ORIGINS:
    raise ValueError("CORS_ORIGINS_PROD environment variable must be set in production")
CORS_ORIGINS = CORS_ORIGINS.split(',')

# Validate required production settings
if not all([MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER, FRONTEND_URL]):
    raise ValueError("Email configuration environment variables are required in production")
