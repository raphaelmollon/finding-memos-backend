from flask import Blueprint, request, jsonify
from app.models.database import get_db_connection
from app.middleware import auth_required
import sqlite3

types_bp = Blueprint('types', __name__)

# Route to list all types
@types_bp.route('/', methods=['GET'])
@auth_required
def get_types():
    with get_db_connection() as conn:
        types = conn.execute('SELECT * FROM types').fetchall()

    return jsonify([dict(type) for type in types])

# Route to add a new type
@types_bp.route('', methods=['POST'])
@auth_required
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

@types_bp.route('/<int:id>', methods=['PUT'])
@auth_required
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

