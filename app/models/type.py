from flask_sqlalchemy import SQLAlchemy
from ..database import db

class Type(db.Model):
    __tablename__ = 'types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
