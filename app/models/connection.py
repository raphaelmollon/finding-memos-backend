from ..database import db
from datetime import datetime, timezone


class Connection(db.Model):
    """
    Connection model stores encrypted connection data from connections.json

    Structure is flattened from the nested JSON format:
    companies -> sites -> applications -> servers -> urls

    All sensitive fields (ip, url, user, pwd, comments, comment_urls)
    remain encrypted as they are in the source JSON file.
    """
    __tablename__ = 'connections'

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Hierarchical identifiers (not unique, used for filtering)
    company_name = db.Column(db.String(255), nullable=False, index=True)
    site_name = db.Column(db.String(255), nullable=False, index=True)
    application_name = db.Column(db.String(255), nullable=False, index=True)

    # Application metadata
    application_last_update = db.Column(db.DateTime, nullable=True)
    connection_last_update = db.Column(db.DateTime, nullable=True)

    # Encrypted fields from application level
    comments = db.Column(db.Text, nullable=True)  # Encrypted
    comment_urls = db.Column(db.JSON, nullable=True)  # Array of encrypted strings

    # Server information
    server_ip = db.Column(db.Text, nullable=True)  # Encrypted
    server_last_update = db.Column(db.DateTime, nullable=True)

    # URL information (unique identifier from source system)
    url_id = db.Column(db.String(36), nullable=False, index=True)  # UUID from source
    url_last_update = db.Column(db.DateTime, nullable=True)
    url_mode = db.Column(db.String(50), nullable=True)  # 'classic' or 'extrapolated'
    url_service = db.Column(db.String(50), nullable=True, index=True)  # SCS, SCL, DIP_ST, etc.
    url_server_type = db.Column(db.String(100), nullable=True, index=True)  # Production, Test, etc.

    # Encrypted URL data
    url_type = db.Column(db.Text, nullable=True)  # Encrypted, nullable
    url = db.Column(db.Text, nullable=True)  # Encrypted, nullable
    user = db.Column(db.Text, nullable=True)  # Encrypted, nullable
    pwd = db.Column(db.Text, nullable=True)  # Encrypted, nullable

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f'<Connection {self.company_name}/{self.site_name}/{self.application_name} - {self.url_id}>'

    def to_dict(self, include_encrypted=False):
        """
        Convert to dictionary for API responses

        Args:
            include_encrypted (bool): Whether to include encrypted fields (default: False)
                                     Set to False to save bandwidth and resources

        Returns:
            dict: Connection data
        """
        data = {
            'id': self.id,
            'company_name': self.company_name,
            'site_name': self.site_name,
            'application_name': self.application_name,
            'application_last_update': self.application_last_update.isoformat() if self.application_last_update else None,
            'connection_last_update': self.connection_last_update.isoformat() if self.connection_last_update else None,
            'server_last_update': self.server_last_update.isoformat() if self.server_last_update else None,
            'url_id': self.url_id,
            'url_last_update': self.url_last_update.isoformat() if self.url_last_update else None,
            'url_mode': self.url_mode,
            'url_service': self.url_service,
            'url_server_type': self.url_server_type,
            'has_credentials': bool(self.user and self.pwd),
            'has_url': bool(self.url),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_encrypted:
            data.update({
                'comments': self.comments,
                'comment_urls': self.comment_urls,
                'server_ip': self.server_ip,
                'url_type': self.url_type,
                'url': self.url,
                'user': self.user,
                'pwd': self.pwd,
            })

        return data
