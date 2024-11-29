import logging
from app.models.database import get_db_connection

def clean_unused_foreign_key_references(conn, table_to_check, foreign_key_to_check, value_to_check):

    if value_to_check is None:
        return
    
    # List of allowed table and foreign key names
    allowed_tables = ['memos']
    allowed_foreign_keys = {
        'category': 'categories',
        'type': 'types'
    }

    # Validate table and foreign key names
    if table_to_check not in allowed_tables:
        raise ValueError(f"Invalid table name: {table_to_check}")

    if foreign_key_to_check not in allowed_foreign_keys:
        raise ValueError(f"Invalid foreign key: {foreign_key_to_check}")

    foreign_table = allowed_foreign_keys[foreign_key_to_check]

    # Securely construct the SQL query
    sql_query = f'''
        SELECT COUNT(*) FROM {table_to_check}
        WHERE {foreign_key_to_check}_id = ?
    '''

    ret = conn.execute(sql_query, (value_to_check,)).fetchone()[0]

    if ret == 0:
        # Delete the entry in the foreign key table
        delete_query = f'DELETE FROM {foreign_table} WHERE id = ?'
        conn.execute(delete_query, (value_to_check,))
        logging.debug(f"No more {table_to_check} with {foreign_key_to_check} <{value_to_check}> ==> DELETED")

def get_or_create_id_by_name(conn, table_name, name):
    if name is None or name == '':
        return None

    # Validate table name to prevent SQL injection
    allowed_tables = ['categories', 'types']
    if table_name not in allowed_tables:
        raise ValueError(f"Invalid table name: {table_name}")

    # Check if the entry exists
    query = f'SELECT id FROM {table_name} WHERE name = ?'
    result = conn.execute(query, (name,)).fetchone()
    if result:
        return result['id']
    else:
        # Insert new entry
        cursor = conn.execute(f'INSERT INTO {table_name} (name) VALUES (?)', (name,))
        return cursor.lastrowid

def get_user_by_id(id):
    if id is None or id == '':
        return None
    
    with get_db_connection() as conn:
        user = conn.execute("select id, email, is_superuser from users where id = ?", (id,)).fetchone()
        return user

