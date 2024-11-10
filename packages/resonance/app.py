#!/usr/bin/env nix-shell
#!nix-shell -i python3 tree jq mpv -p "python3.withPackages(ps: with ps; [ flask requests flask-caching ])"

import logging

from flask import Flask
from flask_caching import Cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure caching
cache = Cache(config={"CACHE_TYPE": "simple", "CACHE_DEFAULT_TIMEOUT": 300})
cache.init_app(app)

# Import routes after app initialization to avoid circular imports
from routes.api import api
from routes.web import web

# Register blueprints
app.register_blueprint(api)
app.register_blueprint(web)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
