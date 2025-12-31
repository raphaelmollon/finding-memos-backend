import os
import json
import logging
import zipfile
import shutil
from datetime import datetime, timezone
from flask import request, g
from flask_restx import Namespace, Resource, fields
from sqlalchemy import or_, and_
from cachetools import TTLCache

from app.database import db
from app.models import Connection, Config, ConnectionUserEngagement
from app.middleware import auth_required
from app.services.encryption_service import encryption_service

connections_ns = Namespace('connections', description='Connections management operations')

# Global cache for decrypted connections
# TTL=300 seconds (5 minutes), maxsize=1 (only one cache entry - all decrypted connections)
# This is shared across all users since everyone sees the same data
decrypted_cache = TTLCache(maxsize=1, ttl=300)
CACHE_KEY = 'all_decrypted_connections'

# API Models for Swagger documentation
# Basic connection model (no encrypted fields - for list/get endpoints)
connection_model = connections_ns.model('Connection', {
    'id': fields.Integer(description='Connection ID'),
    'company_name': fields.String(description='Company name'),
    'site_name': fields.String(description='Site name'),
    'application_name': fields.String(description='Application name'),
    'application_last_update': fields.DateTime(description='Application last update'),
    'connection_last_update': fields.DateTime(description='Connection last update'),
    'server_last_update': fields.DateTime(description='Server last update'),
    'url_id': fields.String(description='URL unique identifier'),
    'url_last_update': fields.DateTime(description='URL last update'),
    'url_mode': fields.String(description='URL mode (classic/extrapolated)'),
    'url_service': fields.String(description='Service type'),
    'url_server_type': fields.String(description='Server type'),
    'url_server_comment': fields.String(description='Server comment'),
    'url_type': fields.String(description='URL type'),
    'has_credentials': fields.Boolean(description='Whether this connection has credentials'),
    'has_url': fields.Boolean(description='Whether this connection has a URL'),
    'rating_up': fields.Integer(description='Thumbs up count'),
    'rating_down': fields.Integer(description='Thumbs down count'),
    'usage_count': fields.Integer(description='Click/copy usage count'),
    'created_at': fields.DateTime(description='Created at'),
    'updated_at': fields.DateTime(description='Updated at'),
    'user_rating': fields.String(description='Current user\'s rating (up/down/null)'),
    'user_usage_count': fields.Integer(description='Current user\'s usage count'),
    'user_first_used_at': fields.DateTime(description='When current user first used this connection'),
    'user_last_used_at': fields.DateTime(description='When current user last used this connection'),
})

# Decrypted connection model (includes decrypted sensitive fields)
decrypted_connection_model = connections_ns.clone('DecryptedConnection', connection_model, {
    'comments': fields.String(description='Decrypted comments'),
    'comment_urls': fields.List(fields.String, description='Decrypted comment URLs'),
    'server_ip': fields.String(description='Decrypted server IP'),
    'url': fields.String(description='Decrypted URL'),
    'user': fields.String(description='Decrypted username'),
    'pwd': fields.String(description='Decrypted password'),
})


def superuser_required(f):
    """Decorator to check if user is superuser"""
    def wrapper(*args, **kwargs):
        if not hasattr(g, 'user') or not g.user.is_superuser:
            return {"error": "Superuser access required"}, 403
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


def get_all_decrypted_connections():
    """
    Get all decrypted connections from cache or decrypt and cache them.

    Returns:
        list: List of all decrypted connection dictionaries
    """
    # Check if cache has valid data
    if CACHE_KEY in decrypted_cache:
        logging.info("Returning decrypted connections from cache")
        return decrypted_cache[CACHE_KEY]

    # Cache miss - decrypt all connections
    logging.info("Cache miss - decrypting all connections")
    all_connections = Connection.query.all()
    decrypted_list = []

    for conn in all_connections:
        conn_dict = conn.to_dict(include_encrypted=True)
        decrypted = encryption_service.decrypt_connection(conn_dict)
        decrypted_list.append(decrypted)

    # Store in cache (TTL will auto-expire after 5 minutes)
    decrypted_cache[CACHE_KEY] = decrypted_list
    logging.info(f"Cached {len(decrypted_list)} decrypted connections")

    return decrypted_list


def clear_decrypted_cache():
    """Clear the decrypted connections cache"""
    if CACHE_KEY in decrypted_cache:
        del decrypted_cache[CACHE_KEY]
        logging.info("Decrypted connections cache cleared")


