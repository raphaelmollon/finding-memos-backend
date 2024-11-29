from flask import Blueprint, jsonify, g
from app.models.database import get_db_connection
from app.middleware import auth_required
from app.middleware import auth_required

users_bp = Blueprint('users', __name__)

@users_bp.route('/me', methods=['GET'])
@auth_required
def get_current_user():
    return jsonify({"user": {"email": g.user['email'], "is_superuser": bool(g.user['is_superuser'])}})

# Route to list all users
@users_bp.route('/', methods=['GET'])
@auth_required
def get_users():
    with get_db_connection() as conn:
        users = conn.execute('''
            SELECT * FROM users
        ''').fetchall()

    return jsonify([dict(user) for user in users])


