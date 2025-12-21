from flask import request, g
from flask_restx import Namespace, Resource, fields

from app.database import db
from app.models import Memo, Category, Type
from app.middleware import auth_required
from app.helpers import get_or_create_category, get_or_create_type, clean_unused_category, clean_unused_type

import logging
from datetime import datetime

memos_ns = Namespace('memos', description='Memos operations')

# Models
category_model = memos_ns.model('Category', {
    'id': fields.Integer(description='Category ID'),
    'name': fields.String(description='Category name')
})

type_model = memos_ns.model('Type', {
    'id': fields.Integer(description='Type ID'), 
    'name': fields.String(description='Type name')
})

memo_model = memos_ns.model('Memo', {
    'id': fields.Integer(description='Memo ID'),
    'name': fields.String(required=True, description='Memo name'),
    'description': fields.String(description='Memo description'),
    'content': fields.String(required=True, description='Memo content'),
    'category_id': fields.Integer(description='Category ID'),
    'type_id': fields.Integer(description='Type ID'),
    'category_name': fields.String(description='Category name'),
    'type_name': fields.String(description='Type name'),
    'author_id': fields.Integer(description='Author user ID'),
    'author_email': fields.String(description='Author email'),
    'author_username': fields.String(description='Author username'),
    'author_avatar': fields.String(description='Author avatar'),
    'created_at': fields.String(description='Creation date'),
    'updated_at': fields.String(description='Last update date')
})

memo_input_model = memos_ns.model('MemoInput', {
    'name': fields.String(required=True, description='Memo name'),
    'description': fields.String(description='Memo description'),
    'content': fields.String(required=True, description='Memo content'),
    'category_name': fields.String(description='Category name'),
    'type_name': fields.String(description='Type name'),
    'author_id': fields.Integer(description='Author id')
})

# Route to list all memos
@memos_ns.route('')
class MemoList(Resource):
    @auth_required
    @memos_ns.response(200, 'Success', [memo_model])
    @memos_ns.response(500, 'Internal server error')
    def get(self):
        try:
            """Get all memos"""
            memos = Memo.query.all()
            result = [memo.to_dict() for memo in memos]
            return result, 200
        except Exception as e:
            logging.error(f"Error fetching memos: {str(e)}")
            return {"error": "Failed to fetch memos. Please try again later."}, 500

    @auth_required
    @memos_ns.expect(memo_input_model)
    @memos_ns.response(201, 'Memo created')
    @memos_ns.response(400, 'Bad Request')
    @memos_ns.response(500, 'Internal server error')
    def post(self):
        """Add a memo"""
        logging.debug("Entering add_memo")
        new_memo = request.get_json()
        name = new_memo.get('name')
        description = new_memo.get('description')
        content = new_memo.get('content')
        category_name = new_memo.get('category_name')
        type_name = new_memo.get('type_name')
    
        if not name or not content:
            return {"error": "Name and content are required."}, 400
    
        try:
            # Handle category
            category = get_or_create_category(category_name)

            # Handle type
            type_obj = get_or_create_type(type_name)

            # Insert memo
            memo = Memo(
                name=name, 
                description=description, 
                content=content, 
                category=category, 
                type=type_obj,
                author_id=g.user.id
            )
            db.session.add(memo)
            db.session.commit()

            return {"message": "New memo added successfully."}, 201

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding memo: {str(e)}")
            return {"error": str(e)}, 500

# Route to delete a memo
@memos_ns.route('/<int:id>')
class MemoResource(Resource):
    @auth_required
    @memos_ns.expect(int)
    @memos_ns.response(200, "Memo deleted")
    @memos_ns.response(403, "Forbidden")
    @memos_ns.response(404, "Memo not found")
    @memos_ns.response(500, 'Internal server error')
    def delete(self, id):
        """Delete a memo"""
        logging.debug(f"delete memo id=<{id}>")
        try:
            # Get information about the memo
            memo = Memo.query.filter_by(id=id).first()
            if not memo:
                return {"error": "Memo not found."}, 404
            
            if memo.author_id != g.user.id and not g.user.is_superuser:
                return {"error": "Unauthorized - can only delete your own memos"}, 403

            old_category_id = memo.category_id
            old_type_id = memo.type_id

            db.session.delete(memo)
            db.session.commit()
            logging.debug(f"delete memo deletion done")

            # Clean up unused category and type
            clean_unused_category(old_category_id)
            clean_unused_type(old_type_id)        
            db.session.commit()

            return {"message": "Memo deleted successfully."}, 200
        
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error deleting memo: {str(e)}")
            return {"error": str(e)}, 500

    # Route to update a memo
    @memos_ns.expect(memo_input_model)
    @auth_required
    @memos_ns.response(200, "Memo updated")
    @memos_ns.response(400, "Bad Request")
    @memos_ns.response(403, "Forbidden")
    @memos_ns.response(404, "Memo not found")
    @memos_ns.response(500, 'Internal server error')
    def put(self, id):
        """Update a memo"""
        updated_memo = request.get_json()
        name = updated_memo.get('name')
        description = updated_memo.get('description')
        content = updated_memo.get('content')
        category_name = updated_memo.get('category_name')
        type_name = updated_memo.get('type_name')
        author_id = updated_memo.get('author_id')

        if not name or not content:
            return {"error": "Name and content are required."}, 400
        
        if author_id != g.user.id and not g.user.is_superuser:
            return {"error": "Unauthorized - can only edit your own memos"}, 403

        try:
            # Get the existing memo
            memo = Memo.query.filter_by(id=id, author_id=author_id).first()
            if not memo:
                return {"error": "Memo not found."}, 404

            old_category_id = memo.category_id
            old_type_id = memo.type_id

            # Handle category
            category = get_or_create_category(category_name)

            # Handle type
            type_obj = get_or_create_type(type_name)

            # Update memo
            memo.name = name
            memo.description = description
            memo.content = content
            memo.category = category
            memo.type = type_obj

            db.session.commit()

            # Clean up old categort and type if they are no longer used
            new_category_id = category.id if category else None
            new_type_id = type_obj.id if type_obj else None
            
            if old_category_id != new_category_id:
                clean_unused_category(old_category_id)
                
            if old_type_id != new_type_id:
                clean_unused_type(old_type_id)
                
            db.session.commit()

            return {"message": "Memo updated successfully."}, 200

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating memo: {str(e)}")
            return {"error": str(e)}, 500