def get_user_engagement_map(user_id, connection_ids=None):
    """
    Get user engagement data for connections as a dictionary.

    Args:
        user_id: The user's ID
        connection_ids: Optional list of connection IDs to filter by

    Returns:
        dict: Map of connection_id -> engagement data
              e.g., {123: {'rating': 'up', 'usage_count': 5, 'last_used_at': '...'}}
    """
    query = ConnectionUserEngagement.query.filter_by(user_id=user_id)

    if connection_ids:
        query = query.filter(ConnectionUserEngagement.connection_id.in_(connection_ids))

    engagements = query.all()

    engagement_map = {}
    for eng in engagements:
        engagement_map[eng.connection_id] = {
            'rating': eng.rating,
            'usage_count': eng.usage_count,
            'first_used_at': eng.first_used_at.replace(tzinfo=timezone.utc).isoformat() if eng.first_used_at else None,
            'last_used_at': eng.last_used_at.replace(tzinfo=timezone.utc).isoformat() if eng.last_used_at else None,
        }

    return engagement_map


def parse_datetime(date_string):
    """Parse datetime string from various formats"""
    if not date_string or date_string == "None":
        return None

    try:
        # Try ISO format first
        return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    except:
        try:
            # Try common format: "2024-12-19 11:31:25"
            return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
        except:
            logging.warning(f"Could not parse datetime: {date_string}")
            return None


