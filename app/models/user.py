from flask_sqlalchemy import SQLAlchemy
from ..database import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_superuser = db.Column(db.Boolean, default=False)
    username = db.Column(db.String(120), unique=False, nullable=True)
    preferences = db.Column(db.Text, default='{}')
    settings = db.Column(db.Text, default='{}')