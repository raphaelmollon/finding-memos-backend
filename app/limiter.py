"""
Rate limiter instance for the application
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Create limiter instance (will be initialized in create_app)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)
