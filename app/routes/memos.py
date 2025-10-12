from flask import request
from flask_restx import Namespace, Resource, fields

from app.database import db
from app.models import Memo, Category, Type
from app.middleware import auth_required
from app.helpers import get_or_create_category, get_or_create_type, clean_unused_category, clean_unused_type

import logging

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
    'type_name': fields.String(description='Type name')
})

memo_input_model = memos_ns.model('MemoInput', {
    'name': fields.String(required=True, description='Memo name'),
    'description': fields.String(description='Memo description'),
    'content': fields.String(required=True, description='Memo content'),
    'category_name': fields.String(description='Category name'),
    'type_name': fields.String(description='Type name')
})

# Route to list all memos
@memos_ns.route('/')
class MemoList(Resource):
    @auth_required
    @memos_ns.response(200, 'Success', [memo_model])
    @memos_ns.response(500, 'Internal server error')
    def get(self):
        try:
            """Get all memos"""
            memos = Memo.query.all()

            result = []
            for memo in memos:
                result.append({
                    'id': memo.id,
                    'name': memo.name,
                    'description': memo.description,
                    'content': memo.content,
                    'category_id': memo.category_id,
                    'type_id': memo.type_id, 
                    'category_name': memo.category.name if memo.category else None,
                    'type_name': memo.type.name if memo.type else None
                })
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
                type=type_obj
            )
            db.session.add(memo)
            db.session.commit()

            return {"message": "New memo added successfully."}, 201

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding memo: {e}")
            return {"error": str(e)}, 500

# Route to delete a memo
@memos_ns.route('/<int:id>')
class MemoResource(Resource):
    @auth_required
    @memos_ns.expect(int)
    @memos_ns.response(200, "Memo deleted")
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
            logging.error(f"Error deleting memo: {e}")
            return {"error": str(e)}, 500

    # Route to update a memo
    @auth_required
    @memos_ns.expect(memo_input_model)
    @memos_ns.response(200, "Memo updated")
    @memos_ns.response(400, "Bad Request")
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

        if not name or not content:
            return {"error": "Name and content are required."}, 400

        try:
            # Get the existing memo
            memo = Memo.query.filter_by(id=id).first()
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
            logging.error(f"Error updating memo: {e}")
            return {"error": str(e)}, 500

# Route to add multiple memos at once
@memos_ns.route('/bulk')
class MemosBulk(Resource):
    @auth_required
    @memos_ns.expect([memo_input_model])
    @memos_ns.response(201, "Memos imported")
    @memos_ns.response(400, "Bad request")
    @memos_ns.response(500, 'Internal server error')
    def post(self):
        """Import memos"""
        memos_data = request.get_json()

        # Check if the data is valid
        if not isinstance(memos_data, list):
            return {"error": "Data must be a list of memos."}, 400

        try:
            for memo_data in memos_data:
                name = memo_data.get('name')
                description = memo_data.get('description', '')
                content = memo_data.get('content')
                category_name = memo_data.get('category')
                type_name = memo_data.get('type')

                if not name or not content:
                    continue  # Ignore invalid entries

                # Get or create category and type
                category = get_or_create_category(category_name)
                type_obj = get_or_create_type(type_name)

                # Insert the memo into the memos table
                memo = Memo(
                    name=name,
                    description=description,
                    content=content,
                    category=category,
                    type=type_obj
                )
                db.session.add(memo)
            
            db.session.commit()
            return {"message": "Memos imported successfully."}, 201

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding bulk memos: {e}")
            return jsonify({"error": str(e)}), 500


