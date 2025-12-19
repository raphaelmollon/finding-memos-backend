import pytest
import json
from app.models import User, Memo, Category, Type
from app.database import db
from app.services.token_service import token_service


class TestUserSignupFlow:
    """Test complete user signup and validation flow."""

    def test_complete_signup_flow(self, app, client, db_session):
        """Test complete signup flow: register -> validate -> login."""
        # Step 1: Sign up
        signup_response = client.post('/auth/sign-up', json={
            'email': 'newuser@test.com',
            'password': 'ValidPassword123!'
        })

        assert signup_response.status_code == 201

        # Verify user was created with NEW status
        with app.app_context():
            user = User.query.filter_by(email='newuser@test.com').first()
            assert user is not None
            assert user.status == 'NEW'
            user_id = user.id

            # Generate validation token manually (simulating email link)
            validation_token = token_service.generate_signup_token(user.id)
            user.email_validation_token = token_service.hash_token(validation_token)
            db.session.commit()

        # Step 2: Try to login before validation (should fail)
        login_response = client.post('/auth/sign-in', json={
            'email': 'newuser@test.com',
            'password': 'ValidPassword123!'
        })

        assert login_response.status_code == 403
        data = json.loads(login_response.data)
        assert 'validate your email' in data['error']

        # Step 3: Validate email
        validate_response = client.post('/auth/validate-email', json={
            'token': validation_token,
            'password': 'ValidPassword123!'
        })

        assert validate_response.status_code == 200

        # Verify user status changed to VALID
        with app.app_context():
            user = User.query.filter_by(id=user_id).first()
            assert user.status == 'VALID'

        # Step 4: Login after validation (should succeed)
        login_response = client.post('/auth/sign-in', json={
            'email': 'newuser@test.com',
            'password': 'ValidPassword123!'
        })

        assert login_response.status_code == 200
        data = json.loads(login_response.data)
        assert 'user' in data
        assert data['user']['email'] == 'newuser@test.com'


class TestPasswordResetFlow:
    """Test complete password reset flow."""

    def test_complete_password_reset_flow(self, app, client, test_user):
        """Test complete password reset: request -> reset -> login."""
        # Step 1: Request password reset
        forgot_response = client.post('/auth/forgot-password', json={
            'email': 'test@test.com'
        })

        assert forgot_response.status_code == 200

        # Get the reset token from database
        with app.app_context():
            user = User.query.filter_by(email='test@test.com').first()
            assert user.reset_token is not None

            # Generate a valid reset token
            reset_token = token_service.generate_reset_token(user.id)
            user.reset_token = token_service.hash_token(reset_token)
            db.session.commit()

        # Step 2: Try to login with old password (should work)
        login_response = client.post('/auth/sign-in', json={
            'email': 'test@test.com',
            'password': 'TestPassword123!'
        })

        assert login_response.status_code == 200

        # Logout
        client.post('/auth/sign-out')

        # Step 3: Reset password
        reset_response = client.post('/auth/reset-password', json={
            'token': reset_token,
            'new_password': 'NewPassword456!'
        })

        assert reset_response.status_code == 200

        # Step 4: Try to login with old password (should fail)
        login_response = client.post('/auth/sign-in', json={
            'email': 'test@test.com',
            'password': 'TestPassword123!'
        })

        assert login_response.status_code == 401

        # Step 5: Login with new password (should succeed)
        login_response = client.post('/auth/sign-in', json={
            'email': 'test@test.com',
            'password': 'NewPassword456!'
        })

        assert login_response.status_code == 200


class TestMemoLifecycle:
    """Test complete memo lifecycle."""

    def test_memo_crud_flow(self, app, authenticated_client, db_session):
        """Test creating, reading, updating, and deleting a memo."""
        # Step 1: Create memo
        create_response = authenticated_client.post('/memos', json={
            'name': 'Integration Test Memo',
            'description': 'Testing full lifecycle',
            'content': 'Original content',
            'category_name': 'Integration',
            'type_name': 'Test'
        })

        assert create_response.status_code == 201

        # Get memo ID
        with app.app_context():
            memo = Memo.query.filter_by(name='Integration Test Memo').first()
            assert memo is not None
            memo_id = memo.id
            category_id = memo.category_id
            type_id = memo.type_id

        # Step 2: Read memo (in list)
        list_response = authenticated_client.get('/memos')
        assert list_response.status_code == 200
        memos = json.loads(list_response.data)
        assert any(m['id'] == memo_id for m in memos)

        # Step 3: Update memo
        update_response = authenticated_client.put(f'/memos/{memo_id}', json={
            'name': 'Updated Memo',
            'content': 'Updated content',
            'category_name': 'New Category',
            'type_name': 'New Type',
            'author_id': memo.author_id
        })

        assert update_response.status_code == 200

        # Verify update
        with app.app_context():
            memo = Memo.query.filter_by(id=memo_id).first()
            assert memo.name == 'Updated Memo'
            assert memo.content == 'Updated content'

        # Step 4: Delete memo
        delete_response = authenticated_client.delete(f'/memos/{memo_id}')
        assert delete_response.status_code == 200

        # Verify deletion
        with app.app_context():
            memo = Memo.query.filter_by(id=memo_id).first()
            assert memo is None