# Route to export current user's memos
@memos_ns.route('/export')
class MemosExport(Resource):
    @auth_required
    @memos_ns.response(200, 'Export successful')
    @memos_ns.response(500, 'Internal server error')
    def get(self):
        """Export all memos for the current user"""
        try:
            memos = Memo.query.filter_by(author_id=g.user.id).all()

            memos_list = []
            for memo in memos:
                memo_dict = {
                    "name": memo.name,
                    "description": memo.description,
                    "content": memo.content,
                    "category_name": memo.category.name if memo.category else None,
                    "type_name": memo.type.name if memo.type else None,
                    "created_at": memo.created_at.isoformat() if memo.created_at else None,
                    "updated_at": memo.updated_at.isoformat() if memo.updated_at else None
                }
                memos_list.append(memo_dict)

            return {
                "memos": memos_list,
                "count": len(memos_list),
                "exported_at": datetime.now().isoformat()
            }, 200

        except Exception as e:
            logging.error(f"Error exporting memos: {str(e)}")
            return {"error": "Failed to export memos. Please try again later."}, 500

# Route to import memos for current user
@memos_ns.route('/import')
class MemosImport(Resource):
    @auth_required
    @memos_ns.response(200, 'Success')
    def get(self):
        """Get help on the memo import format"""
        help_info = {
            "description": "Import multiple memos at once using JSON format",
            "format": {
                "memos": [
                    {
                        "name": "string (required) - The memo title",
                        "content": "string (required) - The memo content",
                        "description": "string (optional) - A description of the memo",
                        "category_name": "string (optional) - Category name (will be created if it doesn't exist)",
                        "type_name": "string (optional) - Type name (will be created if it doesn't exist)"
                    }
                ]
            },
            "example": {
                "memos": [
                    {
                        "name": "My First Memo",
                        "content": "This is the content of my memo",
                        "description": "A simple memo example",
                        "category_name": "Work",
                        "type_name": "Note"
                    },
                    {
                        "name": "Another Memo",
                        "content": "Another memo content",
                        "category_name": "Personal"
                    }
                ]
            },
            "notes": [
                "All memos will be associated with your user account",
                "Categories and types will be created automatically if they don't exist",
                "Invalid memos (missing name or content) will be skipped",
                "You can export your current memos using GET /memos/export"
            ]
        }
        return help_info, 200

    @auth_required
    @memos_ns.response(201, 'Import successful')
    @memos_ns.response(400, 'Bad request')
    @memos_ns.response(500, 'Internal server error')
    def post(self):
        """Import memos for the current user"""
        import_data = request.get_json()

        if not import_data:
            return {"error": "No data provided for import"}, 400

        if not isinstance(import_data, dict):
            return {"error": "Data must be a JSON object with a 'memos' array"}, 400

        memos_data = import_data.get('memos', [])

        if not isinstance(memos_data, list):
            return {"error": "'memos' must be an array of memo objects"}, 400

        if len(memos_data) == 0:
            return {"error": "No memos provided in the 'memos' array"}, 400

        try:
            imported_count = 0
            skipped_count = 0
            errors = []

            for index, memo_data in enumerate(memos_data):
                name = memo_data.get('name')
                content = memo_data.get('content')
                description = memo_data.get('description', '')
                category_name = memo_data.get('category_name')
                type_name = memo_data.get('type_name')

                # Validate required fields
                if not name or not content:
                    skipped_count += 1
                    errors.append(f"Memo at index {index}: Missing required field (name or content)")
                    continue

                # Get or create category and type
                category = get_or_create_category(category_name) if category_name else None
                type_obj = get_or_create_type(type_name) if type_name else None

                # Create memo
                memo = Memo(
                    name=name,
                    description=description,
                    content=content,
                    category=category,
                    type=type_obj,
                    author_id=g.user.id
                )
                db.session.add(memo)
                imported_count += 1

            db.session.commit()

            response = {
                "message": f"Import completed. {imported_count} memos imported successfully.",
                "imported": imported_count,
                "skipped": skipped_count
            }

            if errors:
                response["errors"] = errors

            return response, 201

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error importing memos: {str(e)}")
            return {"error": f"Failed to import memos: {str(e)}"}, 500

# Route to get the number of registered memos
@memos_ns.route('/stats')
class MemosStats(Resource):
    @auth_required
    @memos_ns.response(200, 'Success')
    @memos_ns.response(500, 'Internal server error')
    def get(self):
        try:
            """Count the memos"""
            count = Memo.query.count()
            authors = db.session.query(Memo.author_id).distinct().count()
            categories = db.session.query(Memo.category_id).distinct().count()
            types = db.session.query(Memo.type_id).distinct().count()
            return {"count": count, "authors": authors, "categories": categories, "types": types}, 200
        except Exception as e:
            logging.error(f"Error generating memo stats: {str(e)}")
            return {"error": "Failed to generate memo stats. Please try again later."}, 500

