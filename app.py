from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import sqlite3
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

app = Flask(__name__)
CORS(app)

# Function to connect to the database
def get_db_connection():
    conn = sqlite3.connect('memos.db')
    conn.row_factory = sqlite3.Row
    return conn

# Create the tables and indexes, used once
def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS memos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                content TEXT NOT NULL,
                category_id INTEGER,
                type_id INTEGER,
                FOREIGN KEY (category_id) REFERENCES categories (id),
                FOREIGN KEY (type_id) REFERENCES types (id)
            )
        ''')

        # Add indexes on frequently used columns
        conn.execute('CREATE INDEX IF NOT EXISTS idx_memos_name ON memos (name)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_memos_category ON memos (category_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_memos_type ON memos (type_id)')
    print("Database initialized.")

# Route to list all memos
@app.route('/memos', methods=['GET'])
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
@app.route('/memos', methods=['POST'])
def add_memo():
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
@app.route('/memos/<int:id>', methods=['DELETE'])
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
@app.route('/memos/<int:id>', methods=['PUT'])
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

# Route to list all categories
@app.route('/categories', methods=['GET'])
def get_categories():
    with get_db_connection() as conn:
        categories = conn.execute('SELECT * FROM categories').fetchall()

    return jsonify([dict(category) for category in categories])

# Route to add a category
@app.route('/categories', methods=['POST'])
def add_category():
    new_category = request.get_json()
    name = new_category.get('name')

    if not name:
        return jsonify({"error": "Category name is required."}), 400

    with get_db_connection() as conn:
        try:
            conn.execute('INSERT INTO categories (name) VALUES (?)', (name,))
            return jsonify({"message": "New category added successfully."}), 201

        except sqlite3.IntegrityError:
            return jsonify({"error": "Category already exists"}), 409

# Route to list all types
@app.route('/types', methods=['GET'])
def get_types():
    with get_db_connection() as conn:
        types = conn.execute('SELECT * FROM types').fetchall()

    return jsonify([dict(type) for type in types])

# Route to add a new type
@app.route('/types', methods=['POST'])
def add_type():
    new_type = request.get_json()
    name = new_type.get('name')

    if not name:
        return jsonify({"error": "Type name is required."}), 400

    with get_db_connection() as conn:
        try:
            conn.execute('INSERT INTO types (name) VALUES (?)', (name,))
            return jsonify({"message": "New type added successfully."}), 201

        except sqlite3.IntegrityError:
            return jsonify({"error": "Type already exists."}), 409

# Route to add multiple memos at once
@app.route('/memos/bulk', methods=['POST'])
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


# Route to export the entire database
@app.route('/export', methods=['GET'])
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
    
@app.route('/import', methods=['POST'])
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

@app.route('/categories/<int:id>', methods=['PUT'])
def update_category(id):
    updated_category = request.get_json()
    name = updated_category.get('name')

    if not name:
        return jsonify({"error": "Category name is required."}), 400

    with get_db_connection() as conn:
        try:
            # Check if name already exists for another category
            existing_category = conn.execute('SELECT * FROM categories WHERE name = ? AND id != ?', (name, id)).fetchone()
            if existing_category:
                return jsonify({"error": "Category name already exists."}), 409

            conn.execute('UPDATE categories SET name = ? WHERE id = ?', (name, id))
            return jsonify({"message": "Category updated successfully."}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/categories/<int:id>', methods=['DELETE'])
def delete_category(id):
    with get_db_connection() as conn:
        try:
            # Check if category is in use
            memo = conn.execute('SELECT * FROM memos WHERE category_id = ?', (id,)).fetchone()
            if memo:
                return jsonify({"error": "Cannot delete category, it is used by memos."}), 400

            conn.execute('DELETE FROM categories WHERE id = ?', (id,))
            return jsonify({"message": "Category deleted successfully."}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/types/<int:id>', methods=['PUT'])
def update_type(id):
    updated_type = request.get_json()
    name = updated_type.get('name')

    if not name:
        return jsonify({"error": "Type name is required."}), 400

    with get_db_connection() as conn:
        try:
            # Check if name already exists for another type
            existing_type = conn.execute('SELECT * FROM types WHERE name = ? AND id != ?', (name, id)).fetchone()
            if existing_type:
                return jsonify({"error": "Type name already exists."}), 409

            conn.execute('UPDATE types SET name = ? WHERE id = ?', (name, id))
            return jsonify({"message": "Type updated successfully."}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500


def clean_unused_foreign_key_references(conn, table_to_check, foreign_key_to_check, value_to_check):

    if value_to_check is None:
        return
    
    # List of allowed table and foreign key names
    allowed_tables = ['memos']
    allowed_foreign_keys = {
        'category': 'categories',
        'type': 'types'
    }

    # Validate table and foreign key names
    if table_to_check not in allowed_tables:
        raise ValueError(f"Invalid table name: {table_to_check}")

    if foreign_key_to_check not in allowed_foreign_keys:
        raise ValueError(f"Invalid foreign key: {foreign_key_to_check}")

    foreign_table = allowed_foreign_keys[foreign_key_to_check]

    # Securely construct the SQL query
    sql_query = f'''
        SELECT COUNT(*) FROM {table_to_check}
        WHERE {foreign_key_to_check}_id = ?
    '''

    ret = conn.execute(sql_query, (value_to_check,)).fetchone()[0]

    if ret == 0:
        # Delete the entry in the foreign key table
        delete_query = f'DELETE FROM {foreign_table} WHERE id = ?'
        conn.execute(delete_query, (value_to_check,))
        logging.debug(f"No more {table_to_check} with {foreign_key_to_check} <{value_to_check}> ==> DELETED")

def get_or_create_id_by_name(conn, table_name, name):
    if name is None or name == '':
        return None

    # Validate table name to prevent SQL injection
    allowed_tables = ['categories', 'types']
    if table_name not in allowed_tables:
        raise ValueError(f"Invalid table name: {table_name}")

    # Check if the entry exists
    query = f'SELECT id FROM {table_name} WHERE name = ?'
    result = conn.execute(query, (name,)).fetchone()
    if result:
        return result['id']
    else:
        # Insert new entry
        cursor = conn.execute(f'INSERT INTO {table_name} (name) VALUES (?)', (name,))
        return cursor.lastrowid

if __name__ == '__main__':
    init_db()  # Initialize the database
    app.run(debug=True)

