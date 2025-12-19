from flask import request, session
from flask_restx import Namespace, Resource, fields
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import db
from app.models import User, Config
from app.middleware import auth_required, get_auth_config
from app.helpers import validate_password
from app.services.token_service import token_service
from app.services.email_service import email_service
from app.limiter import limiter

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
    decorators = [limiter.limit("5 per minute")]

    @auth_ns.expect(login_model)
    @auth_ns.response(200, 'Success', user_response_model)
    @auth_ns.response(400, 'Bad Request', error_response_model)
    @auth_ns.response(401, 'Invalid credentials', error_response_model)
    @auth_ns.response(403, 'User not validated', error_response_model)
    @auth_ns.response(429, 'Too many requests', error_response_model)
    @auth_ns.response(500, 'Server internal error', error_response_model)
    @auth_ns.doc(description="Rate limit: 5 per minute")
    def post(self):
        """Sign in a user"""
        logging.debug("Entering sign-in...")
        try:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                return {"error": "Email and password are required"}, 400
            logging.debug(f"Sign-in attempt for email: {email}")

            user = User.query.filter_by(email=email).first()
            if user:
                logging.debug(f"Found user: {user.email}")
            if not user or not check_password_hash(user.password_hash, password):
                return {"error": "Invalid credentials"}, 401
            logging.debug("AFTER existing user check")
        
            if user and user.status == 'NEW':
                return {"error": "Please validate your email address before logging in"}, 403
            if user and user.status == 'CLOSED':
                return {"error": "Your account is closed"}, 403
            if user and user.status != 'VALID':
                return {"error": "Account status is invalid. Please contact support."}, 403
            logging.debug("AFTER status check")

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
    decorators = [limiter.limit("3 per hour")]

    @auth_ns.expect(signup_model)
    @auth_ns.response(201, 'User created', message_response_model)
    @auth_ns.response(400, 'Bad Request', error_response_model)
    @auth_ns.response(403, 'Domain not allowed', error_response_model)
    @auth_ns.response(409, 'User already exists', error_response_model)
    @auth_ns.response(429, 'Too many requests', error_response_model)
    @auth_ns.doc(description="Rate limit: 3 per hour")
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
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            if existing_user.status == 'NEW':
                try:
                    new_token = token_service.generate_signup_token(existing_user.id)
                    existing_user.email_validation_token = token_service.hash_token(new_token)

                    email_sent = email_service.send_email_validation(email, new_token)
                    if email_sent:
                        db.session.commit()
                        return {"message": f"You already registered but didn't validate your email address. A new link has been sent to {email}."}, 200
                    else:
                        db.session.rollback()
                        return {"error": "User already registered, but didn't validate your email address. Failed to renew the validation link"}, 500
                    
                except Exception as e:
                    db.session.rollback()
                    logging.error(f"Failed to resend the validation link: {e}")
                    return {"error": "Failed to process validation requests"}, 500
            else:
                return {"error": "User already exists"}, 409

        # Check if password is strong enough
        password_error = validate_password(password)
        if password_error:
            return {"error": password_error}, 400

        # Create user
        try:
            password_hash = generate_password_hash(password)
            new_user = User(email=email, password_hash=password_hash, status="NEW")
            db.session.add(new_user)
            db.session.flush()
            token = token_service.generate_signup_token(new_user.id)
            new_user.email_validation_token = token_service.hash_token(token)
            email_sent = email_service.send_email_validation(email, token)
            if email_sent:
                db.session.commit()
                return {"message": "Sign-up successful. Please check your emails and confirm registration."}, 201
            else:
                db.session.rollback()
                return {"error": "Registration failed. Please try again in a moment."}, 500
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
    decorators = [limiter.limit("3 per hour")]

    @auth_ns.expect(auth_ns.model('ForgotPassword', {
        'email': fields.String(required=True, description="User email")
    }))
    @auth_ns.response(200, 'Reset link sent', message_response_model)
    @auth_ns.response(400, "Bad request", error_response_model)
    @auth_ns.response(429, 'Too many requests', error_response_model)
    @auth_ns.response(500, "Internal server error", error_response_model)
    @auth_ns.doc(description="Rate limit: 3 per hour")
    def post(self):
        """Request password reset"""
        data = request.get_json()
        email = data.get('email')

        if not email:
            return {"error": "Email is required"}, 400

        try:
            user = User.query.filter_by(email=email).first()
            if user:
                # Generate a new token
                reset_token = token_service.generate_reset_token(user.id)

                # Store the hashed token (security: only hash is stored in DB)
                user.reset_token = token_service.hash_token(reset_token)
                db.session.commit()

                # send the email
                email_sent = email_service.send_password_reset(email, reset_token)

                if email_sent:
                    return {"message": "Reset instructions sent"}, 200
                else:
                    return {"error": "Failed to send reset_email"}, 500
            else:
                return {"message": "If this email exists, reset instructions have been sent"}, 200
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error in forgot-password: {e}")
            return {"error": "Failed to process reset request"}, 500

