import pytest
import json
from app.models import User, Config
from app.database import db
from app.services.token_service import token_service
from werkzeug.security import generate_password_hash


class TestSignIn:
    """Test sign-in endpoint."""

    def test_sign_in_success(self, client, test_user):
        """Test successful sign-in."""
        response = client.post('/auth/sign-in', json={
            'email': 'test@test.com',
            'password': 'TestPassword123!'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert 'user' in data
        assert data['user']['email'] == 'test@test.com'

    def test_sign_in_invalid_credentials(self, client, test_user):
        """Test sign-in with wrong password."""
        response = client.post('/auth/sign-in', json={
            'email': 'test@test.com',
            'password': 'WrongPassword123!'
        })

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid credentials' in data['error']

    def test_sign_in_nonexistent_user(self, client):
        """Test sign-in with non-existent email."""
        response = client.post('/auth/sign-in', json={
            'email': 'nonexistent@test.com',
            'password': 'Password123!'
        })

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data

    def test_sign_in_missing_email(self, client):
        """Test sign-in without email."""
        response = client.post('/auth/sign-in', json={
            'password': 'Password123!'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_sign_in_missing_password(self, client):
        """Test sign-in without password."""
        response = client.post('/auth/sign-in', json={
            'email': 'test@test.com'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_sign_in_new_user(self, client, new_user):
        """Test sign-in with unvalidated user."""
        response = client.post('/auth/sign-in', json={
            'email': 'newuser@test.com',
            'password': 'NewPassword123!'
        })

        assert response.status_code == 403
        data = json.loads(response.data)
        assert 'error' in data
        assert 'validate your email' in data['error']

    def test_sign_in_closed_user(self, app, client, db_session):
        """Test sign-in with closed account."""
        with app.app_context():
            user = User(
                email='closed@test.com',
                password_hash=generate_password_hash('Password123!'),
                status='CLOSED'
            )
            db.session.add(user)
            db.session.commit()

        response = client.post('/auth/sign-in', json={
            'email': 'closed@test.com',
            'password': 'Password123!'
        })

        assert response.status_code == 403
        data = json.loads(response.data)
        assert 'closed' in data['error']


class TestSignUp:
    """Test sign-up endpoint."""

    def test_sign_up_success(self, app, client, db_session):
        """Test successful sign-up."""
        response = client.post('/auth/sign-up', json={
            'email': 'newuser@test.com',
            'password': 'ValidPassword123!'
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'message' in data
        assert 'Sign-up successful' in data['message']

        # Verify user was created
        with app.app_context():
            user = User.query.filter_by(email='newuser@test.com').first()
            assert user is not None
            assert user.status == 'NEW'

    def test_sign_up_weak_password(self, client, db_session):
        """Test sign-up with weak password."""
        response = client.post('/auth/sign-up', json={
            'email': 'newuser@test.com',
            'password': 'weak'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_sign_up_duplicate_email(self, client, test_user):
        """Test sign-up with existing email."""
        response = client.post('/auth/sign-up', json={
            'email': 'test@test.com',
            'password': 'ValidPassword123!'
        })

        assert response.status_code == 409
        data = json.loads(response.data)
        assert 'error' in data
        assert 'already exists' in data['error']

    def test_sign_up_invalid_domain(self, client, db_session):
        """Test sign-up with disallowed email domain."""
        response = client.post('/auth/sign-up', json={
            'email': 'user@invalid.com',
            'password': 'ValidPassword123!'
        })

        assert response.status_code == 403
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Domain' in data['error'] and 'not allowed' in data['error']

    def test_sign_up_missing_email(self, client):
        """Test sign-up without email."""
        response = client.post('/auth/sign-up', json={
            'password': 'ValidPassword123!'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_sign_up_missing_password(self, client):
        """Test sign-up without password."""
        response = client.post('/auth/sign-up', json={
            'email': 'newuser@test.com'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_sign_up_resend_validation_for_new_user(self, app, client, new_user):
        """Test sign-up with existing NEW user resends validation."""
        response = client.post('/auth/sign-up', json={
            'email': 'newuser@test.com',
            'password': 'ValidPassword123!'
        })

        # Should send a new validation email instead of error
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'already registered' in data['message']


class TestSignOut:
    """Test sign-out endpoint."""

    def test_sign_out_success(self, authenticated_client):
        """Test successful sign-out."""
        response = authenticated_client.post('/auth/sign-out')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert 'Signed out' in data['message']

    def test_sign_out_unauthenticated(self, client):
        """Test sign-out without being logged in."""
        response = client.post('/auth/sign-out')

        assert response.status_code == 401


class TestForgotPassword:
    """Test forgot-password endpoint."""

    def test_forgot_password_success(self, app, client, test_user):
        """Test forgot password with valid email."""
        response = client.post('/auth/forgot-password', json={
            'email': 'test@test.com'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

        # Verify reset token was set
        with app.app_context():
            user = User.query.filter_by(email='test@test.com').first()
            assert user.reset_token is not None

    def test_forgot_password_nonexistent_email(self, client):
        """Test forgot password with non-existent email."""
        response = client.post('/auth/forgot-password', json={
            'email': 'nonexistent@test.com'
        })

        # Should return success to avoid user enumeration
        assert response.status_code == 200

    def test_forgot_password_missing_email(self, client):
        """Test forgot password without email."""
        response = client.post('/auth/forgot-password', json={})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


class TestResetPassword:
    """Test reset-password endpoint."""

    def test_reset_password_success(self, app, client, test_user):
        """Test successful password reset."""
        with app.app_context():
            # Get the user from DB
            user = User.query.filter_by(id=test_user.id).first()
            # Generate a reset token
            reset_token = token_service.generate_reset_token(user.id)
            user.reset_token = token_service.hash_token(reset_token)
            db.session.commit()

        response = client.post('/auth/reset-password', json={
            'token': reset_token,
            'new_password': 'NewPassword123!'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert 'successful' in data['message']

        # Verify reset token was cleared
        with app.app_context():
            user = User.query.filter_by(id=test_user.id).first()
            assert user.reset_token is None

    def test_reset_password_invalid_token(self, client):
        """Test reset password with invalid token."""
        response = client.post('/auth/reset-password', json={
            'token': 'invalid-token',
            'new_password': 'NewPassword123!'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_reset_password_weak_password(self, app, client, test_user):
        """Test reset password with weak password."""
        with app.app_context():
            user = User.query.filter_by(id=test_user.id).first()
            reset_token = token_service.generate_reset_token(user.id)
            user.reset_token = token_service.hash_token(reset_token)
            db.session.commit()

        response = client.post('/auth/reset-password', json={
            'token': reset_token,
            'new_password': 'weak'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_reset_password_missing_fields(self, client):
        """Test reset password with missing fields."""
        response = client.post('/auth/reset-password', json={
            'token': 'some-token'
        })

        assert response.status_code == 400


class TestSessionCheck:
    """Test session-check endpoint."""

    def test_session_check_authenticated(self, authenticated_client, test_user):
        """Test session check when authenticated."""
        response = authenticated_client.get('/auth/session-check')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'user' in data
        assert data['user']['email'] == 'test@test.com'

    def test_session_check_unauthenticated(self, client):
        """Test session check when not authenticated."""
        response = client.get('/auth/session-check')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data

    def test_session_check_auth_disabled(self, client, disable_auth):
        """Test session check when auth is disabled."""
        response = client.get('/auth/session-check')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'user' in data


class TestValidateEmail:
    """Test validate-email endpoint."""

    def test_validate_email_success(self, app, client, new_user):
        """Test successful email validation."""
        with app.app_context():
            # Get user from DB
            user = User.query.filter_by(id=new_user.id).first()
            # Generate validation token
            validation_token = token_service.generate_signup_token(user.id)
            user.email_validation_token = token_service.hash_token(validation_token)
            db.session.commit()

        response = client.post('/auth/validate-email', json={
            'token': validation_token,
            'password': 'NewPassword123!'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert 'successful' in data['message']

        # Verify user status changed to VALID
        with app.app_context():
            user = User.query.filter_by(id=new_user.id).first()
            assert user.status == 'VALID'
            assert user.email_validation_token is None

    def test_validate_email_invalid_token(self, client):
        """Test email validation with invalid token."""
        response = client.post('/auth/validate-email', json={
            'token': 'invalid-token',
            'password': 'Password123!'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_validate_email_wrong_password(self, app, client, new_user):
        """Test email validation with wrong password."""
        with app.app_context():
            user = User.query.filter_by(id=new_user.id).first()
            validation_token = token_service.generate_signup_token(user.id)
            user.email_validation_token = token_service.hash_token(validation_token)
            db.session.commit()

        response = client.post('/auth/validate-email', json={
            'token': validation_token,
            'password': 'WrongPassword123!'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'password' in data['error'].lower()


class TestResendValidation:
    """Test resend-validation endpoint."""

    def test_resend_validation_success(self, app, client, new_user):
        """Test successful resend validation."""
        response = client.post('/auth/resend-validation', json={
            'email': 'newuser@test.com'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

    def test_resend_validation_no_pending(self, client, test_user):
        """Test resend validation for user without pending validation."""
        response = client.post('/auth/resend-validation', json={
            'email': 'test@test.com'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


class TestToggleAuth:
    """Test toggle-auth endpoint."""

    def test_toggle_auth_as_superuser(self, app, superuser_client):
        """Test toggling auth as superuser."""
        response = superuser_client.post('/auth/toggle-auth')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

    def test_toggle_auth_as_regular_user(self, authenticated_client):
        """Test toggling auth as regular user."""
        response = authenticated_client.post('/auth/toggle-auth')

        assert response.status_code == 403
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Superuser required' in data['error']

    def test_toggle_auth_unauthenticated(self, client):
        """Test toggling auth without authentication."""
        response = client.post('/auth/toggle-auth')

        assert response.status_code == 401