@connections_ns.route('/import')
class ConnectionsImport(Resource):
    @auth_required
    @superuser_required
    @connections_ns.response(200, 'File status retrieved')
    @connections_ns.response(403, 'Forbidden')
    def get(self):
        """Check if connections.zip file is available (superuser only)"""
        zip_path = 'connections.zip'

        if os.path.exists(zip_path):
            try:
                # Get file size
                file_size = os.path.getsize(zip_path)
                # Get last modified time
                modified_time = datetime.fromtimestamp(os.path.getmtime(zip_path), tz=timezone.utc)

                return {
                    "available": True,
                    "file_path": zip_path,
                    "file_size": file_size,
                    "modified_at": modified_time.isoformat()
                }, 200
            except Exception as e:
                logging.error(f"Error reading file info: {e}")
                return {
                    "available": True,
                    "file_path": zip_path,
                    "error": "File exists but cannot read details"
                }, 200
        else:
            return {
                "available": False,
                "file_path": zip_path,
                "message": "connections.zip file not found in root directory"
            }, 200

    @auth_required
    @superuser_required
    @connections_ns.response(200, 'Import successful')
    @connections_ns.response(400, 'Bad request')
    @connections_ns.response(403, 'Forbidden')
    @connections_ns.response(404, 'connections.zip not found')
    @connections_ns.response(500, 'Internal server error')
    def post(self):
        """Import connections from connections.zip file (superuser only)"""
        zip_path = 'connections.zip'

        # Check if connections.zip exists
        if not os.path.exists(zip_path):
            return {"error": "connections.zip file not found in root directory"}, 404

        temp_dir = None
        try:
            # Create temp directory for extraction
            temp_dir = 'temp_connections_import'
            os.makedirs(temp_dir, exist_ok=True)

            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Check for encryption key
            key_changed = False
            encryption_key_path = os.path.join(temp_dir, 'encryption.key')
            if os.path.exists(encryption_key_path):
                with open(encryption_key_path, 'r') as f:
                    new_encryption_key = f.read().strip()

                # Check if key has changed
                config = Config.query.filter_by(id=1).first()
                old_key = config.encryption_key if config else None

                if old_key != new_encryption_key:
                    key_changed = True
                    logging.info("Encryption key has changed - will clear existing connections")

                    # Clear all existing connections since they were encrypted with the old key
                    deleted_count = Connection.query.delete()
                    db.session.commit()
                    logging.info(f"Deleted {deleted_count} existing connections (old encryption key)")

                    # Update encryption key in Config
                    if not encryption_service.set_encryption_key(new_encryption_key):
                        return {"error": "Failed to update encryption key"}, 500

                    logging.info("Encryption key updated from connections.zip")
                else:
                    logging.info("Encryption key unchanged - skipping update")

            # Load connections.json
            connections_json_path = os.path.join(temp_dir, 'connections.json')
            if not os.path.exists(connections_json_path):
                return {"error": "connections.json not found in zip file"}, 400

            with open(connections_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Parse and import connections
            imported_count = 0
            updated_count = 0
            skipped_count = 0

            companies = data.get('connections', [])

            for company in companies:
                company_name = company.get('company_name')

                for site in company.get('sites', []):
                    site_name = site.get('site_name')

                    for application in site.get('applications', []):
                        app_name = application.get('application_name')
                        app_last_update = parse_datetime(application.get('application_last_update'))
                        conn_last_update = parse_datetime(application.get('connection_last_update'))
                        comments = application.get('comments')
                        comment_urls = application.get('comment_urls', [])

                        for server in application.get('servers', []):
                            server_ip = server.get('ip')
                            server_last_update = parse_datetime(server.get('last_update'))

                            for url_data in server.get('urls', []):
                                url_id = url_data.get('id')

                                if not url_id:
                                    skipped_count += 1
                                    logging.warning(f"Skipping URL without ID in {company_name}/{site_name}/{app_name}")
                                    continue

                                # If encryption key changed, table is empty - skip merge checks
                                if key_changed:
                                    # Create new connection (no need to check for existing)
                                    connection = Connection(
                                        company_name=company_name,
                                        site_name=site_name,
                                        application_name=app_name,
                                        application_last_update=app_last_update,
                                        connection_last_update=conn_last_update,
                                        comments=comments,
                                        comment_urls=comment_urls,
                                        server_ip=server_ip,
                                        server_last_update=server_last_update,
                                        url_id=url_id,
                                        url_last_update=parse_datetime(url_data.get('last_update')),
                                        url_mode=url_data.get('mode'),
                                        url_service=url_data.get('service'),
                                        url_server_type=url_data.get('server_type'),
                                        url_server_comment=url_data.get('server_comment'),
                                        url_type=url_data.get('url_type'),
                                        url=url_data.get('url'),
                                        user=url_data.get('user'),
                                        pwd=url_data.get('pwd'),
                                    )
                                    db.session.add(connection)
                                    imported_count += 1
                                else:
                                    # Check if connection exists (by url_id)
                                    existing = Connection.query.filter_by(url_id=url_id).first()

                                    if existing:
                                        # Update existing connection
                                        existing.company_name = company_name
                                        existing.site_name = site_name
                                        existing.application_name = app_name
                                        existing.application_last_update = app_last_update
                                        existing.connection_last_update = conn_last_update
                                        existing.comments = comments
                                        existing.comment_urls = comment_urls
                                        existing.server_ip = server_ip
                                        existing.server_last_update = server_last_update
                                        existing.url_last_update = parse_datetime(url_data.get('last_update'))
                                        existing.url_mode = url_data.get('mode')
                                        existing.url_service = url_data.get('service')
                                        existing.url_server_type = url_data.get('server_type')
                                        existing.url_server_comment = url_data.get('server_comment')
                                        existing.url_type = url_data.get('url_type')
                                        existing.url = url_data.get('url')
                                        existing.user = url_data.get('user')
                                        existing.pwd = url_data.get('pwd')
                                        existing.updated_at = datetime.now(timezone.utc)
                                        updated_count += 1
                                    else:
                                        # Create new connection
                                        connection = Connection(
                                            company_name=company_name,
                                            site_name=site_name,
                                            application_name=app_name,
                                            application_last_update=app_last_update,
                                            connection_last_update=conn_last_update,
                                            comments=comments,
                                            comment_urls=comment_urls,
                                            server_ip=server_ip,
                                            server_last_update=server_last_update,
                                            url_id=url_id,
                                            url_last_update=parse_datetime(url_data.get('last_update')),
                                            url_mode=url_data.get('mode'),
                                            url_service=url_data.get('service'),
                                            url_server_type=url_data.get('server_type'),
                                            url_server_comment=url_data.get('server_comment'),
                                            url_type=url_data.get('url_type'),
                                            url=url_data.get('url'),
                                            user=url_data.get('user'),
                                            pwd=url_data.get('pwd'),
                                        )
                                        db.session.add(connection)
                                        imported_count += 1

            # Commit all changes
            db.session.commit()

            # Clear decrypted cache since data has changed
            clear_decrypted_cache()

            # Delete the zip file after successful import
            os.remove(zip_path)
            logging.info(f"Deleted connections.zip after successful import")

            return {
                "message": "Import completed successfully",
                "imported": imported_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "total": imported_count + updated_count
            }, 200

        except json.JSONDecodeError as e:
            db.session.rollback()
            logging.error(f"Invalid JSON in connections.json: {e}")
            return {"error": f"Invalid JSON format: {str(e)}"}, 400
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error importing connections: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to import connections: {str(e)}"}, 500
        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logging.debug("Cleaned up temp directory")


@connections_ns.route('')
class ConnectionsList(Resource):
    @auth_required
    @connections_ns.doc(params={
        'all': 'Return all connections without pagination or filters (true/false, default: false)',
        'company': 'Filter by company name (case-insensitive partial match)',
        'site': 'Filter by site name (case-insensitive partial match)',
        'application': 'Filter by application name (case-insensitive partial match)',
        'service': 'Filter by service type (exact match)',
        'server_type': 'Filter by server type (partial match)',
        'mode': 'Filter by mode (classic/extrapolated)',
        'has_credentials': 'Filter by credential presence (true/false)',
        'page': 'Page number (default: 1)',
        'per_page': 'Items per page (default: 50, max: 500)'
    })
    @connections_ns.marshal_list_with(connection_model)
    @connections_ns.response(200, 'Success')
    @connections_ns.response(500, 'Internal server error')
    def get(self):
        """Get all connections with optional filters (no encrypted fields returned)"""
        try:
            # Check if 'all' parameter is set
            fetch_all = request.args.get('all', 'false').lower() == 'true'

            if fetch_all:
                # Return all connections without pagination or filters
                all_connections = Connection.query.all()

                # Get user engagement data
                user_id = g.user.id
                connection_ids = [conn.id for conn in all_connections]
                engagement_map = get_user_engagement_map(user_id, connection_ids)

                # Include user engagement in response
                connections = [
                    conn.to_dict(include_encrypted=False, user_engagement=engagement_map.get(conn.id))
                    for conn in all_connections
                ]
                return connections, 200

            # Start with base query
            query = Connection.query

            # Apply filters
            company = request.args.get('company')
            if company:
                query = query.filter(Connection.company_name.ilike(f'%{company}%'))

            site = request.args.get('site')
            if site:
                query = query.filter(Connection.site_name.ilike(f'%{site}%'))

            application = request.args.get('application')
            if application:
                query = query.filter(Connection.application_name.ilike(f'%{application}%'))

            service = request.args.get('service')
            if service:
                query = query.filter(Connection.url_service == service)

            server_type = request.args.get('server_type')
            if server_type:
                query = query.filter(Connection.url_server_type.ilike(f'%{server_type}%'))

            mode = request.args.get('mode')
            if mode:
                query = query.filter(Connection.url_mode == mode)

            has_credentials = request.args.get('has_credentials')
            if has_credentials:
                if has_credentials.lower() == 'true':
                    query = query.filter(and_(Connection.user.isnot(None), Connection.pwd.isnot(None)))
                elif has_credentials.lower() == 'false':
                    query = query.filter(or_(Connection.user.is_(None), Connection.pwd.is_(None)))

            # Pagination
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 50)), 500)

            pagination = query.paginate(page=page, per_page=per_page, error_out=False)

            # Get user engagement data for this page
            user_id = g.user.id
            connection_ids = [conn.id for conn in pagination.items]
            engagement_map = get_user_engagement_map(user_id, connection_ids)

            # Don't include encrypted fields to save bandwidth, but include user engagement
            connections = [
                conn.to_dict(include_encrypted=False, user_engagement=engagement_map.get(conn.id))
                for conn in pagination.items
            ]

            return connections, 200

        except Exception as e:
            logging.error(f"Error fetching connections: {e}")
            return {"error": "Failed to fetch connections"}, 500


