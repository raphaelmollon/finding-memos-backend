import json
from flask import g, request
from flask_restx import Namespace, Resource, fields
from app.database import db
from app.models import User
from app.middleware import auth_required
from app.helpers import validate_password
import logging

users_ns = Namespace('users', description="Users operations")

# Models
user_model = users_ns.model('User', {
    'id': fields.Integer(description='User ID'),
    'email': fields.String(description='User email'),
    'username': fields.String(description='Username'),
    'is_superuser': fields.Boolean(description='Is superuser'),
    'avatar': fields.String(description='Avatar filename'),
    'preferences': fields.String(description="User preferences"),
    'settings': fields.String(description="User settings"),
    'status': fields.String(description='User status'),
    'created_at': fields.String(description='Creation date'),
    'updated_at': fields.String(description='Last update date')
})

user_update_model = users_ns.model('UserUpdate', {
    'username': fields.String(description='Username'),
    'password': fields.String(description='New password'),
    'old_password': fields.String(description='Current password (required for password change)'),
    'avatar': fields.String(description='Avatar filename'),
    'preferences': fields.String(description="User preferences"),
    'settings': fields.String(description="User settings"),
    'is_superuser': fields.Boolean(description='Is superuser'),
    'status': fields.String(description='User status (NEW/VALID/CLOSED)')

})


@users_ns.route('/me')
class CurrentUser(Resource):
    @auth_required
    @users_ns.response(200, "User retrieved", user_model)
    @users_ns.response(500, "Internal server error")
    def get(self):
        """Get current user profile"""
        try:
            user = g.user
            return {
                "user": user.to_dict()
            }, 200
        except Exception as e:
            logging.error(f"Error fetching current user: {e}")
            return {"error": "Failed to fetch user profile"}, 500

    @auth_required
    @users_ns.response(200, "Account delete")
    @users_ns.response(400, "Cannot delete last superuser")
    @users_ns.response(500, "Internal server error")
    def delete(self):
        """Delete current user account"""
        try:
            user = g.user

            # Prevent last superuser to delete himself
            if user.is_superuser:
                other_superusers = User.query.filter(
                    User.is_superuser == True,
                    User.id != user.id
                ).count()
                if other_superusers == 0:
                    return {"error": "Cannot delete the last superuser account"}, 400
                
            # Delete user
            db.session.delete(user)
            db.session.commit()

            # Disconnect session
            from flask import session
            session.clear()

            return {"message": "Account delete successfully"}, 200
        
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error deleting account: {e}")
            return {"error": "Failed to delete account"}, 500

    @auth_required
    @users_ns.expect(user_update_model)
    @users_ns.response(200, "Profile updated", user_model)
    @users_ns.response(400, "Old password not provided or wrong")
    @users_ns.response(404, "User not found")
    @users_ns.response(500, "Internal server error")
    def put(self):
        """Update current user profile"""
        try:
            user = User.query.filter_by(id=g.user.id).first()
            if not user:
                return {"error": "User not found"}, 404

            data = request.get_json()

            logging.debug(data)

            # Updatable fields
            if 'username' in data:
                user.username = data.get('username')
            
            if 'password' in data and data['password']:  # field is not empty
                # Old password must be provided as well
                if not data.get('old_password'):
                    return {"error": "Old password is required to confirm password change"}, 400
                
                # Check if old password is correct
                from werkzeug.security import check_password_hash
                if not check_password_hash(user.password_hash, data['old_password']):
                    return {"error": "Old password doesn't match"}, 400
                
                # Check if password is strong enough
                password_error = validate_password(data['password'])
                if password_error:
                    return {"error": password_error}, 400

                # Create new password
                from werkzeug.security import generate_password_hash
                user.password_hash = generate_password_hash(data['password'])
            
            if 'preferences' in data:
                user.preferences = data.get('preferences')
            if 'settings' in data:
                user.settings = data.get('settings')
            if 'avatar' in data:
                avatar_filename = data.get('avatar')
                from app.services.avatar_service import avatar_service
                if avatar_service.is_valid_avatar(avatar_filename):
                    user.avatar = avatar_filename
                else:
                    return {"error": "Invalid avatar filename"}, 400
                
            db.session.commit()

            return {
                "message": "Profile updated successfully",
                "user": user.to_dict()
            }, 200

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating profile: {e}")
            return {"error": "Failed to update profile"}, 500

