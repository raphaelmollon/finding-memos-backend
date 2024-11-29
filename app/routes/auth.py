from flask import Blueprint, request, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash
from app.models.database import get_db_connection
from app.middleware import auth_required
import sqlite3
import json
import logging
from app.models.helpers import get_user_by_id

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/sign-in', methods=['POST'])
def sign_in():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    with get_db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Store user in session
        session['user_id'] = user['id']
        return jsonify({"message": "Logged in successfully", "user": {"email": user['email'], "is_superuser": bool(user['is_superuser'])}})

@auth_bp.route('/sign-up', methods=['POST'])
def sign_up():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # Check email domain
    with get_db_connection() as conn:
        config = conn.execute('SELECT allowed_domains FROM config WHERE id = 1').fetchone()
        allowed_domains = json.loads(config['allowed_domains'])
        domain = email.split('@')[-1]

        if domain not in allowed_domains:
            return jsonify({"error": f"Domain '@{domain}' not allowed"}), 403

        password_hash = generate_password_hash(password)
        try:
            conn.execute(
                'INSERT INTO users (email, password_hash) VALUES (?, ?)',
                (email, password_hash)
            )
            conn.commit()
            return jsonify({"message": "Sign-up successful"}), 201
        except sqlite3.IntegrityError:
            return jsonify({"error": "User already exists"}), 409

@auth_bp.route('/sign-out', methods=['POST'])
@auth_required
def sign_out():
    session.clear()
    return jsonify({"message": "Signed out successfully"})

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')

    # In production, send an email with a reset link/token
    return jsonify({"message": f"Password reset link sent to {email}"}), 200

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    new_password = data.get('new_password')

    password_hash = generate_password_hash(new_password)
    with get_db_connection() as conn:
        conn.execute('UPDATE users SET password_hash = ? WHERE email = ?', (password_hash, email))
        conn.commit()
        return jsonify({"message": "Password reset successful"}), 200

@auth_bp.route('/toggle-auth', methods=['POST'])
@auth_required
def toggle_auth():
    with get_db_connection() as conn:
        current_status = conn.execute('SELECT enable_auth FROM config WHERE id = 1').fetchone()
        new_status = not current_status['enable_auth']
        conn.execute('UPDATE config SET enable_auth = ? WHERE id = 1', (new_status,))
        conn.commit()
        return jsonify({"message": f"Authentication {'enabled' if new_status else 'disabled'}"})
    
@auth_bp.route('/session-check', methods=['GET'])
def session_check():
    logging.debug("Entering session_check")
    with get_db_connection() as conn:
        config = conn.execute('SELECT enable_auth FROM config WHERE id = 1').fetchone()
        if not config or not config['enable_auth']:    # Check if a timeout occurred
            return jsonify({"user": {"email": "no_auth@required", "is_superuser": True}})
    if session.get('session_timeout'):
        session.pop('session_timeout', None)  # Clear the flag
        return jsonify({"error": "Session timeout. Please log in again."}), 401
        
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        if user:
            return jsonify({"user": {"email": user["email"], "is_superuser": bool(user["is_superuser"])}})
        else:
            # User ID exists but no user found in DB
            return jsonify({"error": "User not found. Please log in again."}), 401
    
    # No user_id in session
    return jsonify({"error": "No active session"}), 401