@connections_ns.route('/<int:connection_id>')
class ConnectionDetail(Resource):
    @auth_required
    @connections_ns.marshal_with(connection_model)
    @connections_ns.response(200, 'Success')
    @connections_ns.response(404, 'Connection not found')
    @connections_ns.response(500, 'Internal server error')
    def get(self, connection_id):
        """Get a specific connection by ID (no encrypted fields returned)"""
        try:
            connection = Connection.query.get(connection_id)

            if not connection:
                return {"error": "Connection not found"}, 404

            # Get user engagement data
            user_id = g.user.id
            engagement_map = get_user_engagement_map(user_id, [connection_id])

            # Don't include encrypted fields to save bandwidth
            return connection.to_dict(include_encrypted=False, user_engagement=engagement_map.get(connection_id)), 200

        except Exception as e:
            logging.error(f"Error fetching connection: {e}")
            return {"error": "Failed to fetch connection"}, 500


@connections_ns.route('/<int:connection_id>/decrypt')
class ConnectionDecrypt(Resource):
    @auth_required
    @connections_ns.marshal_with(decrypted_connection_model)
    @connections_ns.response(200, 'Success')
    @connections_ns.response(404, 'Connection not found')
    @connections_ns.response(500, 'Internal server error')
    def get(self, connection_id):
        """Get a connection with decrypted sensitive fields (authenticated users only)"""
        try:
            user_id = g.user.id
            decrypted_dict = None

            # Check if cache exists - if so, use it (fast path)
            if CACHE_KEY in decrypted_cache:
                all_decrypted = decrypted_cache[CACHE_KEY]
                decrypted_dict = next((conn.copy() for conn in all_decrypted if conn.get('id') == connection_id), None)
                if decrypted_dict:
                    logging.info(f"Returning connection {connection_id} from cache")

            # Cache doesn't exist - decrypt only this single connection (don't populate full cache)
            if not decrypted_dict:
                logging.info(f"Cache miss - decrypting single connection {connection_id}")
                connection = Connection.query.get(connection_id)

                if not connection:
                    return {"error": "Connection not found"}, 404

                # Get encrypted dict (without user engagement for now)
                connection_dict = connection.to_dict(include_encrypted=True)

                # Decrypt only this connection
                decrypted_dict = encryption_service.decrypt_connection(connection_dict)

            # Add user engagement data (whether from cache or freshly decrypted)
            engagement_map = get_user_engagement_map(user_id, [connection_id])
            user_engagement = engagement_map.get(connection_id)

            if user_engagement:
                decrypted_dict['user_rating'] = user_engagement.get('rating')
                decrypted_dict['user_usage_count'] = user_engagement.get('usage_count', 0)
                decrypted_dict['user_first_used_at'] = user_engagement.get('first_used_at')
                decrypted_dict['user_last_used_at'] = user_engagement.get('last_used_at')

            return decrypted_dict, 200

        except Exception as e:
            logging.error(f"Error decrypting connection: {e}")
            return {"error": "Failed to decrypt connection"}, 500


