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

3. **Initialize the database:**
   - Start the server once to create the database:
     ```bash
     python run.py
     ```
   - Run the initialization script to set up authentication:
     ```bash
     python init_app.py
     ```

## Development Server

```bash
python run.py
```

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