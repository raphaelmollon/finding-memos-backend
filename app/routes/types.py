from flask import request
from flask_restx import Namespace, Resource, fields
from app.database import db
from app.models import Type
from app.middleware import auth_required
import logging

types_ns = Namespace('types', description='Types operations')

# Models
type_model = types_ns.model('Type', {
    'id': fields.Integer(description='Type ID'),
    'name': fields.String(description='Type name')
})

type_input_model = types_ns.model('TypeInput', {
    'name': fields.String(description='Type name')
})

# Route to list all types
@types_ns.route('/')
class TypeList(Resource):
    @auth_required
    @types_ns.response(200, "Success", [type_model])
    @types_ns.response(500, "Internal server error")
    def get(self):
        try:
            types = Type.query.all()
            result = [{"id": type_obj.id, "name":type_obj.name} for type_obj in types]

            return result, 200
        except Exception as e:
            logging.error(f"Error fetching types: {e}")
            return {"error": "Failed to fetch types"}, 500

    # Route to add a new type
    @auth_required
    @types_ns.expect(type_input_model)
    @types_ns.response(201, "Type created")
    @types_ns.response(400, "Bad request")
    @types_ns.response(409, "Type exists already")
    @types_ns.response(500, "Internal server error")
    def post(self):
        new_type = request.get_json()
        name = new_type.get('name')

        if not name:
            return {"error": "Type name is required."}, 400

        try:
            existing_type = Type.query.filter_by(name=name).first()
            if existing_type:
                return {"error": "Type already exists."}, 409

            # Create new type
            type_obj = Type(name=name)
            db.session.add(type_obj)
            db.session.commit()

            return {"message": "New type added successfully."}, 201

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding type: {e}")
            return {"error": "Failed to add type"}, 500
    

@types_ns.route('/<int:id>')
class TypeResource(Resource):
    @auth_required
    @types_ns.expect(type_input_model)
    @types_ns.response(200, "Type updated")
    @types_ns.response(400, "Bad request")
    @types_ns.response(404, "Type not found")
    @types_ns.response(409, "Type already exists")
    @types_ns.response(500, "Internal server error")
    def put(self, id):
        updated_type = request.get_json()
        name = updated_type.get('name')

        if not name:
            return {"error": "Type name is required."}, 400

        try:
            # Check if type exists
            type_obj = Type.query.filter_by(id=id).first()
            if not type_obj:
                return {"error": "Type not found"}, 404
            
            # Check if name already exists for another type
            existing_type = Type.query.filter(
                Type.name == name,
                Type.id != id
            ).first()

            if existing_type:
                return {"error": "Type name already exists"}, 409
            
            # Update type
            type_obj.name = name
            db.session.commit()

            return {"message": "Type updated successfully"}, 200
        
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating type: {e}")
            return {"error": "Failed to update type"}, 500