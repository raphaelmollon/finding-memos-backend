###### START INIT LOGGING
import os
import logging
import json
from logging.config import dictConfig

if not os.path.exists("./log") or not os.path.isdir("./log"):
    os.mkdir("./log")

logging_config_file = "app/logging_config.json"
logging_config_data = None
try:
    with open(logging_config_file, "r") as file:
        logging_config_data = json.load(file)

    dictConfig(logging_config_data)
except:
    logging.error(f"The config file {logging_config_file} couldn't be found. Exiting...")
    quit()
###### END INIT LOGGING


logging.info("Starting server...")

from app import create_app
app = create_app()

if __name__ == "__main__":
    is_production = os.environ.get('FLASK_ENV') == 'production'
    if is_production:
        app.run(debug=False)
    else:
        app.run(
            debug=True, 
            use_reloader=True,
            host="localhost"
            )
