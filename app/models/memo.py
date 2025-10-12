from flask_sqlalchemy import SQLAlchemy
from ..database import db

class Memo(db.Model):
    __tablename__ = 'memos'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    type_id = db.Column(db.Integer, db.ForeignKey('types.id'))

    category = db.relationship('Category', backref='memos')
    type = db.relationship('Type', backref='memos')

    __table_args__ = (
        db.Index('idx_memos_name', 'name'),
        db.Index('idx_memos_category', 'category_id'), 
        db.Index('idx_memos_type', 'type_id'),
    )
