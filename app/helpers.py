import logging
from app.database import db
from app.models import Category, Type, Memo
import re

def get_or_create_category(category_name):
    """Helper to get or create a category"""
    if not category_name:
        return None
    category = Category.query.filter_by(name=category_name).first()
    if not category:
        category = Category(name=category_name)
        db.session.add(category)
        db.session.flush()  # Get an ID without committing
    return category

def get_or_create_type(type_name):
    """Helper to get or create a type"""
    if not type_name:
        return None
    type_obj = Type.query.filter_by(name=type_name).first()
    if not type_obj:
        type_obj = Type(name=type_name)
        db.session.add(type_obj)
        db.session.flush()  # Get an ID without committing
    return type_obj

def clean_unused_categories():
    """Clean up unused categories"""
    unused_categories = Category.query.filter(
        ~Category.memos.any()
    ).all()
    for category in unused_categories:
        db.session.delete(category)

def clean_unused_types():
    """Clean up unused types"""
    unused_types = Type.query.filter(
        ~Type.memos.any()
    ).all()
    for type_obj in unused_types:
        db.session.delete(type_obj)

def clean_unused_category(category_id):
    """Clean up a category if it's no longer used"""
    if not category_id:
        return
        
    category_still_used = Memo.query.filter_by(category_id=category_id).first()
    if not category_still_used:
        Category.query.filter_by(id=category_id).delete()
        logging.debug(f"Cleaned up unused category ID: {category_id}")

def clean_unused_type(type_id):
    """Clean up a type if it's no longer used"""
    if not type_id:
        return
        
    type_still_used = Memo.query.filter_by(type_id=type_id).first()
    if not type_still_used:
        Type.query.filter_by(id=type_id).delete()
        logging.debug(f"Cleaned up unused type ID: {type_id}")

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number"
    if not re.search(r'[²&~\"#\'{(\[\-|`_\\^@)\]°+=}£$¤µ*%§!\/:\.;?,<>]', password):
        return "Password must contain at least one special character (² & ~ \" # ' { ( [ - | ` _ \ ^ @ ) ] ° + = } £ $ ¤ µ * % § ! / : . ; ? , < > )"
    return None

