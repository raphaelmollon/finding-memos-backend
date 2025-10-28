from flask import Blueprint, request, jsonify, session, g
from app.database import db
from app.models import Config, User
import logging
import datetime
from functools import wraps
from flask import current_app as app


middleware_bp = Blueprint('auth', __name__)

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
            session.pop('user_id', None)  # Remove authentication

            # Inject session timeout into the response context
            g.session_timeout = True

        session['last_activity'] = now  # Update activity
        session.permanent = True  # Mark session as permanent
        app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=app.config['LIFETIME_DELAY'])  # Extend session duration
    else:
        g.session_timeout = False
        logging.info("No active user session.")

# Middleware to enforce authentication
def auth_required(f):
    logging.debug("Entering auth_required")
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if authentication is enabled
        config = Config.query.filter_by(id=1).first()
        if not config or not config.enable_auth:
            return f(*args, **kwargs)  # Auth not enforced
        
        # Check session for logged-in user
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
        
        # Get user through SQLAlchemy
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "Invalid session"}), 401
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
