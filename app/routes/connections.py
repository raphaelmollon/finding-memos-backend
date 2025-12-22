import os
import json
import logging
import zipfile
import shutil
from datetime import datetime, timezone
from flask import request, g
from flask_restx import Namespace, Resource, fields
from sqlalchemy import or_, and_

from app.database import db
from app.models import Connection, Config
from app.middleware import auth_required
from app.services.encryption_service import encryption_service

connections_ns = Namespace('connections', description='Connections management operations')

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
    'has_credentials': fields.Boolean(description='Whether this connection has credentials'),
    'has_url': fields.Boolean(description='Whether this connection has a URL'),
    'created_at': fields.DateTime(description='Created at'),
    'updated_at': fields.DateTime(description='Updated at'),
})

# Decrypted connection model (includes decrypted sensitive fields)
decrypted_connection_model = connections_ns.clone('DecryptedConnection', connection_model, {
    'comments': fields.String(description='Decrypted comments'),
    'comment_urls': fields.List(fields.String, description='Decrypted comment URLs'),
    'server_ip': fields.String(description='Decrypted server IP'),
    'url_type': fields.String(description='Decrypted URL type'),
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
                                            url_type=url_data.get('url_type'),
                                            url=url_data.get('url'),
                                            user=url_data.get('user'),
                                            pwd=url_data.get('pwd'),
                                        )
                                        db.session.add(connection)
                                        imported_count += 1

            # Commit all changes
            db.session.commit()

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

            # Don't include encrypted fields to save bandwidth
            connections = [conn.to_dict(include_encrypted=False) for conn in pagination.items]

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

            # Don't include encrypted fields to save bandwidth
            return connection.to_dict(include_encrypted=False), 200

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
            connection = Connection.query.get(connection_id)

            if not connection:
                return {"error": "Connection not found"}, 404

            # Get encrypted dict
            connection_dict = connection.to_dict(include_encrypted=True)

            # Decrypt all fields
            decrypted_dict = encryption_service.decrypt_connection(connection_dict)

            return decrypted_dict, 200

        except Exception as e:
            logging.error(f"Error decrypting connection: {e}")
            return {"error": "Failed to decrypt connection"}, 500


@connections_ns.route('/search')
class ConnectionsAdvancedSearch(Resource):
    @auth_required
    @connections_ns.doc(params={
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
            # Get search parameters for encrypted fields
            search_ip = request.args.get('search_ip', '').lower()
            search_url = request.args.get('search_url', '').lower()
            search_user = request.args.get('search_user', '').lower()
            search_comments = request.args.get('search_comments', '').lower()

            # Standard filters (non-encrypted fields)
            company = request.args.get('company')
            site = request.args.get('site')
            application = request.args.get('application')
            service = request.args.get('service')

            # Pagination with smaller limits for this expensive operation
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)

            # Start with base query and apply non-encrypted filters first
            query = Connection.query

            if company:
                query = query.filter(Connection.company_name.ilike(f'%{company}%'))
            if site:
                query = query.filter(Connection.site_name.ilike(f'%{site}%'))
            if application:
                query = query.filter(Connection.application_name.ilike(f'%{application}%'))
            if service:
                query = query.filter(Connection.url_service == service)

            # Get all matching connections (we need to decrypt them all to search)
            # This is expensive but necessary for encrypted field search
            all_connections = query.all()

            # Filter by encrypted fields (requires decryption)
            matching_connections = []

            for conn in all_connections:
                # Get encrypted dict
                conn_dict = conn.to_dict(include_encrypted=True)

                # Decrypt
                decrypted = encryption_service.decrypt_connection(conn_dict)

                # Check if matches search criteria
                matches = True

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
