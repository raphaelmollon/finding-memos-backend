from flask import Blueprint, request, jsonify
from app.models.database import get_db_connection
from app.middleware import auth_required
import sqlite3

categories_bp = Blueprint('categories', __name__)

# Route to list all categories
@categories_bp.route('/', methods=['GET'])
@auth_required
def get_categories():
    with get_db_connection() as conn:
        categories = conn.execute('SELECT * FROM categories').fetchall()

    return jsonify([dict(category) for category in categories])

# Route to add a category
@categories_bp.route('', methods=['POST'])
@auth_required
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

@categories_bp.route('/<int:id>', methods=['PUT'])
@auth_required
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

