from flask_sqlalchemy import SQLAlchemy
from ..database import db
from datetime import datetime, timezone

class Memo(db.Model):
    __tablename__ = 'memos'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', name='fk_memos_category_id'))
    type_id = db.Column(db.Integer, db.ForeignKey('types.id', name='fk_memos_type_id'))

    author_id = db.Column(db.Integer, db.ForeignKey('users.id', name='fk_memos_author_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    category = db.relationship('Category', backref='memos')
    type = db.relationship('Type', backref='memos')
    author = db.relationship('User', backref='memos')

    __table_args__ = (
        db.Index('idx_memos_name', 'name'),
        db.Index('idx_memos_category_id', 'category_id'), 
        db.Index('idx_memos_type_id', 'type_id'),
        db.Index('idx_memos_author_id', 'author_id'),
        db.Index('idx_memos_created_at', 'created_at'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "type_id": self.type_id,
            "type_name": self.type.name if self.type else None,
            "author_id": self.author_id,
            "author_email": self.author.email if self.author else None,
            "author_username": self.author.username if self.author else None,
            "author_avatar": self.author.avatar if self.author else None,
            "created_at": self.created_at.isoformat() + 'Z' if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + 'Z' if self.updated_at else None
        }