@connections_ns.route('/<int:connection_id>/rate')
class ConnectionRate(Resource):
    @auth_required
    @connections_ns.doc(params={
        'rating': 'Rating type: "up" for thumbs up, "down" for thumbs down'
    })
    @connections_ns.response(200, 'Success')
    @connections_ns.response(400, 'Invalid rating type')
    @connections_ns.response(404, 'Connection not found')
    @connections_ns.response(500, 'Internal server error')
    def post(self, connection_id):
        """Add or change a rating (thumbs up or down) to a connection"""
        try:
            rating = request.args.get('rating', '').lower()

            if rating not in ['up', 'down']:
                return {"error": "Invalid rating type. Must be 'up' or 'down'"}, 400

            connection = Connection.query.get(connection_id)

            if not connection:
                return {"error": "Connection not found"}, 404

            user_id = g.user.id

            # Get or create user engagement record
            engagement = ConnectionUserEngagement.query.filter_by(
                user_id=user_id,
                connection_id=connection_id
            ).first()

            if not engagement:
                # First time this user is rating this connection
                engagement = ConnectionUserEngagement(
                    user_id=user_id,
                    connection_id=connection_id,
                    rating=rating
                )
                db.session.add(engagement)

                # Increment global count
                if rating == 'up':
                    connection.rating_up += 1
                else:
                    connection.rating_down += 1

            else:
                # User already rated - check if they're changing their rating
                old_rating = engagement.rating

                if old_rating == rating:
                    # Same rating - no change needed
                    return {
                        "message": f"You already rated this '{rating}'",
                        "rating_up": connection.rating_up,
                        "rating_down": connection.rating_down,
                        "user_rating": rating
                    }, 200

                elif old_rating is None:
                    # User had no rating before, now adding one
                    engagement.rating = rating
                    if rating == 'up':
                        connection.rating_up += 1
                    else:
                        connection.rating_down += 1

                else:
                    # User is changing their rating (up -> down or down -> up)
                    # Decrement old rating count
                    if old_rating == 'up':
                        connection.rating_up -= 1
                    else:
                        connection.rating_down -= 1

                    # Increment new rating count
                    if rating == 'up':
                        connection.rating_up += 1
                    else:
                        connection.rating_down += 1

                    # Update user's rating
                    engagement.rating = rating

            db.session.commit()

            # Clear cache since data changed
            clear_decrypted_cache()

            return {
                "message": f"Rating '{rating}' recorded successfully",
                "rating_up": connection.rating_up,
                "rating_down": connection.rating_down,
                "user_rating": rating
            }, 200

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error recording rating: {e}")
            return {"error": "Failed to record rating"}, 500


