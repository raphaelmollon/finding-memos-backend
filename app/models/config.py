from flask_sqlalchemy import SQLAlchemy
from ..database import db


class Config(db.Model):
    __tablename__ = 'config'
    id = db.Column(db.Integer, primary_key=True)
    enable_auth = db.Column(db.Boolean, default=True)
    allowed_domains = db.Column(db.Text, default='["example.com"]')