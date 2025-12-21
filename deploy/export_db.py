"""
Database Export Script
======================
Exports the MariaDB database to SQL file for backup or deployment.

Usage:
    python deploy/export_db.py [output_file]

Examples:
    python deploy/export_db.py                     # Exports to db_backup_YYYYMMDD_HHMMSS.sql
    python deploy/export_db.py production_backup.sql
"""

import os
import subprocess
import sys
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
    parsed = urlparse(uri)
    return {
        'user': parsed.username,
        'password': parsed.password,
        'host': parsed.hostname,
        'port': parsed.port or 3306,
        'database': parsed.path.lstrip('/')
    }

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
    output_file = sys.argv[1] if len(sys.argv) > 1 else None
    export_database(output_file)