@users_ns.route('/me/preferences')
class CurrentUserPreferences(Resource):
    @auth_required
    @users_ns.response(200, "Preferences retrieved")
    @users_ns.response(500, "Internal server error")
    def get(self):
        """Get current user preferences"""
        try:
            user = g.user
            return {
                "preferences": user.get_preferences()
            }, 200
        except Exception as e:
            logging.error(f"Error fetching current user preferences: {e}")
            return {"error": "Failed to fetch user preferences"}, 500
    
    @auth_required
    @users_ns.expect(users_ns.model('PreferencesUpdate', {
        'preferences': fields.Raw(description='Updated preferences')
    }))
    def put(self):
        """Update all user preferences (replace entire preferences object)"""
        try:
            data = request.get_json()
            user = g.user
            user.preferences = json.dumps(data.get('preferences', {}))
            db.session.commit()
            return {"message": "Preferences updated successfully"}, 200
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating preferences: {e}")
            return {"error": "Failed to update preferences"}, 500

# For section-specific operations
@users_ns.route('/me/preferences/<string:section>')
class CurrentUserPreferenceSection(Resource):
    @auth_required
    def get(self, section):
        """Get preferences for a specific section"""
        try:
            user = g.user
            section_prefs = user.get_preferences(section)
            return {
                "section": section,
                "preferences": section_prefs
            }, 200
        except Exception as e:
            logging.error(f"Error fetching {section} preferences: {e}")
            return {"error": f"Failed to fetch {section} preferences"}, 500

    @auth_required
    @users_ns.expect(users_ns.model('SectionPreferencesUpdate', {
        'preferences': fields.Raw(description='Updated section preferences')
    }))
    def put(self, section):
        """Update preferences for a specific section"""
        try:
            data = request.get_json()
            user = g.user

            logging.debug(f"section:{section} ; data:{str(data)}")
            
            # Get current preferences
            all_prefs = user.get_preferences()
            logging.debug(f"all_prefs_BEFORE:{str(all_prefs)}")
            # Update only the specified section
            all_prefs[section] = data.get('preferences', {})
            logging.debug(f"all_prefs_AFTER:{str(all_prefs)}")
            
            user.preferences = json.dumps(all_prefs)
            logging.debug(f"user.preferences:{str(user.preferences)}")
            db.session.commit()
            
            return {"message": f"{section} preferences updated successfully"}, 200
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating {section} preferences: {e}")
            return {"error": f"Failed to update {section} preferences"}, 500
        

# Route to list all users
@users_ns.route('')
class UserList(Resource):
    @auth_required
    @users_ns.response(200, "Users retrieved", [user_model])
    @users_ns.response(403, "Forbidden")
    @users_ns.response(500, "Internal server error")
    def get(self):
        """Get all users (requires superuser)"""
        try:
            # Check if current user is superuser
            if not g.user.is_superuser:
                return {"error": "Unauthorized - superuser required"}, 403

            users = User.query.all()
            result = [user.to_dict() for user in users]
            
            return result, 200
        except Exception as e:
            logging.error(f"Error fetching users: {e}")
            return {"error": "Failed to fetch users"}, 500