@connections_ns.route('/<int:connection_id>/track-usage')
class ConnectionTrackUsage(Resource):
    @auth_required
    @connections_ns.response(200, 'Success')
    @connections_ns.response(404, 'Connection not found')
    @connections_ns.response(500, 'Internal server error')
    def post(self, connection_id):
        """Track usage (click/copy) of a connection"""
        try:
            connection = Connection.query.get(connection_id)

            if not connection:
                return {"error": "Connection not found"}, 404

            user_id = g.user.id
            now = datetime.now(timezone.utc)

            # Get or create user engagement record
            engagement = ConnectionUserEngagement.query.filter_by(
                user_id=user_id,
                connection_id=connection_id
            ).first()

            if not engagement:
                # First time this user is using this connection
                engagement = ConnectionUserEngagement(
                    user_id=user_id,
                    connection_id=connection_id,
                    usage_count=1,
                    first_used_at=now,
                    last_used_at=now
                )
                db.session.add(engagement)
            else:
                # User has used this before - increment count and update timestamp
                engagement.usage_count += 1
                engagement.last_used_at = now
                if not engagement.first_used_at:
                    engagement.first_used_at = now

            # Increment global usage count
            connection.usage_count += 1

            db.session.commit()

            # Clear cache since data changed
            clear_decrypted_cache()

            return {
                "message": "Usage tracked successfully",
                "usage_count": connection.usage_count,
                "user_usage_count": engagement.usage_count,
                "user_last_used": engagement.last_used_at.replace(tzinfo=timezone.utc).isoformat()
            }, 200

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error tracking usage: {e}")
            return {"error": "Failed to track usage"}, 500


