from flask import request
from flask_restx import Namespace, Resource, fields
from app.database import db
from app.models import Category
from app.middleware import auth_required
import logging

categories_ns = Namespace('categories', description='Categories operations')

# Models
category_model = categories_ns.model('Category', {
    'id': fields.Integer(description='Category ID'),
    'name': fields.String(description='Category name')
})

category_input_model = categories_ns.model('CategoryInput', {
    'name': fields.String(description='Category name')
})

# Route to list all categories
@categories_ns.route('/')
class CategoryList(Resource):
    @auth_required
    @categories_ns.response(200, "Success", [category_model])
    @categories_ns.response(500, "Internal server error")
    def get(self):
        try:
            categories = Category.query.all()
            result = [{"id": category.id, "name": category.name} for category in categories]

            return result, 200
        except Exception as e:
            logging.error(f"Error fetching categories: {e}")
            return {"error": "Failed to fetch categories"}, 500

    # Route to add a category
    @auth_required
    @categories_ns.expect(category_input_model)
    @categories_ns.response(201, "Category created")
    @categories_ns.response(400, "Bad request")
    @categories_ns.response(409, "Category exists already")
    @categories_ns.response(500, "Internal server error")
    def post(self):
        new_category = request.get_json()
        name = new_category.get('name')

        if not name:
            return {"error": "Category name is required."}, 400

        try:
            existing_category = Category.query.filter_by(name=name).first()
            if existing_category:
                return {"error": "Category already exists"}, 409
            
            category = Category(name=name)
            db.session.add(category)
            db.session.commit()

            return {"message": "New category added successfully."}, 201

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding category: {e}")
            return {"error": "Failed to add category"}, 500

@categories_ns.route('/<int:id>')
class CategoryResource(Resource):
    @auth_required
    @categories_ns.expect(category_input_model)
    @categories_ns.response(200, "Category updated")
    @categories_ns.response(400, "Bad request")
    @categories_ns.response(404, "Category not found")
    @categories_ns.response(409, "Category already exists")
    @categories_ns.response(500, "Internal server error")
    def put(self, id):
        updated_category = request.get_json()
        name = updated_category.get('name')

        if not name:
            return {"error": "Category name is required."}, 400

        try:
            category = Category.query.filter_by(id=id).first()
            if not category:
                return {"error": "Category not found"}, 404
            
            # Check if name already exists for another category
            existing_category = Category.query.filter(
                Category.name == name,
                Category.id != id
            ).first()

            if existing_category:
                return {"error": "Category name already exists."}, 409

            category.name = name
            db.session.commit()
            return {"message": "Category updated successfully."}, 200
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating category: {e}")
            return {"error": str(e)}, 500
