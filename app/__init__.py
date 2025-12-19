import logging
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_restx import Api
from app.middleware import add_session_timeout_flag, refresh_session
from app.routes import register_routes
from .database import db
from .limiter import limiter
import os

def create_app():

    app = Flask(__name__)

    # Load configuration first (needed for CORS_ORIGINS)
    is_production = os.environ.get('FLASK_ENV') == 'production'
    logging.debug(f"IS_PRODUCTION:{is_production}")
    if is_production:
        app.config.from_pyfile('config_prod.py')
    else:
        app.config.from_pyfile('config.py')

    # Configure CORS with origins from config
    CORS(app,
         supports_credentials=True,
         origins=app.config['CORS_ORIGINS'],
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
         expose_headers=["X-Session-Timeout"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         max_age=600
    )

    # Initialize the database
    db.init_app(app)
    migrate = Migrate(app, db)

    # Initialize rate limiter
    limiter.init_app(app)

    # Initialize Flask-RESTX API
    api = Api(
        app,
        version='1.0',
        title='Finding Memos API Documentation',
        description='API for managing memos and other stuff',
        doc='/docs/'
    )

    # Middleware
    app.before_request(refresh_session)
    app.after_request(add_session_timeout_flag)

    # Ensure tables exist
    with app.app_context():
        db.create_all()
        logging.info("Database initialized.")

    # Register routes
    register_routes(app, api)

    # Initialize services
    from app.services.email_service import email_service
    email_service.init_app(app)

    return app