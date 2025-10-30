from flask_sqlalchemy import SQLAlchemy
from ..database import db
import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_superuser = db.Column(db.Boolean, default=False)
    username = db.Column(db.String(120), unique=False, nullable=True)
    avatar = db.Column(db.String(50), default='0.png')
    preferences = db.Column(db.Text, default='{}')
    settings = db.Column(db.Text, default='{}')
    reset_token = db.Column(db.String(100), nullable=True)

    status = db.Column(db.String(20), nullable=False, default_server='NEW')  # NEW, VALID, CLOSED
    email_validation_token = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at.isoformat() + 'Z' if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            "email": self.email,
            "is_superuser": self.is_superuser,
            "username": self.username,
            "avatar": self.avatar,
            "preferences": self.preferences,
            "settings": self.settings
        }