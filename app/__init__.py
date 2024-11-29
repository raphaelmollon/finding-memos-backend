from flask import Flask
from flask_cors import CORS
from app.models.database import init_db
from app.middleware import add_session_timeout_flag, refresh_session
import logging
from app.routes import register_routes

def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True, origins=["http://localhost:8080", "http://127.0.0.1:8080", "https://finding-memos.rm-info.fr"])

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )

    app.config.from_pyfile('config.py')

    # Middleware
    app.before_request(refresh_session)
    app.after_request(add_session_timeout_flag)

    # Initialize the database
    init_db()

    # Register routes
    register_routes(app)

    return app