import os
import datetime


LIFETIME_DELAY = 15     # in days
TIMEOUT_DELAY = 24*3600 # 1 day in seconds
DATABASE_FILE = "memos.db"

SECRET_KEY = os.urandom(24)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'None'  # Or 'Strict' for tighter security
SESSION_COOKIE_SECURE = True  # Set to FALSE in Production
PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=LIFETIME_DELAY)  # Adjust as needed

SQLALCHEMY_DATABASE_URI = "sqlite:///memos.db"