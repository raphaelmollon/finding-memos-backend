import logging
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

class TokenService:
    def __init__(self):
        self._serializer = None

    @property
    def serializer(self):
        """Init the serializer on demande with the current SECRET_KEY"""
        if self._serializer is None:
            self._serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return self._serializer

    def generate_reset_token(self, user_id):
        """Generate a securised and time limited token"""
        return self.serializer.dumps(user_id, salt="password-reset-salt")
    
    def validate_reset_token(self, token, max_age=3600):
        """Validate a token and return user_id (max_age in seconds)"""
        try:
            user_id = self.serializer.loads(
                token,
                salt="password-reset-salt",
                max_age=max_age
            )
            return user_id
        except Exception as e:
            logging.error(f"Token validation failed: {e}")
            return None
        
    def generate_signup_token(self, user_id):
        """Generate a securised and time limited token"""
        return self.serializer.dumps(user_id, salt="signup-salt")
    
    def validate_signup_token(self, token, max_age=3600):
        """Validate a token and return user_id (max_age in seconds)"""
        try:
            user_id = self.serializer.loads(
                token,
                salt="signup-salt",
                max_age=max_age
            )
            return user_id
        except Exception as e:
            logging.error(f"Token validation failed: {e}")
            return None
        
# Global instance
token_service = TokenService()