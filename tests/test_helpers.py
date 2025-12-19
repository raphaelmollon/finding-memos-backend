import pytest
from app.helpers import (
    get_or_create_category,
    get_or_create_type,
    clean_unused_category,
    clean_unused_type,
    validate_password
)
from app.models import Category, Type, Memo
from app.database import db


class TestGetOrCreateHelpers:
    """Test get_or_create helper functions."""

    def test_get_or_create_category_new(self, app, db_session):
        """Test creating a new category."""
        with app.app_context():
            category = get_or_create_category('New Category')
            assert category is not None
            assert category.name == 'New Category'
            assert category.id is not None

    def test_get_or_create_category_existing(self, app, db_session, test_category):
        """Test getting an existing category."""
        with app.app_context():
            category = get_or_create_category('Test Category')
            assert category.id == test_category.id

    def test_get_or_create_category_none(self, app, db_session):
        """Test with None category name."""
        with app.app_context():
            category = get_or_create_category(None)
            assert category is None

    def test_get_or_create_category_empty(self, app, db_session):
        """Test with empty category name."""
        with app.app_context():
            category = get_or_create_category('')
            assert category is None

    def test_get_or_create_type_new(self, app, db_session):
        """Test creating a new type."""
        with app.app_context():
            type_obj = get_or_create_type('New Type')
            assert type_obj is not None
            assert type_obj.name == 'New Type'
            assert type_obj.id is not None

    def test_get_or_create_type_existing(self, app, db_session, test_type):
        """Test getting an existing type."""
        with app.app_context():
            type_obj = get_or_create_type('Test Type')
            assert type_obj.id == test_type.id

    def test_get_or_create_type_none(self, app, db_session):
        """Test with None type name."""
        with app.app_context():
            type_obj = get_or_create_type(None)
            assert type_obj is None

    def test_get_or_create_type_empty(self, app, db_session):
        """Test with empty type name."""
        with app.app_context():
            type_obj = get_or_create_type('')
            assert type_obj is None


class TestCleanupHelpers:
    """Test cleanup helper functions."""

    def test_clean_unused_category(self, app, db_session, test_user):
        """Test cleaning up an unused category."""
        with app.app_context():
            # Create a category
            category = Category(name='Unused Category')
            db.session.add(category)
            db.session.commit()
            category_id = category.id

            # Verify it exists
            assert Category.query.filter_by(id=category_id).first() is not None

            # Clean it up
            clean_unused_category(category_id)
            db.session.commit()

            # Verify it's deleted
            assert Category.query.filter_by(id=category_id).first() is None

    def test_clean_unused_category_in_use(self, app, db_session, test_memo, test_category):
        """Test that used categories are not deleted."""
        with app.app_context():
            category_id = test_category.id

            # Try to clean it up (should not delete because it's in use)
            clean_unused_category(category_id)
            db.session.commit()

            # Verify it still exists
            assert Category.query.filter_by(id=category_id).first() is not None

    def test_clean_unused_category_none(self, app, db_session):
        """Test cleaning up with None category_id."""
        with app.app_context():
            # Should not raise an error
            clean_unused_category(None)
            db.session.commit()

    def test_clean_unused_type(self, app, db_session, test_user):
        """Test cleaning up an unused type."""
        with app.app_context():
            # Create a type
            type_obj = Type(name='Unused Type')
            db.session.add(type_obj)
            db.session.commit()
            type_id = type_obj.id

            # Verify it exists
            assert Type.query.filter_by(id=type_id).first() is not None

            # Clean it up
            clean_unused_type(type_id)
            db.session.commit()

            # Verify it's deleted
            assert Type.query.filter_by(id=type_id).first() is None

    def test_clean_unused_type_in_use(self, app, db_session, test_memo, test_type):
        """Test that used types are not deleted."""
        with app.app_context():
            type_id = test_type.id

            # Try to clean it up (should not delete because it's in use)
            clean_unused_type(type_id)
            db.session.commit()

            # Verify it still exists
            assert Type.query.filter_by(id=type_id).first() is not None

    def test_clean_unused_type_none(self, app, db_session):
        """Test cleaning up with None type_id."""
        with app.app_context():
            # Should not raise an error
            clean_unused_type(None)
            db.session.commit()


class TestValidatePassword:
    """Test password validation."""

    def test_valid_password(self):
        """Test a valid password."""
        error = validate_password('ValidPass123!')
        assert error is None

    def test_password_too_short(self):
        """Test password that's too short."""
        error = validate_password('Val1!')
        assert error is not None
        assert '8 characters' in error

    def test_password_no_uppercase(self):
        """Test password without uppercase."""
        error = validate_password('validpass123!')
        assert error is not None
        assert 'uppercase' in error

    def test_password_no_lowercase(self):
        """Test password without lowercase."""
        error = validate_password('VALIDPASS123!')
        assert error is not None
        assert 'lowercase' in error

    def test_password_no_digit(self):
        """Test password without digit."""
        error = validate_password('ValidPass!')
        assert error is not None
        assert 'number' in error

    def test_password_no_special_char(self):
        """Test password without special character."""
        error = validate_password('ValidPass123')
        assert error is not None
        assert 'special character' in error

    def test_various_special_chars(self):
        """Test password with various special characters."""
        special_chars = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '-', '_', '=', '+', '[', ']', '{', '}', '|', '\\', ':', ';', '"', "'", '<', '>', ',', '.', '?', '/']

        for char in special_chars:
            password = f'ValidPass123{char}'
            error = validate_password(password)
            assert error is None, f"Password with {char} should be valid"

    def test_password_all_requirements(self):
        """Test that all password requirements work together."""
        # Valid password with all requirements
        assert validate_password('MyPassword123!') is None
        assert validate_password('Test123$password') is None
        assert validate_password('Secure@Pass1') is None
