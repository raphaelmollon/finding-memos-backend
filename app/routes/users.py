from flask import g, request
from flask_restx import Namespace, Resource, fields
from app.database import db
from app.models import User
from app.middleware import auth_required
import logging

users_ns = Namespace('users', description="Users operations")

# Models
user_model = users_ns.model('User', {
    'id': fields.Integer(description='User ID'),
    'email': fields.String(description='User email'),
    'username': fields.String(description='Username'),
    'is_superuser': fields.Boolean(description='Is superuser'),
    'preferences': fields.String(description="User preferences"),
    'settings': fields.String(description="User settings")
})

user_update_model = users_ns.model('UserUpdate', {
    'username': fields.String(description='Username'),
    'email': fields.String(description='User email'),  # for superuser only
    'is_superuser': fields.Boolean(description='Is superuser'),  # for superuser only
    'preferences': fields.String(description="User preferences"),
    'settings': fields.String(description="User settings")
})


@users_ns.route('/me')
class UserProfile(Resource):
    @auth_required
    @users_ns.response(200, "User retrieved", user_model)
    @users_ns.response(500, "Internal server error")
    def get(self):
        """Get current user profile"""
        try:
            # g.user is already defined in middleware auth_required
            return {
                "user": {
                    "id": g.user.id,
                    "email": g.user.email, 
                    "is_superuser": g.user.is_superuser,
                    "username": g.user.username,
                    "preferences": g.user.preferences,
                    "settings": g.user.settings
                }
            }, 200
        except Exception as e:
            logging.error(f"Error fetching current user: {e}")
            return {"error": "Failed to fetch user profile"}, 500
    
# Route to list all users
@users_ns.route('/')
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
            result = [{
                "id": user.id,
                "email": user.email,
                "is_superuser": user.is_superuser,
                "username": user.username,
                "preferences": user.preferences,
                "settings": user.settings
            } for user in users]
            
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
            
            # Only a superuser can modify these fields
            if g.user.is_superuser:
                if 'email' in data:
                    # Vérifier que l'email n'est pas déjà utilisé
                    existing_user = User.query.filter(
                        User.email == data['email'],
                        User.id != id
                    ).first()
                    if existing_user:
                        return {"error": "Email already exists"}, 409
                    user.email = data['email']
                
                if 'is_superuser' in data:
                    user.is_superuser = bool(data.get('is_superuser'))

            db.session.commit()
            
            return {
                "message": "User updated successfully",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "is_superuser": user.is_superuser,
                    "username": user.username,
                    "preferences": user.preferences,
                    "settings": user.settings
                }
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