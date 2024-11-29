from flask import Blueprint, request, jsonify
from app.models.database import get_db_connection
from app.middleware import auth_required

global_bp = Blueprint('global', __name__)

# Route to export the entire database
@global_bp.route('/export', methods=['GET'])
@auth_required
def export_database():
    with get_db_connection() as conn:
        try:
            # Fetch all data from categories
            categories = conn.execute('SELECT * FROM categories').fetchall()
            categories_list = [dict(category) for category in categories]

            # Fetch all data from categories
            types = conn.execute('SELECT * FROM types').fetchall()
            types_list = [dict(type) for type in types]

            # Fetch all data from memos
            memos = conn.execute('SELECT * FROM memos').fetchall()
            memos_list = [dict(memo) for memo in memos]

            # Combine data into a single dictionary
            export_data = {
                'categories': categories_list,
                'types': types_list,
                'memos': memos_list
            }

            return jsonify(export_data)

        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
@global_bp.route('/import', methods=['POST'])
@auth_required
def import_database():
    try:
        # Get the JSON data from the request
        import_data = request.get_json()
        if not import_data:
            return jsonify({"error": "No data provided for import"}), 400

        categories = import_data.get('categories', [])
        types = import_data.get('types', [])
        memos = import_data.get('memos', [])

        with get_db_connection() as conn:
            # Create mappings for categories and types (name -> id)
            category_name_to_id = {}
            type_name_to_id = {}

            # Import categories
            for category in categories:
                name = category.get('name')
                if not name:
                    continue  # Skip categories without a name

                # Check if the category already exists
                existing_category = conn.execute('SELECT id FROM categories WHERE name = ?', (name,)).fetchone()
                if existing_category:
                    category_id = existing_category['id']
                else:
                    # Insert the new category
                    cursor = conn.execute('INSERT INTO categories (name) VALUES (?)', (name,))
                    category_id = cursor.lastrowid

                category_name_to_id[name] = category_id

            # Import types
            for type_entry in types:
                name = type_entry.get('name')
                if not name:
                    continue  # Skip types without a name

                # Check if the type already exists
                existing_type = conn.execute('SELECT id FROM types WHERE name = ?', (name,)).fetchone()
                if existing_type:
                    type_id = existing_type['id']
                else:
                    # Insert the new type
                    cursor = conn.execute('INSERT INTO types (name) VALUES (?)', (name,))
                    type_id = cursor.lastrowid

                type_name_to_id[name] = type_id

            # Import memos
            for memo in memos:
                name = memo.get('name')
                description = memo.get('description')
                content = memo.get('content')
                category_id = memo.get('category_id')
                type_id = memo.get('type_id')

                if not name or not content:
                    continue  # Skip incomplete memos

                # Map category_id using name
                if category_id:
                    # Get the category name from the imported data
                    category = next((c for c in categories if c.get('id') == category_id), None)
                    if category:
                        category_name = category.get('name')
                        category_id = category_name_to_id.get(category_name)
                    else:
                        category_id = None

                # Map type_id using name
                if type_id:
                    # Get the type name from the imported data
                    type_entry = next((t for t in types if t.get('id') == type_id), None)
                    if type_entry:
                        type_name = type_entry.get('name')
                        type_id = type_name_to_id.get(type_name)
                    else:
                        type_id = None

                # Insert the memo
                conn.execute('''
                    INSERT INTO memos (name, description, content, category_id, type_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, description, content, category_id, type_id))

        return jsonify({"message": "Data imported successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

