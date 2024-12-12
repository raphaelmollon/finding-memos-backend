import sqlite3
from app.config import DATABASE_FILE
import logging

# Function to connect to the database
def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Create the tables and indexes, used once
def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_superuser BOOLEAN DEFAULT FALSE,
                preferences TEXT DEFAULT '\{\}',
                settings TEXT DEFAULT '\{\}'
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY,
                enable_auth BOOLEAN DEFAULT TRUE,
                allowed_domains TEXT DEFAULT '["example.com"]'
            );
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS memos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                content TEXT NOT NULL,
                category_id INTEGER,
                type_id INTEGER,
                FOREIGN KEY (category_id) REFERENCES categories (id),
                FOREIGN KEY (type_id) REFERENCES types (id)
            )
        ''')

        # Add indexes on frequently used columns
        conn.execute('CREATE INDEX IF NOT EXISTS idx_memos_name ON memos (name)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_memos_category ON memos (category_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_memos_type ON memos (type_id)')
    
    logging.info("Database initialized.")
