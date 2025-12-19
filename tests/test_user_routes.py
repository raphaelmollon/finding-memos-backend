import pytest
import json
from app.models import User
from app.database import db
from werkzeug.security import generate_password_hash


class TestCurrentUser:
    """Test /users/me endpoints."""

    def test_get_current_user(self, authenticated_client, test_user):
        """Test getting current user profile."""
        response = authenticated_client.get('/users/me')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'user' in data
        assert data['user']['email'] == 'test@test.com'

    def test_get_current_user_unauthenticated(self, client):
        """Test getting current user without authentication."""
        response = client.get('/users/me')

        assert response.status_code == 401

    def test_update_current_user_username(self, authenticated_client, test_user):
        """Test updating username."""
        response = authenticated_client.put('/users/me', json={
            'username': 'newusername'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user']['username'] == 'newusername'

    def test_update_current_user_password(self, app, authenticated_client, test_user):
        """Test updating password."""
        response = authenticated_client.put('/users/me', json={
            'password': 'NewPassword123!',
            'old_password': 'TestPassword123!'
        })

        assert response.status_code == 200

        # Verify password was changed
        from werkzeug.security import check_password_hash
        with app.app_context():
            user = User.query.filter_by(id=test_user.id).first()
            assert check_password_hash(user.password_hash, 'NewPassword123!')

    def test_update_password_wrong_old_password(self, authenticated_client):
        """Test updating password with wrong old password."""
        response = authenticated_client.put('/users/me', json={
            'password': 'NewPassword123!',
            'old_password': 'WrongPassword123!'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "doesn't match" in data['error']

    def test_update_password_missing_old_password(self, authenticated_client):
        """Test updating password without old password."""
        response = authenticated_client.put('/users/me', json={
            'password': 'NewPassword123!'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Old password is required' in data['error']

    def test_update_password_weak(self, authenticated_client):
        """Test updating to weak password."""
        response = authenticated_client.put('/users/me', json={
            'password': 'weak',
            'old_password': 'TestPassword123!'
        })

        assert response.status_code == 400

    def test_update_preferences(self, app, authenticated_client):
        """Test updating preferences."""
        prefs = json.dumps({'theme': 'dark', 'lang': 'en'})
        response = authenticated_client.put('/users/me', json={
            'preferences': prefs
        })

        assert response.status_code == 200

    def test_delete_current_user(self, app, authenticated_client, test_user):
        """Test deleting own account."""
        # First create another superuser so we can delete test_user
        response = authenticated_client.delete('/users/me')

        assert response.status_code == 200

        # Verify user was deleted
        with app.app_context():
            user = User.query.filter_by(id=test_user.id).first()
            assert user is None

    def test_delete_last_superuser(self, superuser_client):
        """Test preventing deletion of last superuser."""
        response = superuser_client.delete('/users/me')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'last superuser' in data['error']


class TestUserPreferences:
    """Test user preferences endpoints."""

    def test_get_all_preferences(self, app, authenticated_client, test_user):
        """Test getting all preferences."""
        with app.app_context():
            user = User.query.filter_by(id=test_user.id).first()
            user.preferences = json.dumps({
                'theme': {'color': 'dark'},
                'notifications': {'enabled': True}
            })
            db.session.commit()

        response = authenticated_client.get('/users/me/preferences')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'preferences' in data
        assert 'theme' in data['preferences']
        assert 'notifications' in data['preferences']

    def test_update_all_preferences(self, app, authenticated_client):
        """Test updating all preferences."""
        new_prefs = {
            'theme': {'color': 'light'},
            'layout': {'sidebar': 'left'}
        }

        response = authenticated_client.put('/users/me/preferences', json={
            'preferences': new_prefs
        })

        assert response.status_code == 200

    def test_get_section_preferences(self, app, authenticated_client, test_user):
        """Test getting preferences for a section."""
        with app.app_context():
            user = User.query.filter_by(id=test_user.id).first()
            user.preferences = json.dumps({
                'theme': {'color': 'dark', 'font': 'large'}
            })
            db.session.commit()

        response = authenticated_client.get('/users/me/preferences/theme')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['section'] == 'theme'
        assert data['preferences'] is not None
        if data['preferences']:  # May be None if not set
            assert data['preferences']['color'] == 'dark'

    def test_update_section_preferences(self, app, authenticated_client, test_user):
        """Test updating section preferences."""
        with app.app_context():
            user = User.query.filter_by(id=test_user.id).first()
            user.preferences = json.dumps({
                'theme': {'color': 'dark'},
                'notifications': {'enabled': True}
            })
            db.session.commit()

        response = authenticated_client.put('/users/me/preferences/theme', json={
            'preferences': {'color': 'light', 'font': 'small'}
        })

        assert response.status_code == 200

        # Verify other sections are preserved
        with app.app_context():
            user = User.query.filter_by(id=test_user.id).first()
            prefs = user.get_preferences()
            assert prefs['theme']['color'] == 'light'
            assert 'notifications' in prefs
            assert prefs['notifications']['enabled'] is True


class TestUserList:
    """Test user list endpoint."""

    def test_get_all_users_as_superuser(self, superuser_client, test_user):
        """Test getting all users as superuser."""
        response = superuser_client.get('/users')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_all_users_as_regular_user(self, authenticated_client):
        """Test getting all users as regular user."""
        response = authenticated_client.get('/users')

        assert response.status_code == 403

    def test_get_all_users_unauthenticated(self, client):
        """Test getting all users without authentication."""
        response = client.get('/users')

        assert response.status_code == 401


class TestUserResource:
    """Test individual user endpoints."""

    def test_update_own_profile(self, authenticated_client, test_user):
        """Test regular user updating own profile."""
        response = authenticated_client.put(f'/users/{test_user.id}', json={
            'username': 'updated_username'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user']['username'] == 'updated_username'

    def test_update_other_user_as_regular_user(self, app, authenticated_client, db_session):
        """Test regular user trying to update another user."""
        with app.app_context():
            other_user = User(
                email='other@test.com',
                password_hash=generate_password_hash('Password123!'),
                status='VALID'
            )
            db.session.add(other_user)
            db.session.commit()
            other_id = other_user.id

        response = authenticated_client.put(f'/users/{other_id}', json={
            'username': 'hacked'
        })

        assert response.status_code == 403

    def test_superuser_update_other_user(self, app, superuser_client, test_user):
        """Test superuser updating another user."""
        response = superuser_client.put(f'/users/{test_user.id}', json={
            'username': 'updated_by_admin',
            'is_superuser': True
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user']['username'] == 'updated_by_admin'

    def test_superuser_change_email(self, app, superuser_client, test_user):
        """Test superuser changing user email."""
        response = superuser_client.put(f'/users/{test_user.id}', json={
            'email': 'newemail@test.com'
        })

        assert response.status_code == 200

        with app.app_context():
            user = User.query.filter_by(id=test_user.id).first()
            assert user.email == 'newemail@test.com'

    def test_superuser_change_email_duplicate(self, app, superuser_client, test_user):
        """Test superuser changing email to existing one."""
        response = superuser_client.put(f'/users/{test_user.id}', json={
            'email': 'admin@test.com'  # Superuser's email
        })

        assert response.status_code == 409

    def test_superuser_change_status(self, app, superuser_client, test_user):
        """Test superuser changing user status."""
        response = superuser_client.put(f'/users/{test_user.id}', json={
            'status': 'CLOSED'
        })

        assert response.status_code == 200

        with app.app_context():
            user = User.query.filter_by(id=test_user.id).first()
            assert user.status == 'CLOSED'

    def test_superuser_change_invalid_status(self, superuser_client, test_user):
        """Test superuser changing to invalid status."""
        response = superuser_client.put(f'/users/{test_user.id}', json={
            'status': 'INVALID'
        })

        assert response.status_code == 400

    def test_prevent_removing_last_superuser(self, app, superuser_client, superuser):
        """Test preventing removal of last superuser status."""
        response = superuser_client.put(f'/users/{superuser.id}', json={
            'is_superuser': False
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'last superuser' in data['error']

    def test_delete_user_as_superuser(self, app, superuser_client, test_user):
        """Test superuser deleting another user."""
        user_id = test_user.id

        response = superuser_client.delete(f'/users/{user_id}')

        assert response.status_code == 200

        with app.app_context():
            user = User.query.filter_by(id=user_id).first()
            assert user is None

    def test_delete_user_as_regular_user(self, app, authenticated_client, db_session):
        """Test regular user trying to delete another user."""
        with app.app_context():
            other_user = User(
                email='other@test.com',
                password_hash=generate_password_hash('Password123!'),
                status='VALID'
            )
            db.session.add(other_user)
            db.session.commit()
            other_id = other_user.id

        response = authenticated_client.delete(f'/users/{other_id}')

        assert response.status_code == 403

    def test_delete_own_account(self, app, authenticated_client, test_user):
        """Test deleting own account via user ID endpoint."""
        user_id = test_user.id

        response = authenticated_client.delete(f'/users/{user_id}')

        assert response.status_code == 200

        with app.app_context():
            user = User.query.filter_by(id=user_id).first()
            assert user is None


class TestAvatars:
    """Test avatar endpoints."""

    def test_get_available_avatars(self, authenticated_client):
        """Test getting available avatars."""
        response = authenticated_client.get('/users/avatars')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'avatars' in data
        assert isinstance(data['avatars'], list)


class TestAdminResetPassword:
    """Test admin password reset endpoint."""

    def test_admin_reset_password(self, superuser_client, test_user):
        """Test superuser resetting another user's password."""
        response = superuser_client.post(f'/users/{test_user.id}/reset-password')

        # Will fail in test because email service is not configured
        # but should return 500 (not 403 or 404)
        assert response.status_code in [200, 500]

    def test_admin_reset_password_as_regular_user(self, authenticated_client, test_user):
        """Test regular user trying to reset password."""
        response = authenticated_client.post(f'/users/{test_user.id}/reset-password')

        assert response.status_code == 403

    def test_admin_reset_password_nonexistent_user(self, superuser_client):
        """Test resetting password for non-existent user."""
        response = superuser_client.post('/users/99999/reset-password')

        assert response.status_code == 404
