from ..database import db
from datetime import datetime, timezone


class ConnectionUserEngagement(db.Model):
    """
    Tracks individual user engagement with connections (ratings and usage).

    This allows per-user tracking of:
    - Which connections a user has rated (thumbs up/down)
    - How many times a user has used each connection
    - When they first/last used a connection
    """
    __tablename__ = 'connection_user_engagement'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    connection_id = db.Column(db.Integer, db.ForeignKey('connections.id', name='fk_cue_connection_id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', name='fk_cue_user_id', ondelete='CASCADE'), nullable=False, index=True)

    # Rating: 'up', 'down', or None (no rating)
    rating = db.Column(db.Enum('up', 'down', name='rating_enum'), nullable=True)

    # Usage tracking for this specific user
    usage_count = db.Column(db.Integer, default=0, nullable=False, index=True)
    first_used_at = db.Column(db.DateTime, nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True, index=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Unique constraint: one engagement record per user-connection pair
    __table_args__ = (
        db.UniqueConstraint('user_id', 'connection_id', name='unique_user_connection'),
    )

    # Relationships
    connection = db.relationship('Connection', backref='user_engagements')
    user = db.relationship('User', backref='connection_engagements')

    def __repr__(self):
        return f'<ConnectionUserEngagement user_id={self.user_id} connection_id={self.connection_id} rating={self.rating}>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'connection_id': self.connection_id,
            'user_id': self.user_id,
            'rating': self.rating,
            'usage_count': self.usage_count,
            'first_used_at': self.first_used_at.replace(tzinfo=timezone.utc).isoformat() if self.first_used_at else None,
            'last_used_at': self.last_used_at.replace(tzinfo=timezone.utc).isoformat() if self.last_used_at else None,
            'created_at': self.created_at.replace(tzinfo=timezone.utc).isoformat() if self.created_at else None,
            'updated_at': self.updated_at.replace(tzinfo=timezone.utc).isoformat() if self.updated_at else None,
        }
