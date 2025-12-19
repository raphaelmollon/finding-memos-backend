from flask import Blueprint, request, jsonify, session, g
from app.database import db
from app.models import Config, User
import logging
import datetime
from functools import wraps
from flask import current_app as app


middleware_bp = Blueprint('auth', __name__)

# Cache for auth configuration
_auth_config_cache = {'enable_auth': True, 'last_refresh': None}

def get_auth_config():
    """Get authentication config with caching to avoid DB queries on every request"""
    global _auth_config_cache

    # Refresh cache every 60 seconds or if never loaded
    now = datetime.datetime.now(datetime.timezone.utc)
    if (_auth_config_cache['last_refresh'] is None or
        (now - _auth_config_cache['last_refresh']).total_seconds() > 60):

        config = Config.query.filter_by(id=1).first()
        _auth_config_cache['enable_auth'] = config.enable_auth if config else True
        _auth_config_cache['last_refresh'] = now
        logging.debug("Refreshed auth config cache")

    return _auth_config_cache['enable_auth']

# Middleware to enforce authentication
@middleware_bp.before_request
def refresh_session():
    logging.debug("Entering refresh_session")
    if 'user_id' in session:  # Ensure there's an active session
        last_activity = session.get('last_activity')
        now = datetime.datetime.now(datetime.timezone.utc)

        # If the user has been inactive for too long, log them out
        if last_activity and (now - last_activity).total_seconds() > app.config['TIMEOUT_DELAY']:
            logging.info(f"Session timeout for user {session['user_id']} due to inactivity.")
            session.clear()  # Clear entire session to avoid partial state

            # Inject session timeout into the response context
            g.session_timeout = True
            return  # Exit early - don't update last_activity for timed-out sessions

        # Only update activity for valid, active sessions
        session['last_activity'] = now
        session.permanent = True
        app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=app.config['LIFETIME_DELAY'])
    else:
        g.session_timeout = False
        logging.info("No active user session.")

# Middleware to enforce authentication
def auth_required(f):
    logging.debug("Entering auth_required")
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if authentication is enabled (cached to avoid DB query on every request)
        if not get_auth_config():
            return f(*args, **kwargs)  # Auth not enforced
        
        # Check session for logged-in user
        user_id = session.get('user_id')
        if not user_id:
            return {"error": "Authentication required"}, 401

        # Get user through SQLAlchemy
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return {"error": "Invalid session"}, 401
        # Attach user information to the global `g` object for route use
        g.user = user

        return f(*args, **kwargs)
    return decorated_function


@middleware_bp.after_request
def add_session_timeout_flag(response):
    logging.debug("Entering add_session_timeout_flag")

    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Expose-Headers"] = "X-Session-Timeout"  # Expose this header

    if hasattr(g, 'session_timeout') and g.session_timeout:
        logging.info('Send timeout flag to frontend')
        response.headers['X-Session-Timeout'] = 'true'

    return response
