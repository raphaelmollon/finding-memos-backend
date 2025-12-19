import pytest
import json
from datetime import datetime
from app.models import User, Memo, Category, Type, Config
from app.database import db


class TestUserModel:
    """Test User model."""

    def test_user_creation(self, app, db_session):
        """Test creating a user."""
        with app.app_context():
            user = User(
                email='newuser@test.com',
                password_hash='hashed_password',
                username='newuser'
            )
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.email == 'newuser@test.com'
            assert user.username == 'newuser'
            assert user.is_superuser is False
            assert user.status == 'NEW'
            assert user.avatar == '0.png'
            assert user.preferences == '{}'
            assert user.settings == '{}'

    def test_user_to_dict(self, app, test_user):
        """Test user to_dict method."""
        with app.app_context():
            user_dict = test_user.to_dict()

            assert 'id' in user_dict
            assert 'email' in user_dict
            assert 'username' in user_dict
            assert 'is_superuser' in user_dict
            assert 'avatar' in user_dict
            assert 'settings' in user_dict
            assert 'status' in user_dict
            assert 'created_at' in user_dict
            assert 'updated_at' in user_dict
            assert 'preferences' not in user_dict  # Not included by default

    def test_user_to_dict_with_preferences(self, app, test_user):
        """Test user to_dict with preferences."""
        with app.app_context():
            test_user.preferences = json.dumps({'theme': {'color': 'dark'}})
            db.session.commit()

            user_dict = test_user.to_dict(include_preferences=True)
            assert 'preferences' in user_dict

    def test_user_get_preference(self, app, test_user):
        """Test getting user preferences."""
        with app.app_context():
            test_user.preferences = json.dumps({
                'theme': {'color': 'dark', 'font': 'large'}
            })
            db.session.commit()

            assert test_user.get_preference('theme', 'color') == 'dark'
            assert test_user.get_preference('theme', 'font') == 'large'
            assert test_user.get_preference('theme', 'missing', 'default') == 'default'
            assert test_user.get_preference('missing', 'key') is None

    def test_user_get_preferences(self, app, test_user):
        """Test getting all preferences."""
        with app.app_context():
            test_user.preferences = json.dumps({
                'theme': {'color': 'dark'},
                'notifications': {'enabled': True}
            })
            db.session.commit()

            # Get all preferences
            all_prefs = test_user.get_preferences()
            assert 'theme' in all_prefs
            assert 'notifications' in all_prefs

            # Get section preferences
            theme_prefs = test_user.get_preferences('theme')
            assert theme_prefs == {'color': 'dark'}

    def test_user_get_preferences_invalid_json(self, app, test_user):
        """Test getting preferences with invalid JSON."""
        with app.app_context():
            test_user.preferences = 'invalid json'
            db.session.commit()

            prefs = test_user.get_preferences()
            assert prefs == {}

    def test_user_unique_email(self, app, db_session, test_user):
        """Test that email must be unique."""
        with app.app_context():
            duplicate_user = User(
                email='test@test.com',  # Same as test_user
                password_hash='password'
            )
            db.session.add(duplicate_user)

            with pytest.raises(Exception):  # Should raise IntegrityError
                db.session.commit()


