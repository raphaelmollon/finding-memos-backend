"""
Database Export Script (Pure Python)
=====================================
Exports the MariaDB database using pure Python (no mysqldump required).

This script connects directly to the database and exports table structures
and data as SQL statements.

Usage:
    python deploy/export_db_python.py [output_file]

Examples:
    python deploy/export_db_python.py                     # Exports to db_backup_YYYYMMDD_HHMMSS.sql
    python deploy/export_db_python.py production_backup.sql
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

def export_database_python(output_file=None):
    """Export database using pure Python (no mysqldump needed)."""
    try:
        # Import Flask app and database
        from app import create_app
        from app.database import db

        app = create_app()

        # Generate output filename if not provided
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"db_backup_{timestamp}.sql"

        print(f"Exporting database to '{output_file}'...")

        with app.app_context():
            # Get database connection
            engine = db.engine
            connection = engine.raw_connection()
            cursor = connection.cursor()

            with open(output_file, 'w', encoding='utf-8') as f:
                # Write header
                f.write("-- MariaDB Database Export\n")
                f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-- \n\n")
                f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

                # Get all tables
                cursor.execute("SHOW TABLES")
                tables = [row[0] for row in cursor.fetchall()]

                print(f"Found {len(tables)} tables to export")

                for table in tables:
                    print(f"  Exporting table: {table}")

                    # Drop table statement
                    f.write(f"-- Table: {table}\n")
                    f.write(f"DROP TABLE IF EXISTS `{table}`;\n")

                    # Create table statement
                    cursor.execute(f"SHOW CREATE TABLE `{table}`")
                    create_table = cursor.fetchone()[1]
                    f.write(f"{create_table};\n\n")

                    # Get table data
                    cursor.execute(f"SELECT * FROM `{table}`")
                    rows = cursor.fetchall()

                    if rows:
                        # Get column names
                        cursor.execute(f"DESCRIBE `{table}`")
                        columns = [col[0] for col in cursor.fetchall()]
                        columns_str = ', '.join([f"`{col}`" for col in columns])

                        # Write insert statements
                        f.write(f"-- Data for table: {table}\n")
                        f.write(f"INSERT INTO `{table}` ({columns_str}) VALUES\n")

                        for i, row in enumerate(rows):
                            # Escape and format values
                            values = []
                            for val in row:
                                if val is None:
                                    values.append('NULL')
                                elif isinstance(val, (int, float)):
                                    values.append(str(val))
                                elif isinstance(val, bytes):
                                    # Handle binary data
                                    values.append(f"0x{val.hex()}")
                                else:
                                    # Escape strings
                                    escaped = str(val).replace('\\', '\\\\').replace("'", "\\'")
                                    values.append(f"'{escaped}'")

                            values_str = ', '.join(values)

                            if i < len(rows) - 1:
                                f.write(f"({values_str}),\n")
                            else:
                                f.write(f"({values_str});\n")

                        f.write("\n")

                f.write("SET FOREIGN_KEY_CHECKS=1;\n")

            cursor.close()
            connection.close()

        file_size = os.path.getsize(output_file) / 1024  # KB
        print(f"\n[OK] Database exported successfully to '{output_file}'")
        print(f"  File size: {file_size:.2f} KB")
        print(f"  Tables exported: {len(tables)}")

        return output_file

    except Exception as e:
        print(f"[ERROR] Export failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    output_file = sys.argv[1] if len(sys.argv) > 1 else None
    export_database_python(output_file)
