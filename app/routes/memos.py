from flask import Blueprint, request, jsonify, session
from app.models.database import get_db_connection
from app.middleware import auth_required
from app.models.helpers import get_or_create_id_by_name, clean_unused_foreign_key_references
import logging

memos_bp = Blueprint('memos', __name__)

# Route to list all memos
@memos_bp.route('/', methods=['GET'])
@auth_required
def get_memos():
    with get_db_connection() as conn:
        memos = conn.execute('''
            SELECT memos.*, categories.name AS category_name, types.name AS type_name
            FROM memos
            LEFT JOIN categories ON memos.category_id = categories.id
            LEFT JOIN types ON memos.type_id = types.id
        ''').fetchall()

    return jsonify([dict(memo) for memo in memos])

# Route to add a new memo
@memos_bp.route('', methods=['POST'])
@auth_required
def add_memo():
    logging.debug("Entering add_memo")
    new_memo = request.get_json()
    name = new_memo.get('name')
    description = new_memo.get('description')
    content = new_memo.get('content')
    category_name = new_memo.get('category_name')
    type_name = new_memo.get('type_name')
    
    if not name or not content:
        return jsonify({"error": "Name and content are required."}), 400
    
    with get_db_connection() as conn:
        try:
            # Handle category
            category_id = None
            if category_name:
                category_id = get_or_create_id_by_name(conn, 'categories', category_name)

            # Handle type
            type_id = None
            if type_name:
                type_id = get_or_create_id_by_name(conn, 'types', type_name)

            # Insert memo
            conn.execute('INSERT INTO memos (name, description, content, category_id, type_id) VALUES (?, ?, ?, ?, ?)',
                        (name, description, content, category_id, type_id))
            return jsonify({"message": "New memo added successfully."}), 201

        except Exception as e:
            return jsonify({"error": str(e)}), 500

# Route to delete a memo
@memos_bp.route('/<int:id>', methods=['DELETE'])
@auth_required
def delete_memo(id):
    logging.debug(f"delete memo id=<{id}>")
    with get_db_connection() as conn:
        try:
            # Get information about the memo
            memo_to_delete = conn.execute('SELECT * FROM memos WHERE id = ?', (id,)).fetchone()
            if not memo_to_delete:
                return jsonify({"error": "Memo not found."}), 404

            conn.execute('DELETE FROM memos WHERE id = ?', (id,))
            logging.debug(f"delete memo deletion done")

            # Clean up unused categories and types
            clean_unused_foreign_key_references(conn, 'memos', 'category', memo_to_delete['category_id'])
            clean_unused_foreign_key_references(conn, 'memos', 'type', memo_to_delete['type_id'])

            return jsonify({"message": "Memo deleted successfully."}), 200
        
        except Exception as e:
            logging.error(e)
            return jsonify({"error": str(e)}), 500

# Route to update a memo
@memos_bp.route('/<int:id>', methods=['PUT'])
@auth_required
def update_memo(id):
    updated_memo = request.get_json()
    name = updated_memo.get('name')
    description = updated_memo.get('description')
    content = updated_memo.get('content')
    category_name = updated_memo.get('category_name')
    type_name = updated_memo.get('type_name')

    if not name or not content:
        return jsonify({"error": "Name and content are required."}), 400

    with get_db_connection() as conn:
        try:
            # Get the existing memo
            existing_memo = conn.execute('SELECT * FROM memos WHERE id = ?', (id,)).fetchone()
            if not existing_memo:
                return jsonify({"error": "Memo not found."}), 404

            old_category_id = existing_memo['category_id']
            old_type_id = existing_memo['type_id']

            # Handle category
            category_id = None
            if category_name:
                category_id = get_or_create_id_by_name(conn, 'categories', category_name)

            # Handle type
            type_id = None
            if type_name:
                type_id = get_or_create_id_by_name(conn, 'types', type_name)

            # Update memo
            conn.execute('''
                UPDATE memos
                SET name = ?, description = ?, content = ?, category_id = ?, type_id = ?
                WHERE id = ?
            ''', (name, description, content, category_id, type_id, id))

            # Clean up old categories and types if they are no longer used
            if old_category_id != category_id:
                clean_unused_foreign_key_references(conn, 'memos', 'category', old_category_id)

            if old_type_id != type_id:
                clean_unused_foreign_key_references(conn, 'memos', 'type', old_type_id)

            return jsonify({"message": "Memo updated successfully."}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

# Route to add multiple memos at once
@memos_bp.route('/bulk', methods=['POST'])
@auth_required
def add_memos_bulk():
    memos = request.get_json()

    # Check if the data is valid
    if not isinstance(memos, list):
        return jsonify({"error": "Data must be a list of memos."}), 400

    with get_db_connection() as conn:
        try:
            for memo in memos:
                name = memo.get('name')
                description = memo.get('description', '')
                content = memo.get('content')
                category_name = memo.get('category')
                type_name = memo.get('type')

                if not name or not content:
                    continue  # Ignore invalid entries

                # Get the category id
                category_id = None
                if category_name:
                    category_id = get_or_create_id_by_name(conn, 'categories', category_name)

                # Get the type id
                type_id = None
                if type_name:
                    type_id = get_or_create_id_by_name(conn, 'types', type_name)

                # Insert the memo into the memos table
                conn.execute('''
                    INSERT INTO memos (name, description, content, category_id, type_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, description, content, category_id, type_id))

        except Exception as e:
            # Handle potential errors
            return jsonify({"error": str(e)}), 500

    return jsonify({"message": "Memos added successfully."}), 201