class TestMemoModel:
    """Test Memo model."""

    def test_memo_creation(self, app, db_session, test_user):
        """Test creating a memo."""
        with app.app_context():
            memo = Memo(
                name='New Memo',
                description='Description',
                content='Content',
                author_id=test_user.id
            )
            db.session.add(memo)
            db.session.commit()

            assert memo.id is not None
            assert memo.name == 'New Memo'
            assert memo.description == 'Description'
            assert memo.content == 'Content'
            assert memo.author_id == test_user.id
            assert memo.created_at is not None
            assert memo.updated_at is not None

    def test_memo_to_dict(self, app, test_memo):
        """Test memo to_dict method."""
        with app.app_context():
            # Refresh the memo to get relationships
            memo = Memo.query.filter_by(id=test_memo.id).first()
            memo_dict = memo.to_dict()

            assert memo_dict['id'] == test_memo.id
            assert memo_dict['name'] == 'Test Memo'
            assert memo_dict['description'] == 'Test Description'
            assert memo_dict['content'] == 'Test Content'
            assert memo_dict['category_name'] == 'Test Category'
            assert memo_dict['type_name'] == 'Test Type'
            assert 'author_email' in memo_dict
            assert 'author_username' in memo_dict
            assert 'created_at' in memo_dict
            assert 'updated_at' in memo_dict

    def test_memo_relationships(self, app, test_memo, test_user, test_category, test_type):
        """Test memo relationships."""
        with app.app_context():
            # Refresh the memo to get relationships
            memo = Memo.query.filter_by(id=test_memo.id).first()
            assert memo.author.id == test_user.id
            assert memo.category.id == test_category.id
            assert memo.type.id == test_type.id

    def test_memo_without_category_type(self, app, db_session, test_user):
        """Test creating memo without category and type."""
        with app.app_context():
            memo = Memo(
                name='Simple Memo',
                content='Content',
                author_id=test_user.id
            )
            db.session.add(memo)
            db.session.commit()

            memo_dict = memo.to_dict()
            assert memo_dict['category_name'] is None
            assert memo_dict['type_name'] is None


class TestCategoryModel:
    """Test Category model."""

    def test_category_creation(self, app, db_session):
        """Test creating a category."""
        with app.app_context():
            category = Category(name='New Category')
            db.session.add(category)
            db.session.commit()

            assert category.id is not None
            assert category.name == 'New Category'
            assert category.created_at is not None
            assert category.updated_at is not None

    def test_category_unique_name(self, app, db_session, test_category):
        """Test that category name must be unique."""
        with app.app_context():
            duplicate_category = Category(name='Test Category')
            db.session.add(duplicate_category)

            with pytest.raises(Exception):  # Should raise IntegrityError
                db.session.commit()

    def test_category_memo_relationship(self, app, test_category, test_memo):
        """Test category-memo relationship."""
        with app.app_context():
            # Refresh the category to get relationships
            category = Category.query.filter_by(id=test_category.id).first()
            assert len(category.memos) == 1
            assert category.memos[0].id == test_memo.id


class TestTypeModel:
    """Test Type model."""

    def test_type_creation(self, app, db_session):
        """Test creating a type."""
        with app.app_context():
            type_obj = Type(name='New Type')
            db.session.add(type_obj)
            db.session.commit()

            assert type_obj.id is not None
            assert type_obj.name == 'New Type'
            assert type_obj.created_at is not None
            assert type_obj.updated_at is not None

    def test_type_unique_name(self, app, db_session, test_type):
        """Test that type name must be unique."""
        with app.app_context():
            duplicate_type = Type(name='Test Type')
            db.session.add(duplicate_type)

            with pytest.raises(Exception):  # Should raise IntegrityError
                db.session.commit()

    def test_type_memo_relationship(self, app, test_type, test_memo):
        """Test type-memo relationship."""
        with app.app_context():
            # Refresh the type to get relationships
            type_obj = Type.query.filter_by(id=test_type.id).first()
            assert len(type_obj.memos) == 1
            assert type_obj.memos[0].id == test_memo.id


class TestConfigModel:
    """Test Config model."""

    def test_config_defaults(self, app, db_session):
        """Test config default values."""
        with app.app_context():
            config = Config.query.filter_by(id=1).first()
            assert config is not None
            assert config.enable_auth is True
            assert 'test.com' in config.allowed_domains

    def test_config_modification(self, app, db_session):
        """Test modifying config."""
        with app.app_context():
            config = Config.query.filter_by(id=1).first()
            config.enable_auth = False
            config.allowed_domains = '["newdomain.com"]'
            db.session.commit()

            updated_config = Config.query.filter_by(id=1).first()
            assert updated_config.enable_auth is False
            assert updated_config.allowed_domains == '["newdomain.com"]'