@connections_ns.route('/search')
class ConnectionsAdvancedSearch(Resource):
    @auth_required
    @connections_ns.doc(params={
        'all': 'Return all matching results without pagination (true/false, default: false)',
        'short': 'Return only essential fields: id + encrypted fields (true/false, default: false)',
        'url_ids': 'Comma-separated list of url_ids to filter by (e.g., "id1,id2,id3"). Omit to search all.',
        'all_encrypted_fields': 'Search in ALL encrypted fields at once (server_ip, url, user, comments, comment_urls)',
        'search_ip': 'Search in decrypted server IPs (case-insensitive partial match)',
        'search_url': 'Search in decrypted URLs (case-insensitive partial match)',
        'search_user': 'Search in decrypted usernames (case-insensitive partial match)',
        'search_comments': 'Search in decrypted comments (case-insensitive partial match)',
        'company': 'Filter by company name (case-insensitive partial match)',
        'site': 'Filter by site name (case-insensitive partial match)',
        'application': 'Filter by application name (case-insensitive partial match)',
        'service': 'Filter by service type (exact match)',
        'page': 'Page number (default: 1)',
        'per_page': 'Items per page (default: 20, max: 100)'
    })
    @connections_ns.marshal_list_with(decrypted_connection_model)
    @connections_ns.response(200, 'Success')
    @connections_ns.response(500, 'Internal server error')
    def get(self):
        """
        Advanced search with decryption - search in encrypted fields

        WARNING: This endpoint decrypts all connections that match the filters,
        which is CPU and memory intensive. Use with pagination and filters.
        """
        try:
            # Check if 'all' parameter is set
            fetch_all = request.args.get('all', 'false').lower() == 'true'
            short_format = request.args.get('short', 'false').lower() == 'true'

            # Get search parameters for encrypted fields
            all_encrypted_fields = request.args.get('all_encrypted_fields', '').lower()
            search_ip = request.args.get('search_ip', '').lower()
            search_url = request.args.get('search_url', '').lower()
            search_user = request.args.get('search_user', '').lower()
            search_comments = request.args.get('search_comments', '').lower()

            # Standard filters (non-encrypted fields)
            url_ids_param = request.args.get('url_ids')
            company = request.args.get('company')
            site = request.args.get('site')
            application = request.args.get('application')
            service = request.args.get('service')

            # Pagination with smaller limits for this expensive operation (ignored if fetch_all=true)
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)

            # Get decrypted connections from cache or decrypt and cache them
            all_decrypted = get_all_decrypted_connections()

            # Filter decrypted connections based on non-encrypted field filters
            filtered_decrypted = all_decrypted

            # Apply non-encrypted filters on cached data
            if url_ids_param:
                url_ids_list = [url_id.strip() for url_id in url_ids_param.split(',') if url_id.strip()]
                if url_ids_list:
                    filtered_decrypted = [conn for conn in filtered_decrypted if conn.get('url_id') in url_ids_list]

            if company:
                filtered_decrypted = [conn for conn in filtered_decrypted if company.lower() in conn.get('company_name', '').lower()]

            if site:
                filtered_decrypted = [conn for conn in filtered_decrypted if site.lower() in conn.get('site_name', '').lower()]

            if application:
                filtered_decrypted = [conn for conn in filtered_decrypted if application.lower() in conn.get('application_name', '').lower()]

            if service:
                filtered_decrypted = [conn for conn in filtered_decrypted if conn.get('url_service') == service]

            # Filter by encrypted fields (data is already decrypted from cache)
            matching_connections = []

            for decrypted in filtered_decrypted:
                # Data is already decrypted from cache - just check if matches search criteria
                matches = True

                # Search across all encrypted fields at once
                if all_encrypted_fields:
                    field_match = False
                    # Search in server_ip
                    if decrypted.get('server_ip') and all_encrypted_fields in decrypted['server_ip'].lower():
                        field_match = True
                    # Search in url
                    if decrypted.get('url') and all_encrypted_fields in decrypted['url'].lower():
                        field_match = True
                    # Search in user
                    if decrypted.get('user') and all_encrypted_fields in decrypted['user'].lower():
                        field_match = True
                    # Search in comments
                    if decrypted.get('comments') and all_encrypted_fields in decrypted['comments'].lower():
                        field_match = True
                    # Search in comment_urls array
                    if decrypted.get('comment_urls') and isinstance(decrypted['comment_urls'], list):
                        for comment_url in decrypted['comment_urls']:
                            if comment_url and all_encrypted_fields in comment_url.lower():
                                field_match = True
                                break

                    if not field_match:
                        matches = False

                # Individual field searches (only if all_encrypted_fields not used)
                if not all_encrypted_fields:
                    if search_ip and decrypted.get('server_ip'):
                        if search_ip not in decrypted['server_ip'].lower():
                            matches = False

                    if search_url and decrypted.get('url'):
                        if search_url not in decrypted['url'].lower():
                            matches = False

                    if search_user and decrypted.get('user'):
                        if search_user not in decrypted['user'].lower():
                            matches = False

                    if search_comments and decrypted.get('comments'):
                        if search_comments not in decrypted['comments'].lower():
                            matches = False

                if matches:
                    matching_connections.append(decrypted)

            # Apply short format if requested (only id + encrypted fields)
            if short_format:
                short_results = []
                for conn in matching_connections:
                    short_results.append({
                        'id': conn.get('id'),
                        'url_id': conn.get('url_id'),
                        'comments': conn.get('comments'),
                        'comment_urls': conn.get('comment_urls'),
                        'server_ip': conn.get('server_ip'),
                        'url': conn.get('url'),
                        'user': conn.get('user'),
                        'pwd': conn.get('pwd'),
                    })
                matching_connections = short_results
            else:
                # Add user engagement data when not in short format
                user_id = g.user.id
                connection_ids = [conn.get('id') for conn in matching_connections]
                engagement_map = get_user_engagement_map(user_id, connection_ids)

                for conn in matching_connections:
                    conn_id = conn.get('id')
                    user_engagement = engagement_map.get(conn_id)
                    if user_engagement:
                        conn['user_rating'] = user_engagement.get('rating')
                        conn['user_usage_count'] = user_engagement.get('usage_count', 0)
                        conn['user_first_used_at'] = user_engagement.get('first_used_at')
                        conn['user_last_used_at'] = user_engagement.get('last_used_at')

            # Return all results or apply pagination
            if fetch_all:
                # Return all matching connections without pagination
                return matching_connections, 200
            else:
                # Apply pagination manually
                total_matches = len(matching_connections)
                start = (page - 1) * per_page
                end = start + per_page
                paginated_results = matching_connections[start:end]

                return paginated_results, 200

        except Exception as e:
            logging.error(f"Error in advanced search: {e}")
            import traceback
            traceback.print_exc()
            return {"error": "Failed to perform advanced search"}, 500


