"""
Database Export Script
======================
Exports the MariaDB database to SQL or JSON file for backup or deployment.

Usage:
    python deploy/export_db.py [output_file] [--to-json]

Options:
    --to-json    Export to JSON format instead of SQL

Examples:
    python deploy/export_db.py                     # Exports to db_backup_YYYYMMDD_HHMMSS.sql
    python deploy/export_db.py production_backup.sql
    python deploy/export_db.py backup.json --to-json
"""

import os
import subprocess
import sys
import json
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# Fix encoding for Windows console (only for print operations)
def safe_print(msg):
    """Print with proper encoding handling for Windows."""
    try:
        print(msg)
    except UnicodeEncodeError:
        # Fallback for Windows console encoding issues
        print(msg.encode('ascii', 'replace').decode('ascii'))

def parse_db_uri(uri):
    """Parse database URI and extract connection parameters."""
    # Handle URLs with special characters in password
    try:
        parsed = urlparse(uri)
        return {
            'user': parsed.username,
            'password': parsed.password,
            'host': parsed.hostname,
            'port': parsed.port or 3306,
            'database': parsed.path.lstrip('/')
        }
    except ValueError:
        # Manual parsing for special characters
        if '://' in uri:
            uri = uri.split('://', 1)[1]

        if '@' in uri:
            credentials, location = uri.rsplit('@', 1)
            if ':' in credentials:
                user, password = credentials.split(':', 1)
            else:
                user = credentials
                password = ''

            if '/' in location:
                host_port, database = location.split('/', 1)
            else:
                host_port = location
                database = ''

            if ':' in host_port:
                host, port = host_port.rsplit(':', 1)
                port = int(port)
            else:
                host = host_port
                port = 3306

            return {
                'user': user,
                'password': password,
                'host': host,
                'port': port,
                'database': database
            }
        else:
            raise ValueError(f"Invalid database URI format: {uri}")


def export_to_json(output_file=None):
    """Export database to JSON file using Python."""
    # Get database URI from environment
    db_uri = os.getenv('SQLALCHEMY_DATABASE_URI')
    if not db_uri:
        safe_print("Error: SQLALCHEMY_DATABASE_URI not set in .env file")
        sys.exit(1)

    # Parse connection parameters
    db_params = parse_db_uri(db_uri)

    # Generate output filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"db_backup_{timestamp}.json"

    safe_print(f"Exporting database '{db_params['database']}' to '{output_file}' (JSON format)...")

    try:
        import pymysql

        # Connect to database
        connection = pymysql.connect(
            host=db_params['host'],
            port=db_params['port'],
            user=db_params['user'],
            password=db_params['password'],
            database=db_params['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        export_data = {
            'export_date': datetime.now().isoformat(),
            'database': db_params['database'],
            'tables': {}
        }

        with connection.cursor() as cursor:
            # Get all tables
            cursor.execute("SHOW TABLES")
            tables = [row[f"Tables_in_{db_params['database']}"] for row in cursor.fetchall()]

            # Export each table
            for table in tables:
                safe_print(f"  Exporting table: {table}")
                cursor.execute(f"SELECT * FROM `{table}`")
                rows = cursor.fetchall()

                # Convert datetime objects to strings
                serialized_rows = []
                for row in rows:
                    serialized_row = {}
                    for key, value in row.items():
                        if isinstance(value, datetime):
                            serialized_row[key] = value.isoformat()
                        elif isinstance(value, bytes):
                            serialized_row[key] = value.decode('utf-8', errors='replace')
                        else:
                            serialized_row[key] = value
                    serialized_rows.append(serialized_row)

                export_data['tables'][table] = serialized_rows

        connection.close()

        # Write to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        safe_print(f"[OK] Database exported successfully to '{output_file}'")
        file_size = os.path.getsize(output_file) / 1024  # KB
        safe_print(f"  File size: {file_size:.2f} KB")
        safe_print(f"  Tables exported: {len(export_data['tables'])}")

        return output_file

    except ImportError:
        safe_print("Error: pymysql module not installed")
        safe_print("  Install it with: pip install pymysql")
        sys.exit(1)
    except Exception as e:
        safe_print(f"[ERROR] Export failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def export_database(output_file=None):
    """Export database to SQL file using mariadb-dump or mysqldump."""
    # Get database URI from environment
    db_uri = os.getenv('SQLALCHEMY_DATABASE_URI')
    if not db_uri:
        safe_print("Error: SQLALCHEMY_DATABASE_URI not set in .env file")
        sys.exit(1)

    # Parse connection parameters
    db_params = parse_db_uri(db_uri)

    # Generate output filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"db_backup_{timestamp}.sql"

    # Try mariadb-dump first (newer), fallback to mysqldump
    dump_cmd = None
    for cmd_name in ['mariadb-dump', 'mysqldump']:
        try:
            # Test if command exists
            subprocess.run([cmd_name, '--version'],
                         capture_output=True,
                         check=False)
            dump_cmd = cmd_name
            break
        except FileNotFoundError:
            continue

    if not dump_cmd:
        safe_print("WARNING: Neither mariadb-dump nor mysqldump found. Trying Python-based export instead...")
        # Fallback to Python-based export
        try:
            from pathlib import Path
            script_dir = Path(__file__).parent
            sys.path.insert(0, str(script_dir))
            from export_db_python import export_database_python
            return export_database_python(output_file)
        except Exception as fallback_error:
            safe_print(f"\nERROR: Python-based export also failed: {fallback_error}")
            safe_print("\nPlease either:")
            safe_print("  1. Install MariaDB client tools (includes mariadb-dump)")
            safe_print("  2. Or install MySQL client (includes mysqldump)")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    # Build dump command
    cmd = [
        dump_cmd,
        f'--host={db_params["host"]}',
        f'--port={db_params["port"]}',
        f'--user={db_params["user"]}',
        f'--password={db_params["password"]}',
        '--single-transaction',  # Consistent backup
        '--routines',            # Include stored procedures
        '--triggers',            # Include triggers
        '--events',              # Include events
        db_params['database']
    ]

    safe_print(f"Exporting database '{db_params['database']}' to '{output_file}' using {dump_cmd}...")

    try:
        # Run dump command and write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True
            )

        if result.returncode == 0:
            safe_print(f"[OK] Database exported successfully to '{output_file}'")
            file_size = os.path.getsize(output_file) / 1024  # KB
            safe_print(f"  File size: {file_size:.2f} KB")
            return output_file
        else:
            safe_print(f"[ERROR] Export failed: {result.stderr}")
            sys.exit(1)

    except Exception as e:
        safe_print(f"[ERROR] Export failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Export MariaDB database to SQL or JSON file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deploy/export_db.py                           # Export to SQL (auto-generated name)
  python deploy/export_db.py backup.sql                # Export to SQL (custom name)
  python deploy/export_db.py backup.json --to-json     # Export to JSON
  python deploy/export_db.py --to-json                 # Export to JSON (auto-generated name)
        """
    )

    parser.add_argument(
        'output_file',
        nargs='?',
        help='Output filename (default: db_backup_YYYYMMDD_HHMMSS.sql or .json)'
    )

    parser.add_argument(
        '--to-json',
        action='store_true',
        help='Export to JSON format instead of SQL'
    )

    args = parser.parse_args()

    if args.to_json:
        export_to_json(args.output_file)
    else:
        export_database(args.output_file)
