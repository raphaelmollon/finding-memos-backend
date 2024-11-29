from flask import Blueprint

from .auth import auth_bp
from .memos import memos_bp
from .categories import categories_bp
from .types import types_bp
from .users import users_bp
from .globals import global_bp

def register_routes(app):
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(memos_bp, url_prefix='/memos')
    app.register_blueprint(categories_bp, url_prefix='/categories')
    app.register_blueprint(types_bp, url_prefix='/types')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(global_bp, url_prefix='/global')
