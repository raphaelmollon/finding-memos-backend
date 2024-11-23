import os
import sqlite3
import json
from getpass import getpass
from werkzeug.security import generate_password_hash

# Database connection function
def get_db_connection():
    if not os.path.exists('memos.db'):
        print("Error: Database file 'memos.db' does not exist. Please ensure the server has initialized the database.")
        exit(1)
    conn = sqlite3.connect('memos.db')
    conn.row_factory = sqlite3.Row
    return conn

# Check if a table exists in the database
def table_exists(conn, table_name):
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
    result = conn.execute(query, (table_name,)).fetchone()
    return result is not None

# Check if at least one superuser exists
def superuser_exists(conn):
    query = "SELECT id FROM users WHERE is_superuser = 1 LIMIT 1"
    result = conn.execute(query).fetchone()
    return result is not None

# Initialize the config table
def initialize_config(conn):
    print("\n--- Configure Application Settings ---")
    
    enable_auth = input("Enable authentication? (yes/no): ").strip().lower() == "yes"
    allowed_domains_input = input(
        "Enter allowed email domains (comma-separated, e.g., example.com,company.org): "
    ).strip()
    allowed_domains = [domain.strip() for domain in allowed_domains_input.split(",") if domain.strip()]

    conn.execute('DELETE FROM config')  # Ensure there's only one config entry
    conn.execute(
        '''
        INSERT INTO config (id, enable_auth, allowed_domains)
        VALUES (1, ?, ?)
        ''',
        (enable_auth, json.dumps(allowed_domains))
    )
    conn.commit()
    print("Configuration saved.")

# Initialize the superuser
def initialize_superuser(conn):
    print("\n--- Create Superuser ---")
    
    while True:
        email = input("Enter superuser email: ").strip()
        if "@" not in email or "." not in email:
            print("Invalid email address. Please try again.")
            continue
        
        existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing_user:
            print("This email is already registered as a user. Please try another.")
            continue
        
        break

    while True:
        password = getpass("Enter superuser password: ")
        confirm_password = getpass("Confirm superuser password: ")
        if password != confirm_password:
            print("Passwords do not match. Please try again.")
        elif len(password) < 6:
            print("Password must be at least 6 characters long. Please try again.")
        else:
            break

    password_hash = generate_password_hash(password)
    conn.execute(
        '''
        INSERT INTO users (email, password_hash, is_superuser)
        VALUES (?, ?, ?)
        ''',
        (email, password_hash, True)
    )
    conn.commit()
    print(f"Superuser {email} created successfully.")

def main():
    print("Welcome to the Finding Memos Initialization Script!")
    with get_db_connection() as conn:
        # Verify required tables exist
        if not table_exists(conn, 'users') or not table_exists(conn, 'config'):
            print("Error: Required tables do not exist in the database. Ensure the server has initialized the database.")
            exit(1)
        
        # Check if a superuser already exists
        if superuser_exists(conn):
            print("Error: A superuser already exists. Use the application UI to manage settings or create additional users.")
            exit(1)
        
        # Initialize configuration and superuser
        initialize_config(conn)
        initialize_superuser(conn)

if __name__ == "__main__":
    main()