@auth_ns.route('/reset-password')
class ResetPassword(Resource):
    decorators = [limiter.limit("10 per hour")]

    @auth_ns.expect(auth_ns.model('ResetPassword', {
        'token': fields.String(required=True, description="Reset token from email"),
        'new_password': fields.String(required=True, description="New password", min_length=8)
    }))
    @auth_ns.response(200, 'Password reset', message_response_model)
    @auth_ns.response(400, 'Invalid or expired token', error_response_model)
    @auth_ns.response(404, 'User not found', error_response_model)
    @auth_ns.response(429, 'Too many requests', error_response_model)
    @auth_ns.response(500, 'Internal server error', error_response_model)
    @auth_ns.doc(description="Rate limit: 10 per hour")
    def post(self):
        """Reset password with secure token"""
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('new_password')

        # Validate new password
        password_error = validate_password(new_password)
        if password_error:
            return {"error": password_error}, 400

        if not token or not new_password:
            return {"error": "Token and new password are required"}, 400
        
        try:
            # from app.services.token_service import token_service
            user_id = token_service.validate_reset_token(token)

            if not user_id:
                return {"error": "Invalid or expired reset token"}, 400

            user = User.query.filter_by(id=user_id).first()
            if not user or not user.reset_token:
                return {"error": "Invalid or expired reset token"}, 400

            # Check that token hashes match (security: compare hashed values)
            if user.reset_token != token_service.hash_token(token):
                return {"error": "Invalid reset token"}, 400
            
            # Update password
            user.password_hash = generate_password_hash(new_password)
            user.reset_token = None
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

        # Check if authentication is enabled (using cached config)
        if not get_auth_config():
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

@auth_ns.route('/validate-email')
class ValidateEmail(Resource):
    @auth_ns.expect(auth_ns.model('ValidateEmail', {
        'token': fields.String(required=True, description="Email validation token"),
        'password': fields.String(required=True, description="Password confirmation")
    }))
    @auth_ns.response(200, 'Email validated', message_response_model)
    @auth_ns.response(400, 'Invalid or expired token', error_response_model)
    @auth_ns.response(404, 'User not found', error_response_model)
    @auth_ns.response(500, 'Internal server error', error_response_model)
    def post(self):
        """Validate email with secure token and password confirmation"""
        data = request.get_json()
        token = data.get('token')
        password = data.get('password')

        if not token:
            return {"error": "Token is required"}, 400
        
        try:
            user_id = token_service.validate_signup_token(token)

            if not user_id:
                return {"error": "Invalid or expired validation token"}, 400

            user = User.query.filter_by(id=user_id, status="NEW").first()
            if not user or not user.email_validation_token:
                return {"error": "Invalid or expired validation token"}, 400

            # Check that token hashes match (security: compare hashed values)
            if user.email_validation_token != token_service.hash_token(token):
                return {"error": "Invalid validation token"}, 400
            
            from werkzeug.security import check_password_hash
            if not check_password_hash(user.password_hash, password):
                return {"error": "Invalid password"}, 400
            
            # Update status
            user.status = "VALID"
            user.email_validation_token = None
            db.session.commit()
            return {"message": "Email validation successful"}, 200
        
        except Exception as e:
            db.session.rollback()
            logging.error(f"Email validation error: {e}")
            return {"error": "Email validation failed"}, 500

@auth_ns.route('/resend-validation')
class ResendValidation(Resource):
    decorators = [limiter.limit("3 per hour")]

    @auth_ns.expect(auth_ns.model('EmailValidation', {
        'email': fields.String(required=True, description='User email')
    }))
    @auth_ns.response(200, 'Email resent', message_response_model)
    @auth_ns.response(400, 'Invalid request', error_response_model)
    @auth_ns.response(404, 'User not found', error_response_model)
    @auth_ns.response(429, 'Too many requests', error_response_model)
    @auth_ns.response(500, 'Internal server error', error_response_model)
    @auth_ns.doc(description="Rate limit: 3 per hour")
    def post(self):
        """Resend the validation email with a new token"""
        try:
            data = request.get_json()
            email = data.get('email')

            user = User.query.filter_by(email=email, status='NEW').first()
            if not user:
                return {"error": "No pending validation found for this email"}, 400

            new_token = token_service.generate_signup_token(user.id)
            user.email_validation_token = token_service.hash_token(new_token)

            email_sent = email_service.send_email_validation(email, new_token)
            if email_sent:
                db.session.commit()
                return {"message": "New validation email sent"}, 200
            else:
                db.session.rollback()
                return {"error": "Failed to send a new validation email"}, 500
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Failed to send a validation email: {e}")
            return {"error": "Failed to resend the validation email"}, 500

