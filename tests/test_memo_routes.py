import pytest
import json
from app.models import Memo, Category, Type, User
from app.database import db


class TestMemoList:
    """Test memo list endpoint."""

    def test_get_all_memos(self, authenticated_client, test_memo):
        """Test getting all memos."""
        response = authenticated_client.get('/memos')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]['name'] == 'Test Memo'

    def test_get_all_memos_unauthenticated(self, client):
        """Test getting memos without authentication."""
        response = client.get('/memos')

        assert response.status_code == 401

    def test_get_all_memos_empty(self, authenticated_client, db_session):
        """Test getting memos when none exist."""
        response = authenticated_client.get('/memos')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 0


class TestCreateMemo:
    """Test creating memos."""

    def test_create_memo_success(self, app, authenticated_client, db_session):
        """Test successful memo creation."""
        response = authenticated_client.post('/memos', json={
            'name': 'New Memo',
            'description': 'New Description',
            'content': 'New Content',
            'category_name': 'Work',
            'type_name': 'Note'
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'message' in data
        assert 'success' in data['message']

        # Verify memo was created
        with app.app_context():
            memo = Memo.query.filter_by(name='New Memo').first()
            assert memo is not None
            assert memo.description == 'New Description'
            assert memo.content == 'New Content'

    def test_create_memo_with_new_category(self, app, authenticated_client, db_session):
        """Test creating memo with new category."""
        response = authenticated_client.post('/memos', json={
            'name': 'Test',
            'content': 'Content',
            'category_name': 'New Category'
        })

        assert response.status_code == 201

        # Verify category was created
        with app.app_context():
            category = Category.query.filter_by(name='New Category').first()
            assert category is not None

    def test_create_memo_with_existing_category(self, app, authenticated_client, test_category):
        """Test creating memo with existing category."""
        with app.app_context():
            category_count = Category.query.count()

        response = authenticated_client.post('/memos', json={
            'name': 'Test',
            'content': 'Content',
            'category_name': 'Test Category'
        })

        assert response.status_code == 201

        # Verify no duplicate category was created
        with app.app_context():
            assert Category.query.count() == category_count

    def test_create_memo_without_category(self, authenticated_client, db_session):
        """Test creating memo without category."""
        response = authenticated_client.post('/memos', json={
            'name': 'Test',
            'content': 'Content'
        })

        assert response.status_code == 201

    def test_create_memo_missing_name(self, authenticated_client):
        """Test creating memo without name."""
        response = authenticated_client.post('/memos', json={
            'content': 'Content'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_memo_missing_content(self, authenticated_client):
        """Test creating memo without content."""
        response = authenticated_client.post('/memos', json={
            'name': 'Test'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_memo_unauthenticated(self, client):
        """Test creating memo without authentication."""
        response = client.post('/memos', json={
            'name': 'Test',
            'content': 'Content'
        })

        assert response.status_code == 401


class TestUpdateMemo:
    """Test updating memos."""

    def test_update_memo_success(self, app, authenticated_client, test_memo, test_user):
        """Test successful memo update."""
        response = authenticated_client.put(f'/memos/{test_memo.id}', json={
            'name': 'Updated Memo',
            'description': 'Updated Description',
            'content': 'Updated Content',
            'category_name': 'Updated Category',
            'type_name': 'Updated Type',
            'author_id': test_user.id
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert 'success' in data['message']

        # Verify memo was updated
        with app.app_context():
            memo = Memo.query.filter_by(id=test_memo.id).first()
            assert memo.name == 'Updated Memo'
            assert memo.description == 'Updated Description'
            assert memo.content == 'Updated Content'

    def test_update_memo_change_category(self, app, authenticated_client, test_memo, test_user, test_category):
        """Test updating memo category."""
        with app.app_context():
            old_category_id = test_category.id

        response = authenticated_client.put(f'/memos/{test_memo.id}', json={
            'name': 'Updated',
            'content': 'Updated',
            'category_name': 'Different Category',
            'author_id': test_user.id
        })

        assert response.status_code == 200

        # Old category should be cleaned up if unused
        with app.app_context():
            memo = Memo.query.filter_by(id=test_memo.id).first()
            assert memo.category.name == 'Different Category'

    def test_update_memo_unauthorized(self, app, authenticated_client, db_session, test_user):
        """Test updating another user's memo."""
        with app.app_context():
            # Create another user
            from werkzeug.security import generate_password_hash
            other_user = User(
                email='other@test.com',
                password_hash=generate_password_hash('Password123!'),
                status='VALID'
            )
            db.session.add(other_user)
            db.session.commit()
            other_user_id = other_user.id

            # Create memo for other user
            memo = Memo(
                name='Other Memo',
                content='Content',
                author_id=other_user_id
            )
            db.session.add(memo)
            db.session.commit()
            memo_id = memo.id

        # Try to update with wrong author_id (should fail because test_user doesn't own it)
        response = authenticated_client.put(f'/memos/{memo_id}', json={
            'name': 'Hacked',
            'content': 'Hacked',
            'author_id': other_user_id
        })

        assert response.status_code == 403

    def test_update_memo_not_found(self, authenticated_client, test_user):
        """Test updating non-existent memo."""
        response = authenticated_client.put('/memos/99999', json={
            'name': 'Updated',
            'content': 'Updated',
            'author_id': test_user.id
        })

        assert response.status_code == 404

    def test_update_memo_missing_required_fields(self, authenticated_client, test_memo, test_user):
        """Test updating memo without required fields."""
        response = authenticated_client.put(f'/memos/{test_memo.id}', json={
            'author_id': test_user.id
        })

        assert response.status_code == 400


class TestDeleteMemo:
    """Test deleting memos."""

    def test_delete_memo_success(self, app, authenticated_client, test_memo):
        """Test successful memo deletion."""
        memo_id = test_memo.id

        response = authenticated_client.delete(f'/memos/{memo_id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert 'success' in data['message']

        # Verify memo was deleted
        with app.app_context():
            memo = Memo.query.filter_by(id=memo_id).first()
            assert memo is None

    def test_delete_memo_cleans_unused_category(self, app, authenticated_client, test_memo, test_category):
        """Test that deleting memo cleans up unused category."""
        memo_id = test_memo.id
        category_id = test_category.id

        response = authenticated_client.delete(f'/memos/{memo_id}')

        assert response.status_code == 200

        # Verify category was cleaned up (since it's no longer used)
        with app.app_context():
            category = Category.query.filter_by(id=category_id).first()
            assert category is None

    def test_delete_memo_not_found(self, authenticated_client):
        """Test deleting non-existent memo."""
        response = authenticated_client.delete('/memos/99999')

        assert response.status_code == 404

    def test_delete_memo_unauthorized(self, app, client, test_user, db_session):
        """Test deleting another user's memo."""
        with app.app_context():
            # Create another authenticated user
            from werkzeug.security import generate_password_hash
            other_user = User(
                email='other@test.com',
                password_hash=generate_password_hash('Password123!'),
                status='VALID'
            )
            db.session.add(other_user)
            db.session.commit()
            other_user_id = other_user.id

            # Create memo for other user
            memo = Memo(
                name='Other Memo',
                content='Content',
                author_id=other_user_id
            )
            db.session.add(memo)
            db.session.commit()
            memo_id = memo.id

        # Login as test_user
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id

        # Try to delete other user's memo
        response = client.delete(f'/memos/{memo_id}')

        assert response.status_code == 403

    def test_delete_memo_as_superuser(self, app, superuser_client, db_session, test_user):
        """Test that superuser can delete any memo."""
        with app.app_context():
            # Create memo for regular user
            memo = Memo(
                name='User Memo',
                content='Content',
                author_id=test_user.id
            )
            db.session.add(memo)
            db.session.commit()
            memo_id = memo.id

        response = superuser_client.delete(f'/memos/{memo_id}')

        assert response.status_code == 200


class TestBulkImport:
    """Test bulk memo import."""

    def test_bulk_import_success(self, app, authenticated_client, db_session):
        """Test successful bulk import."""
        memos_data = [
            {
                'name': 'Memo 1',
                'description': 'Desc 1',
                'content': 'Content 1',
                'category': 'Cat1',
                'type': 'Type1'
            },
            {
                'name': 'Memo 2',
                'content': 'Content 2',
                'category': 'Cat2',
                'type': 'Type2'
            }
        ]

        response = authenticated_client.post('/memos/bulk', json=memos_data)

        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'message' in data
        assert 'success' in data['message']

        # Verify memos were created
        with app.app_context():
            assert Memo.query.count() == 2

    def test_bulk_import_skip_invalid(self, app, authenticated_client, db_session):
        """Test bulk import skips invalid entries."""
        memos_data = [
            {
                'name': 'Valid Memo',
                'content': 'Content'
            },
            {
                'name': 'Invalid Memo'
                # Missing content
            },
            {
                'content': 'Content'
                # Missing name
            }
        ]

        response = authenticated_client.post('/memos/bulk', json=memos_data)

        assert response.status_code == 201

        # Only valid memo should be imported
        with app.app_context():
            assert Memo.query.count() == 1
            memo = Memo.query.first()
            assert memo.name == 'Valid Memo'

    def test_bulk_import_invalid_format(self, authenticated_client):
        """Test bulk import with invalid format."""
        response = authenticated_client.post('/memos/bulk', json={'not': 'a list'})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'list' in data['error']


class TestMemoStats:
    """Test memo statistics."""

    def test_memo_stats(self, authenticated_client, test_memo):
        """Test getting memo statistics."""
        response = authenticated_client.get('/memos/stats')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'count' in data
        assert 'authors' in data
        assert 'categories' in data
        assert 'types' in data
        assert data['count'] >= 1

    def test_memo_stats_empty(self, authenticated_client, db_session):
        """Test stats with no memos."""
        response = authenticated_client.get('/memos/stats')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 0

    def test_memo_stats_unauthenticated(self, client):
        """Test stats without authentication."""
        response = client.get('/memos/stats')

        assert response.status_code == 401
