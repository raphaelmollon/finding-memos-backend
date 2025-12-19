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