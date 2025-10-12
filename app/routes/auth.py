from flask import request, session
from flask_restx import Namespace, Resource, fields
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import db
from app.models import User, Config
from app.middleware import auth_required

import json
import logging

auth_ns = Namespace('auth', description="Authentication operations")

login_model = auth_ns.model('Login', {
    'email': fields.String(required=True, description='User email'),
    'password': fields.String(required=True, description='User password')
})

signup_model = auth_ns.model('SignUp', {
    'email': fields.String(required=True, description='User email'),
    'password': fields.String(required=True, description='User password')
})

user_response_model = auth_ns.model('User', {
    'email': fields.String(description='User email'),
    'username': fields.String(description='Username'),
    'is_superuser': fields.Boolean(description='Is superuser')
})

message_response_model = auth_ns.model('MessageResponse', {
    'message': fields.String(description='Response message')
})

error_response_model = auth_ns.model('ErrorResponse', {
    'error': fields.String(description='Error message')
})


# Routes RESTX
@auth_ns.route('/sign-in')
class SignIn(Resource):
    @auth_ns.expect(login_model)
    @auth_ns.response(200, 'Success', user_response_model)
    @auth_ns.response(400, 'Bad Request', error_response_model)
    @auth_ns.response(401, 'Invalid credentials', error_response_model)
    def post(self):
        """Sign in a user"""
        logging.debug("Entering sign-in...")
        try:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                return {"error": "Email and password are required"}, 400

            user = User.query.filter_by(email=email).first()
            if not user or not check_password_hash(user.password_hash, password):
                return {"error": "Invalid credentials"}, 401

            session['user_id'] = user.id
            logging.debug(f"Session created for user {user.id}")
            
            return {
                "message": "Logged in successfully", 
                "user": {
                    "email": user.email, 
                    "is_superuser": user.is_superuser,
                    "username": user.username
                }
            }, 200
            
        except Exception as e:
            logging.error(f"Sign-in error: {e}")
            return {"error": "Authentication failed"}, 500

@auth_ns.route('/sign-up')
class SignUp(Resource):
    @auth_ns.expect(signup_model)
    @auth_ns.response(201, 'User created', message_response_model)
    @auth_ns.response(400, 'Bad Request', error_response_model)
    @auth_ns.response(403, 'Domain not allowed', error_response_model)
    @auth_ns.response(409, 'User already exists', error_response_model)
    def post(self):
        """Sign up a new user"""
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return {"error": "Email and password are required"}, 400

        # Check email domain
        config = Config.query.filter_by(id=1).first()
        if not config:
            return {"error": "Configuration not found"}, 500
            
        allowed_domains = json.loads(config.allowed_domains)
        domain = email.split('@')[-1]

        if domain not in allowed_domains:
            return {"error": f"Domain '@{domain}' not allowed"}, 403

        # Check if user exists
        if User.query.filter_by(email=email).first():
            return {"error": "User already exists"}, 409

        # Create user
        try:
            password_hash = generate_password_hash(password)
            new_user = User(email=email, password_hash=password_hash)
            db.session.add(new_user)
            db.session.commit()
            return {"message": "Sign-up successful"}, 201
        except Exception as e:
            db.session.rollback()
            logging.error(f"Sign-up error: {e}")
            return {"error": "Registration failed"}, 500

@auth_ns.route('/sign-out')
class SignOut(Resource):
    @auth_required
    @auth_ns.response(200, 'Signed out', message_response_model)
    def post(self):
        """Sign out the current user"""
        session.clear()
        return {"message": "Signed out successfully"}, 200

@auth_ns.route('/forgot-password')
class ForgotPassword(Resource):
    @auth_ns.expect(auth_ns.model('ForgotPassword', {
        'email': fields.String(required=True)
    }))
    @auth_ns.response(200, 'Reset link sent', message_response_model)
    def post(self):
        """Request password reset"""
        data = request.get_json()
        email = data.get('email')

        # In production, send an email with a reset link/token
        return {"message": f"Password reset link sent to {email}"}, 200

@auth_ns.route('/reset-password')
class ResetPassword(Resource):
    @auth_ns.expect(auth_ns.model('ResetPassword', {
        'email': fields.String(required=True),
        'new_password': fields.String(required=True)
    }))
    @auth_ns.response(200, 'Password reset', message_response_model)
    @auth_ns.response(404, 'User not found', error_response_model)
    def post(self):
        """Reset user password"""
        data = request.get_json()
        email = data.get('email')
        new_password = data.get('new_password')

        user = User.query.filter_by(email=email).first()
        if not user:
            return {"error": "User not found"}, 404

        try:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            return {"message": "Password reset successful"}, 200
        except Exception as e:
            db.session.rollback()
            logging.error(f"Password reset error: {e}")
            return {"error": "Password reset failed"}, 500

@auth_ns.route('/toggle-auth')
class ToggleAuth(Resource):
    @auth_required
    @auth_ns.response(200, 'Auth toggled', message_response_model)
    @auth_ns.response(403, 'Forbidden', error_response_model)
    def post(self):
        """Toggle authentication (superuser only)"""
        from flask import g
        if not g.user.is_superuser:
            return {"error": "Superuser required"}, 403

        config = Config.query.filter_by(id=1).first()
        if not config:
            return {"error": "Configuration not found"}, 404

        try:
            config.enable_auth = not config.enable_auth
            db.session.commit()
            return {
                "message": f"Authentication {'enabled' if config.enable_auth else 'disabled'}"
            }, 200
        except Exception as e:
            db.session.rollback()
            logging.error(f"Toggle auth error: {e}")
            return {"error": "Failed to update authentication setting"}, 500

@auth_ns.route('/session-check')
class SessionCheck(Resource):
    @auth_ns.response(200, 'Session valid', user_response_model)
    @auth_ns.response(401, 'No active session', error_response_model)
    def get(self):
        """Check current session status"""
        logging.debug("Entering session-check")
        
        # Vérifier si l'authentification est activée
        config = Config.query.filter_by(id=1).first()
        if not config or not config.enable_auth:
            return {"user": {"email": "no_auth@required", "is_superuser": True}}, 200
        
        if session.get('session_timeout'):
            session.pop('session_timeout', None)
            return {"error": "Session timeout. Please log in again."}, 401
            
        if 'user_id' in session:
            user = User.query.filter_by(id=session['user_id']).first()
            if user:
                return {
                    "user": {
                        "email": user.email, 
                        "is_superuser": user.is_superuser,
                        "username": user.username
                    }
                }, 200
            else:
                return {"error": "User not found. Please log in again."}, 401
        
        return {"error": "No active session"}, 401


