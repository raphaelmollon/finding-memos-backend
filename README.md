# Finding-Memo - Backend

### Compiles and hot-reloads for development
```bash
python run.py
```

### Setup with a Web Server Gateway Interface
> - Application startup file: **wsgi.py**
> - Application Entry point: **application**

#### Content of wsgi.py
```py
from run import app  # Import your Flask application

# Ensure the Flask app is exposed as "application"
application = app
```

### Initialization

1. Start the server using either options above.  
If the database doesn't exist yet, it will be automatically created

1. Run init_app `python init_app.py` to setup the authentication system for the first use.


### Update DB after Model's changes
```bash
flask db migrate -m "Description of changes"
flask db upgrade
```