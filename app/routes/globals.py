from flask import Blueprint, request, jsonify
from flask_restx import Namespace, Resource, fields
from app.database import db
from app.models import Category, Type, Memo
from app.middleware import auth_required
import logging
from app.helpers import get_or_create_category, get_or_create_type

globals_ns = Namespace('global', description="Import/Export operations")

# Models
memo_input_model = globals_ns.model('MemoInput', {
    'name': fields.String(required=True, description='Memo name'),
    'description': fields.String(description='Memo description'),
    'content': fields.String(required=True, description='Memo content'),
    'category_name': fields.String(description='Category name'),
    'type_name': fields.String(description='Type name')
})

category_input_model = globals_ns.model('Category', {
    'name': fields.String(description='Category name')
})

type_input_model = globals_ns.model('Type', {
    'name': fields.String(description='Type name')
})

# Route to export the entire database
@globals_ns.route('/export')
class GlobalExport(Resource):
    @auth_required
    @globals_ns.response(200, "Export successful")
    @globals_ns.response(500, "Internal server error")
    def get(self):
        try:
            # Fetch all data using SQLAlchemy
            categories = Category.query.all()
            types = Type.query.all()
            memos = Memo.query.all()

            # Convert to dictionaries
            categories_list = [{"id": cat.id, "name": cat.name} for cat in categories]
            types_list = [{"id": t.id, "name": t.name} for t in types]
            memos_list = [{
                "id": memo.id,
                "name": memo.name,
                "description": memo.description,
                "content": memo.content,
                "category_id": memo.category_id,
                "type_id": memo.type_id
            } for memo in memos]

            # Combine data into a single dictionary
            export_data = {
                'categories': categories_list,
                'types': types_list,
                'memos': memos_list
            }

            return export_data, 200

        except Exception as e:
            logging.error(f"Error exporting database: {e}")
            return {"error": "Failed to export database"}, 500

@globals_ns.route('/import')
class GlobalsImport(Resource):
    @auth_required
    @globals_ns.expect(globals_ns.model('ImportData', {
        'categories': fields.List(fields.Nested(category_input_model)),
        'types': fields.List(fields.Nested(type_input_model)),
        'memos': fields.List(fields.Nested(memo_input_model))
    }))
    @globals_ns.response(201, "Import successful")
    @globals_ns.response(400, "Bad request")
    @globals_ns.response(500, "Internal server error")
    def post(self):
        try:
            # Get the JSON data from the request
            import_data = request.get_json()
            if not import_data:
                return {"error": "No data provided for import"}, 400

            categories_data = import_data.get('categories', [])
            types_data = import_data.get('types', [])
            memos_data = import_data.get('memos', [])

            # Create mappings for categories and types (name -> id)
            category_name_to_id = {}
            type_name_to_id = {}

            # Import categories
            for category in categories_data:
                name = category.get('name')
                if not name:
                    continue  # Skip categories without a name

                category_obj = get_or_create_category(name)
                category_name_to_id[name] = category_obj.id

            # Import types
            for type_entry in types_data:
                name = type_entry.get('name')
                if not name:
                    continue  # Skip types without a name

                type_obj = get_or_create_type(name)
                type_name_to_id[name] = type_obj.id

            # Import memos
            for memo in memos_data:
                name = memo.get('name')
                description = memo.get('description')
                content = memo.get('content')
                category_id = memo.get('category_id')
                type_id = memo.get('type_id')

                if not name or not content:
                    continue  # Skip incomplete memos

                # Map category_id using name
                final_category_id = None
                if category_id:
                    # Get the category name from the imported data
                    category = next((c for c in categories_data if c.get('id') == category_id), None)
                    if category:
                        category_name = category.get('name')
                        final_category_id = category_name_to_id.get(category_name)

                # Map type_id using name
                final_type_id = None
                if type_id:
                    # Get the type name from the imported data
                    type_entry = next((t for t in types_data if t.get('id') == type_id), None)
                    if type_entry:
                        type_name = type_entry.get('name')
                        final_type_id = type_name_to_id.get(type_name)

                # Insert the memo
                new_memo = Memo(
                    name=name,
                    description=description,
                    content=content,
                    category_id=final_category_id,
                    type_id=final_type_id
                )
                db.session.add(new_memo)

            # Commit all changes
            db.session.commit()
            return {"message": "Data imported successfully"}, 201

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error importing database: {e}")
            return {"error": "Failed to import database"}, 500