class TestUserProfile:
    """Test user profile management."""

    def test_user_profile_workflow(self, app, authenticated_client, test_user):
        """Test updating user profile and preferences."""
        # Step 1: Get current profile
        response = authenticated_client.get('/users/me')
        assert response.status_code == 200
        data = json.loads(response.data)
        original_username = data['user']['username']

        # Step 2: Update username
        response = authenticated_client.put('/users/me', json={
            'username': 'updated_username'
        })
        assert response.status_code == 200

        # Step 3: Update preferences
        response = authenticated_client.put('/users/me/preferences', json={
            'preferences': {
                'theme': {'color': 'dark'},
                'notifications': {'enabled': True}
            }
        })
        assert response.status_code == 200

        # Step 4: Get section preferences
        response = authenticated_client.get('/users/me/preferences/theme')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['preferences']['color'] == 'dark'

        # Step 5: Update section preferences
        response = authenticated_client.put('/users/me/preferences/theme', json={
            'preferences': {'color': 'light', 'font': 'large'}
        })
        assert response.status_code == 200

        # Verify full preferences
        response = authenticated_client.get('/users/me/preferences')
        data = json.loads(response.data)
        assert data['preferences']['theme']['color'] == 'light'
        assert data['preferences']['notifications']['enabled'] is True


class TestAuthenticationStates:
    """Test authentication state transitions."""

    def test_auth_toggle_workflow(self, app, superuser, client, db_session):
        """Test toggling authentication on and off."""
        from app.middleware import _auth_config_cache

        # Explicitly ensure auth is enabled at start
        with app.app_context():
            from app.models import Config
            config = Config.query.filter_by(id=1).first()
            config.enable_auth = True
            db_session.commit()

        # Force cache to refresh from database
        _auth_config_cache['last_refresh'] = None

        # Step 1: Verify auth is enabled (should return 401 when not authenticated)
        response = client.get('/auth/session-check')
        assert response.status_code == 401  # Not authenticated

        # Create authenticated superuser client
        with client.session_transaction() as sess:
            sess['user_id'] = superuser.id

        # Step 2: Toggle auth off
        response = client.post('/auth/toggle-auth')
        assert response.status_code == 200

        # Force cache refresh by clearing last_refresh
        _auth_config_cache['last_refresh'] = None

        # Clear session for next test
        with client.session_transaction() as sess:
            sess.clear()

        # Step 3: Access endpoint without auth (should work now)
        response = client.get('/auth/session-check')
        # Should return success when auth is disabled
        data = json.loads(response.data)
        assert 'user' in data

        # Re-authenticate as superuser
        with client.session_transaction() as sess:
            sess['user_id'] = superuser.id

        # Step 4: Toggle auth back on
        response = client.post('/auth/toggle-auth')
        assert response.status_code == 200

        # Force cache refresh by clearing last_refresh
        _auth_config_cache['last_refresh'] = None

        # Clear session again
        with client.session_transaction() as sess:
            sess.clear()

        # Step 5: Access endpoint without auth (should fail again)
        response = client.get('/memos')
        assert response.status_code == 401


class TestBulkOperations:
    """Test bulk operations."""

    def test_bulk_memo_import(self, app, authenticated_client, db_session):
        """Test importing multiple memos at once."""
        memos_data = [
            {
                'name': f'Bulk Memo {i}',
                'content': f'Content {i}',
                'category': f'Category {i % 3}',
                'type': f'Type {i % 2}'
            }
            for i in range(10)
        ]

        # Import memos
        response = authenticated_client.post('/memos/bulk', json=memos_data)
        assert response.status_code == 201

        # Verify all were created
        with app.app_context():
            count = Memo.query.filter(Memo.name.like('Bulk Memo%')).count()
            assert count == 10

            # Verify categories were created
            categories = Category.query.filter(Category.name.like('Category%')).count()
            assert categories == 3

            # Verify types were created
            types = Type.query.filter(Type.name.like('Type%')).count()
            assert types == 2

        # Check stats
        response = authenticated_client.get('/memos/stats')
        data = json.loads(response.data)
        assert data['count'] >= 10


class TestSessionManagement:
    """Test session management across requests."""

    def test_session_persistence(self, client, test_user):
        """Test that session persists across requests."""
        # Login
        response = client.post('/auth/sign-in', json={
            'email': 'test@test.com',
            'password': 'TestPassword123!'
        })
        assert response.status_code == 200

        # Make authenticated request
        response = client.get('/users/me')
        assert response.status_code == 200

        # Make another authenticated request
        response = client.get('/memos')
        assert response.status_code == 200

        # Logout
        response = client.post('/auth/sign-out')
        assert response.status_code == 200

        # Try to make authenticated request after logout
        response = client.get('/users/me')
        assert response.status_code == 401


class TestErrorHandling:
    """Test error handling across the application."""

    def test_invalid_json(self, authenticated_client):
        """Test handling of invalid JSON."""
        response = authenticated_client.post(
            '/memos',
            data='invalid json',
            content_type='application/json'
        )
        # Should handle gracefully
        assert response.status_code in [400, 500]

    def test_missing_required_fields(self, authenticated_client):
        """Test handling of missing required fields."""
        response = authenticated_client.post('/memos', json={})
        assert response.status_code == 400

    def test_nonexistent_resources(self, authenticated_client):
        """Test accessing non-existent resources."""
        response = authenticated_client.delete('/memos/99999')
        assert response.status_code == 404

    def test_unauthorized_access(self, client):
        """Test unauthorized access to protected endpoints."""
        response = client.get('/memos')
        assert response.status_code == 401

        response = client.post('/memos', json={
            'name': 'Test',
            'content': 'Test'
        })
        assert response.status_code == 401