@users_ns.route('/<int:id>')
class UserResource(Resource):
    @auth_required
    @users_ns.expect(user_update_model)
    @users_ns.response(200, "User updated")
    @users_ns.response(403, "Forbidden (restricted to superuser)")
    @users_ns.response(404, "User not found")
    @users_ns.response(409, "Email address already used")
    @users_ns.response(500, "Internal server error")
    def put(self, id):
        """Update a user"""
        try:
            # Check permissions : either superuser, or your own profile
            if not g.user.is_superuser and g.user.id != id:
                return {"error": "Unauthorized - can only update your own profile"}, 403

            user = User.query.filter_by(id=id).first()
            if not user:
                return {"error": "User not found"}, 404

            data = request.get_json()
            
            # Updatable fields
            if 'username' in data:
                user.username = data.get('username')
            if 'preferences' in data:
                user.preferences = data.get('preferences')
            if 'settings' in data:
                user.settings = data.get('settings')
            if 'avatar' in data:
                avatar_filename = data.get('avatar')
                from app.services.avatar_service import avatar_service
                if avatar_service.is_valid_avatar(avatar_filename):
                    user.avatar = avatar_filename
                else:
                    return {"error": "Invalid avatar filename"}, 400
                
            # Only a superuser can modify these fields
            if g.user.is_superuser:
                if 'email' in data:
                    # Check that email is not already used
                    existing_user = User.query.filter(
                        User.email == data['email'],
                        User.id != id
                    ).first()
                    if existing_user:
                        return {"error": "Email already exists"}, 409
                    user.email = data['email']
                
                if 'is_superuser' in data:
                    new_superuser_status = bool(data.get('is_superuser'))

                    if user.is_superuser and not new_superuser_status:
                        other_superusers = User.query.filter(
                            User.is_superuser == True,
                            User.id != id
                        ).count()
                        if other_superusers == 0:
                            return {"error": "Cannot remove superuser status from the last superuser"}, 400
                    
                    user.is_superuser = new_superuser_status

                if 'status' in data:
                    valid_statuses = ['NEW', 'VALID', 'CLOSED']
                    if data['status'] in valid_statuses:
                        user.status = data['status']
                    else:
                        return {"error": f"Invalid status. Must be one of: {valid_statuses}"}, 400

            db.session.commit()
            
            return {
                "message": "User updated successfully",
                "user": user.to_dict()
            }, 200

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating user: {e}")
            return {"error": "Failed to update user"}, 500

    @auth_required
    @users_ns.response(200, "User deleted")
    @users_ns.response(400, "Cannot delete last superuser")
    @users_ns.response(403, "Forbidden")
    @users_ns.response(404, "User not found")
    @users_ns.response(500, "Internal server error")
    def delete(self, id):
        """Delete a user"""
        try:
            # Check permissions: either superuser or your own profile
            if not g.user.is_superuser and g.user.id != id:
                return {"error": "Unauthorized - can only delete your own account"}, 403

            # Prevent deleting account if last superuser
            if g.user.id == id and g.user.is_superuser:
                other_superusers = User.query.filter(
                    User.is_superuser == True,
                    User.id != id
                ).count()
                if other_superusers == 0:
                    return {"error": "Cannot delete the last superuser account"}, 400

            user = User.query.filter_by(id=id).first()
            if not user:
                return {"error": "User not found"}, 404

            db.session.delete(user)
            db.session.commit()
            
            # If user deletes himself, disconnect as well
            if g.user.id == id:
                from flask import session
                session.clear()
                
            return {"message": "User deleted successfully"}, 200

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error deleting user: {e}")
            return {"error": "Failed to delete user"}, 500

@users_ns.route('/avatars')
class AvatarList(Resource):
    @auth_required
    @users_ns.response(200, "Avatars list retrieved")
    @users_ns.response(500, "Internal server error")
    def get(self):
        """Get all available avatars"""
        try:
            from app.services.avatar_service import avatar_service
            avatars = avatar_service.get_available_avatars()
            return {'avatars': avatars}, 200
        except Exception as e:
            logging.error(f"Error fetching avatars: {e}")
            return {"error": "Failed to fetch avatars"}, 500

@users_ns.route('/<int:id>/reset-password')
class AdminResetPassword(Resource):
    @auth_required
    @users_ns.response(200, "Password reset initiated")
    @users_ns.response(403, "Forbidden")
    @users_ns.response(404, "User not found")
    @users_ns.response(500, "Internal server error")
    def post(self, id):
        """Admin: Force password reset for a user"""
        try:
            # Check if superuser
            if not g.user.is_superuser:
                return {"error": "Superuser required"}, 403
            
            user = User.query.filter_by(id=id).first()
            if not user:
                return {"error": "User not found"}, 404
            
            # Generate a reset token
            from app.services.token_service import token_service
            reset_token = token_service.generate_reset_token(user.id)

            # Send the email
            from app.services.email_service import email_service
            email_sent = email_service.send_password_reset(user.email, reset_token)

            if email_sent:
                return {"message": f"Password reset email sent to {user.email}"}, 200
            else:
                return {"error": "Failed to send reset email"}, 500
            
        except Exception as e:
            logging.error(f"Admin password reset error {e}")
            return {"error": "Failed to initiate password reset"}, 500