@connections_ns.route('/my-top-used')
class MyTopUsedConnections(Resource):
    @auth_required
    @connections_ns.doc(params={
        'limit': 'Number of results to return (default: 5, max: 20)'
    })
    @connections_ns.marshal_list_with(connection_model)
    @connections_ns.response(200, 'Success')
    @connections_ns.response(500, 'Internal server error')
    def get(self):
        """Get current user's top used connections"""
        try:
            user_id = g.user.id
            limit = min(int(request.args.get('limit', 5)), 20)

            # Get user's top used connections
            top_engagements = ConnectionUserEngagement.query.filter_by(user_id=user_id) \
                .filter(ConnectionUserEngagement.usage_count > 0) \
                .order_by(ConnectionUserEngagement.usage_count.desc()) \
                .limit(limit) \
                .all()

            # Get the connections
            connection_ids = [eng.connection_id for eng in top_engagements]
            connections = Connection.query.filter(Connection.id.in_(connection_ids)).all()

            # Create engagement map
            engagement_map = {eng.connection_id: {
                'rating': eng.rating,
                'usage_count': eng.usage_count,
                'first_used_at': eng.first_used_at.replace(tzinfo=timezone.utc).isoformat() if eng.first_used_at else None,
                'last_used_at': eng.last_used_at.replace(tzinfo=timezone.utc).isoformat() if eng.last_used_at else None,
            } for eng in top_engagements}

            # Sort connections by usage count
            connections_dict = {conn.id: conn for conn in connections}
            sorted_connections = [connections_dict[eng.connection_id] for eng in top_engagements if eng.connection_id in connections_dict]

            # Return with user engagement
            results = [
                conn.to_dict(include_encrypted=False, user_engagement=engagement_map.get(conn.id))
                for conn in sorted_connections
            ]

            return results, 200

        except Exception as e:
            logging.error(f"Error fetching top used connections: {e}")
            return {"error": "Failed to fetch top used connections"}, 500


@connections_ns.route('/my-recently-used')
class MyRecentlyUsedConnections(Resource):
    @auth_required
    @connections_ns.doc(params={
        'limit': 'Number of results to return (default: 5, max: 20)'
    })
    @connections_ns.marshal_list_with(connection_model)
    @connections_ns.response(200, 'Success')
    @connections_ns.response(500, 'Internal server error')
    def get(self):
        """Get current user's recently used connections"""
        try:
            user_id = g.user.id
            limit = min(int(request.args.get('limit', 5)), 20)

            # Get user's recently used connections
            recent_engagements = ConnectionUserEngagement.query.filter_by(user_id=user_id) \
                .filter(ConnectionUserEngagement.last_used_at.isnot(None)) \
                .order_by(ConnectionUserEngagement.last_used_at.desc()) \
                .limit(limit) \
                .all()

            # Get the connections
            connection_ids = [eng.connection_id for eng in recent_engagements]
            connections = Connection.query.filter(Connection.id.in_(connection_ids)).all()

            # Create engagement map
            engagement_map = {eng.connection_id: {
                'rating': eng.rating,
                'usage_count': eng.usage_count,
                'first_used_at': eng.first_used_at.replace(tzinfo=timezone.utc).isoformat() if eng.first_used_at else None,
                'last_used_at': eng.last_used_at.replace(tzinfo=timezone.utc).isoformat() if eng.last_used_at else None,
            } for eng in recent_engagements}

            # Sort connections by last used date
            connections_dict = {conn.id: conn for conn in connections}
            sorted_connections = [connections_dict[eng.connection_id] for eng in recent_engagements if eng.connection_id in connections_dict]

            # Return with user engagement
            results = [
                conn.to_dict(include_encrypted=False, user_engagement=engagement_map.get(conn.id))
                for conn in sorted_connections
            ]

            return results, 200

        except Exception as e:
            logging.error(f"Error fetching recently used connections: {e}")
            return {"error": "Failed to fetch recently used connections"}, 500


@connections_ns.route('/stats')
class ConnectionsStats(Resource):
    @auth_required
    @connections_ns.response(200, 'Success')
    @connections_ns.response(500, 'Internal server error')
    def get(self):
        """Get connection statistics (authenticated users only)"""
        try:
            total = Connection.query.count()
            companies = db.session.query(Connection.company_name).distinct().count()
            sites = db.session.query(Connection.site_name).distinct().count()
            applications = db.session.query(Connection.application_name).distinct().count()
            services = db.session.query(Connection.url_service).distinct().count()

            return {
                "total_connections": total,
                "unique_companies": companies,
                "unique_sites": sites,
                "unique_applications": applications,
                "unique_services": services
            }, 200

        except Exception as e:
            logging.error(f"Error generating connection stats: {e}")
            return {"error": "Failed to generate statistics"}, 500
