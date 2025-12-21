"""
Database Import Script
======================
Imports SQL file into MariaDB database.

Usage:
    python deploy/import_db_from_sql.py <sql_file> [--yes]

Options:
    --yes, -y    Skip confirmation prompt

Examples:
    python deploy/import_db_from_sql.py db_backup_20231215_120000.sql
    python deploy/import_db_from_sql.py production_backup.sql --yes

WARNING: This will import data into the database specified in your .env file.
         Make sure you're targeting the correct database!
"""

import os
import subprocess
import sys
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

def parse_db_uri(uri):
    """Parse database URI and extract connection parameters."""
    # Handle URLs with special characters in password
    # Format: mysql+pymysql://user:password@host:port/database
    try:
        # Try standard parsing first
        parsed = urlparse(uri)
        return {
            'user': parsed.username,
            'password': parsed.password,
            'host': parsed.hostname,
            'port': parsed.port or 3306,
            'database': parsed.path.lstrip('/')
        }
    except ValueError:
        # If standard parsing fails, try manual parsing
        # Remove protocol prefix
        if '://' in uri:
            uri = uri.split('://', 1)[1]

        # Split into credentials and location
        if '@' in uri:
            # Find the last @ which separates credentials from host
            credentials, location = uri.rsplit('@', 1)

            # Parse credentials
            if ':' in credentials:
                user, password = credentials.split(':', 1)
            else:
                user = credentials
                password = ''

            # Parse location (host:port/database)
            if '/' in location:
                host_port, database = location.split('/', 1)
            else:
                host_port = location
                database = ''

            # Parse host and port
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

def import_database(sql_file, skip_confirmation=False):
    """Import SQL file into database using mysql client."""
    if not os.path.exists(sql_file):
        print(f"Error: File '{sql_file}' not found")
        sys.exit(1)

    # Get database URI from environment
    db_uri = os.getenv('SQLALCHEMY_DATABASE_URI')
    if not db_uri:
        print("Error: SQLALCHEMY_DATABASE_URI not set in .env file")
        sys.exit(1)

    # Parse connection parameters
    db_params = parse_db_uri(db_uri)

    # Confirm import (unless skipped)
    print(f"⚠️  WARNING: This will import data into database '{db_params['database']}'")
    print(f"   Host: {db_params['host']}:{db_params['port']}")
    print(f"   File: {sql_file}")

    if not skip_confirmation:
        response = input("\nContinue? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Import cancelled")
            sys.exit(0)
    else:
        print("   [Auto-confirmed with --yes flag]")

    # Try mariadb client first, fallback to mysql
    client_cmd = None
    for cmd_name in ['mariadb', 'mysql']:
        try:
            subprocess.run([cmd_name, '--version'],
                         capture_output=True,
                         check=False)
            client_cmd = cmd_name
            break
        except FileNotFoundError:
            continue

    if not client_cmd:
        print("✗ Error: Neither mariadb nor mysql client found.")
        print("  Please ensure MySQL/MariaDB client is installed.")
        sys.exit(1)

    # Build command
    cmd = [
        client_cmd,
        f'--host={db_params["host"]}',
        f'--port={db_params["port"]}',
        f'--user={db_params["user"]}',
        f'--password={db_params["password"]}',
        db_params['database']
    ]

    print(f"\nImporting '{sql_file}' into database '{db_params['database']}' using {client_cmd}...")

    try:
        # Run mysql/mariadb and pipe SQL file into it
        with open(sql_file, 'r', encoding='utf-8') as f:
            result = subprocess.run(
                cmd,
                stdin=f,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True
            )

        if result.returncode == 0:
            print(f"✓ Database imported successfully from '{sql_file}'")
        else:
            print(f"✗ Import failed:")
            print(f"  {result.stderr}")
            sys.exit(1)

    except Exception as e:
        print(f"✗ Import failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Import SQL file into MariaDB database',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('sql_file', help='SQL file to import')
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt'
    )

    args = parser.parse_args()

    import_database(args.sql_file, skip_confirmation=args.yes)
