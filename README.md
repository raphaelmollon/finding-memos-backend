# Finding-Memo - Backend

## Initial Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and fill in your configuration:
     - `SECRET_KEY` - Generate a secure random key for sessions
     - Email server credentials (`MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD`, etc.)
     - Frontend URLs for development and production
     - Database connection (see step 3)

3. **Set up MariaDB database:**
   - Create database and user in MariaDB:
     ```bash
     mysql -u root -p
     ```
     ```sql
     CREATE DATABASE finding_memo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
     CREATE USER 'YOUR_USER'@'YOUR_SERVER' IDENTIFIED BY 'YOUR_SECURE_PASSWORD';
     GRANT ALL PRIVILEGES ON finding_memo.* TO 'YOUR_USER'@'localhost';
     FLUSH PRIVILEGES;
     EXIT;
     ```
   - Update `.env` with your MariaDB connection string:
     ```
     SQLALCHEMY_DATABASE_URI=mysql+pymysql://YOUR_USER:YOUR_PASSWORD@YOUR_SERVER:3306/finding_memo
     ```

4. **Initialize the database:**
   - Run migrations to create tables:
     ```bash
     flask db upgrade
     ```

5. **Create first superuser (fresh installation only):**
   - If migrating from SQLite, skip this step (run `migrate_data.py` instead)
   - For fresh installations, create superuser via Flask shell:
     ```bash
     flask shell
     ```
     ```python
     from app.models import User, Config
     from app.database import db
     from werkzeug.security import generate_password_hash
     import json

     # Create superuser
     superuser = User(
         email='admin@example.com',
         password_hash=generate_password_hash('your_password'),
         is_superuser=True,
         status='VALID'
     )
     db.session.add(superuser)

     # Create config
     config = Config(
         id=1,
         enable_auth=True,
         allowed_domains=json.dumps(['example.com'])
     )
     db.session.add(config)

     db.session.commit()
     exit()
     ```

## Run Development Server

```bash
python run.py
```

## Testing

A dedicated README is available in ./tests/ 



## Setup with a Web Server Gateway Interface (Production)
> - Application startup file: **wsgi.py**
> - Application Entry point: **application**

#### Content of wsgi.py
```py
from run import app  # Import your Flask application

# Ensure the Flask app is exposed as "application"
application = app
```

#### Production Environment Variables
Set `FLASK_ENV=production` and ensure all required variables in `.env` are configured.


### Update DB after Model's changes
```bash
flask db migrate -m "Description of changes"
flask db upgrade
```

### Update requirements after new deploy
```bash
pipreqs
```
Then in the python app setup on the hosting server:
Run PIP install requirements.txt (after deploying the package including this file)


## Deployment

All deployment tools are in the `deploy/` folder. See [deploy/README_DEPLOYMENT.md](deploy/README_DEPLOYMENT.md) for complete documentation.

### Quick Deploy (Automated Package)

Create a clean deployment package with one command:

```bash
# Code only (use migrations on server)
python deploy/deploy.py

# Include database export
python deploy/deploy.py --with-data

# Custom filename
python deploy/deploy.py --output production_v2.zip --with-data
```

This creates a ZIP file containing only production-ready files (excludes tests, cache, logs, etc.).

**What gets included:**
- All Python code (`app/`, `migrations/`)
- Configuration files (`requirements.txt`, `.env.example`)
- Deployment scripts (`deploy/` folder)
- Documentation
- Database export (if `--with-data` flag used)

**What gets excluded:**
- Tests, cache files, logs
- `.env` file (configure separately on server)
- Development files (`.git`, `.pytest_cache`, etc.)
- Old SQLite databases and backups

The script shows deployment instructions after creating the package.

---

## Database Backup & Deployment

### Exporting Database
Export your database to SQL file for backup or deployment:
```bash
# Export with auto-generated filename (db_backup_YYYYMMDD_HHMMSS.sql)
python deploy/export_db.py

# Export to specific file
python deploy/export_db.py production_backup.sql
```

### Importing Database
Import SQL file into database:
```bash
# With confirmation prompt
python deploy/import_db_from_sql.py db_backup_20231215_120000.sql

# Skip confirmation (useful for automated tools/scripts)
python deploy/import_db_from_sql.py db_backup_20231215_120000.sql --yes
```

### Deployment Workflows

#### Option 1: Deploy with Data (Full Backup)
When you want to copy everything including data:
1. Export database locally: `python deploy/export_db.py production_deploy.sql`
2. Deploy code + SQL file to server
3. On server: `python deploy/import_db_from_sql.py production_deploy.sql --yes`

#### Option 2: Deploy Schema Only (Migrations)
When you only need table structures without data:
1. Ensure migrations are created: `flask db migrate -m "description"`
2. Deploy code (including migrations folder) to server
3. On server: `flask db upgrade`
4. Manually create superuser if needed (see step 5 in Initial Setup)

#### Option 3: Update Schema on Existing Database
When you need to update table structures on deployed database:
1. Locally: `flask db migrate -m "add new column"`
2. Deploy code (including new migration files)
3. On server: `flask db upgrade`

### Notes
- Export/import scripts require `mysql` or `mysqldump` client installed
- Always backup before importing or running migrations in production
- Exports include data, schema, triggers, and stored procedures
- See `deploy/` folder for complete deployment documentation