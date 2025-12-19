import pytest
import os
import sys
import tempfile
import json
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.database import db
from app.models import User, Memo, Category, Type, Config
from werkzeug.security import generate_password_hash


@pytest.fixture(scope='session')
def app():
    """Create application for the tests."""
    # Create a temporary file for the database
    db_fd, db_path = tempfile.mkstemp()

    # Set test environment variables
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    os.environ['SECRET_KEY'] = 'test-secret-key-for-testing'
    os.environ['TESTING'] = 'True'

    # Create app
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

    # Disable rate limiting for tests
    from app.limiter import limiter
    limiter.enabled = False

    # Mock email service to not send real emails
    from unittest.mock import Mock
    from app.services import email_service
    email_service.email_service.send_email_validation = Mock(return_value=True)
    email_service.email_service.send_password_reset = Mock(return_value=True)

    # Create tables
    with app.app_context():
        db.create_all()

        # Create initial config
        config = Config(id=1, enable_auth=True, allowed_domains='["test.com", "example.com"]')
        db.session.add(config)
        db.session.commit()

    yield app

    # Cleanup - close database connections first
    with app.app_context():
        db.session.remove()
        db.engine.dispose()

    try:
        os.close(db_fd)
        os.unlink(db_path)
    except (PermissionError, OSError):
        # On Windows, file might still be locked
        pass


@pytest.fixture(scope='function')
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture(scope='function', autouse=True)
def reset_auth_cache():
    """Reset auth config cache before every test."""
    from app.middleware import _auth_config_cache
    _auth_config_cache['enable_auth'] = True
    _auth_config_cache['last_refresh'] = None
    yield
    # Reset again after test
    _auth_config_cache['enable_auth'] = True
    _auth_config_cache['last_refresh'] = None


@pytest.fixture(scope='function')
def db_session(app):
    """Create a new database session for a test."""
    with app.app_context():
        # Clear all tables before test
        db.session.query(Memo).delete()
        db.session.query(User).delete()
        db.session.query(Category).delete()
        db.session.query(Type).delete()
        # Don't delete Config, just reset it
        config = Config.query.filter_by(id=1).first()
        if config:
            config.enable_auth = True
            config.allowed_domains = '["test.com", "example.com"]'
        db.session.commit()

        yield db.session

        # Cleanup after test
        db.session.rollback()
        db.session.close()


@pytest.fixture
def test_user(app, db_session):
    """Create a test user."""
    with app.app_context():
        user = User(
            email='test@test.com',
            password_hash=generate_password_hash('TestPassword123!'),
            username='testuser',
            is_superuser=False,
            status='VALID'
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def superuser(app, db_session):
    """Create a superuser."""
    with app.app_context():
        user = User(
            email='admin@test.com',
            password_hash=generate_password_hash('AdminPassword123!'),
            username='admin',
            is_superuser=True,
            status='VALID'
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def new_user(app, db_session):
    """Create a user with NEW status (not validated)."""
    with app.app_context():
        user = User(
            email='newuser@test.com',
            password_hash=generate_password_hash('NewPassword123!'),
            username='newuser',
            is_superuser=False,
            status='NEW'
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def test_category(app, db_session):
    """Create a test category."""
    with app.app_context():
        category = Category(name='Test Category')
        db.session.add(category)
        db.session.commit()
        db.session.refresh(category)
        return category


@pytest.fixture
def test_type(app, db_session):
    """Create a test type."""
    with app.app_context():
        type_obj = Type(name='Test Type')
        db.session.add(type_obj)
        db.session.commit()
        db.session.refresh(type_obj)
        return type_obj


@pytest.fixture
def test_memo(app, db_session, test_user, test_category, test_type):
    """Create a test memo."""
    with app.app_context():
        memo = Memo(
            name='Test Memo',
            description='Test Description',
            content='Test Content',
            author_id=test_user.id,
            category_id=test_category.id,
            type_id=test_type.id
        )
        db.session.add(memo)
        db.session.commit()
        db.session.refresh(memo)
        return memo


@pytest.fixture
def authenticated_client(client, test_user):
    """Create an authenticated test client."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
    return client


@pytest.fixture
def superuser_client(client, superuser):
    """Create an authenticated superuser client."""
    with client.session_transaction() as sess:
        sess['user_id'] = superuser.id
    return client


@pytest.fixture
def disable_auth(app, db_session):
    """Disable authentication for tests."""
    with app.app_context():
        config = Config.query.filter_by(id=1).first()
        config.enable_auth = False
        db.session.commit()

        # Update cache
        from app.middleware import _auth_config_cache
        import datetime
        _auth_config_cache['enable_auth'] = False
        _auth_config_cache['last_refresh'] = datetime.datetime.now(datetime.timezone.utc)

        yield

        # Re-enable after test
        config.enable_auth = True
        db.session.commit()

        # Update cache
        _auth_config_cache['enable_auth'] = True
        _auth_config_cache['last_refresh'] = datetime.datetime.now(datetime.timezone.utc)
