import os
import logging
from flask import url_for

class AvatarService:
    AVATARS_DIR = 'app/static/avatars'
    DEFAULT_AVATAR = 'default.png'
    
    @classmethod
    def get_available_avatars(cls):
        """Retrieves the list of available avatars"""
        try:
            avatars = []
            for filename in os.listdir(cls.AVATARS_DIR):
                if filename.endswith('.png') and filename != cls.DEFAULT_AVATAR:
                    avatars.append({
                        'filename': filename,
                        'url': f'/static/avatars/{filename}'  # frontend URL
                    })
            return sorted(avatars, key=lambda x: x['filename'])
        except Exception as e:
            logging.error(f"Error listing avatars: {e}")
            return []
    
    @classmethod
    def is_valid_avatar(cls, avatar_name):
        """Checks if an avatar exists"""
        if not avatar_name:
            return False
        return os.path.exists(os.path.join(cls.AVATARS_DIR, avatar_name))

# Instance globale
avatar_service = AvatarService()