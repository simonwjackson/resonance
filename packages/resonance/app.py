#!/usr/bin/env nix-shell
#!nix-shell -i python3 tree jq mpv -p "python3.withPackages(ps: with ps; [ flask requests flask-caching ])"

import glob
import json
import logging
import mimetypes
import os
import subprocess
from functools import wraps
from typing import Any, Dict, List, Optional, Union

from flask import (
    Blueprint,
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_caching import Cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure caching
cache = Cache(config={"CACHE_TYPE": "simple", "CACHE_DEFAULT_TIMEOUT": 300})
cache.init_app(app)

# Create blueprints for API and Web routes
api = Blueprint("api", __name__, url_prefix="/api")
web = Blueprint("web", __name__)


# Existing utility functions
def parse_jsonl_output(output: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Parse JSONL output from deadwax command"""
    try:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            raise ValueError("Empty output from deadwax command")
        results = [json.loads(line) for line in lines]
        return results[0] if len(results) == 1 else results
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.error(f"Problematic output: {output}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing JSONL: {str(e)}")
        raise


def run_deadwax_command(
    command: str, target: str, recommend: Optional[str] = None
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Run a deadwax command and return the parsed JSONL result"""
    try:
        cmd = ["deadwax"]
        if command.startswith("show"):
            resource_type = command.split("/")[1]
            cmd.extend(["show", resource_type])
            if recommend:
                cmd.extend(["--recommend", recommend])
            cmd.append(target)
        else:  # search
            resource_type = command.split("/")[1]
            cmd.extend(["search", resource_type, target])

        logger.info(f"Executing command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return parse_jsonl_output(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise


# Decorators
def validate_resource_type(func):
    """Decorator to validate resource type in URL"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        valid_types = {"artist", "album", "playlist", "song"}
        if "type" in kwargs and kwargs["type"] not in valid_types:
            abort(
                400,
                description=f"Invalid resource type. Must be one of: {', '.join(valid_types)}",
            )
        return func(*args, **kwargs)

    return wrapper


def validate_search_type(func):
    """Decorator to validate search type in URL"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        valid_types = {"artist", "album", "playlist", "song", "all"}
        if "type" in kwargs and kwargs["type"] not in valid_types:
            abort(
                400,
                description=f"Invalid search type. Must be one of: {', '.join(valid_types)}",
            )
        return func(*args, **kwargs)

    return wrapper


# Error handlers
@app.errorhandler(400)
def bad_request(error):
    if request.headers.get("HX-Request"):
        return render_template("errors/400.html", error=error.description), 400
    return jsonify(error=str(error.description)), 400


@app.errorhandler(404)
def not_found(error):
    if request.headers.get("HX-Request"):
        return render_template("errors/404.html", error=error.description), 404
    return jsonify(error=str(error.description)), 404


@app.errorhandler(500)
def server_error(error):
    if request.headers.get("HX-Request"):
        return render_template("errors/500.html", error="Internal server error"), 500
    return jsonify(error="Internal server error"), 500


# API Routes
@api.route("/show/<type>/<id>")
@validate_resource_type
@cache.memoize(timeout=300)
def show_resource(type: str, id: str):
    """Handle show requests for specific resources"""
    recommend = request.args.get("recommend")
    try:
        result = run_deadwax_command(f"show/{type}", id, recommend)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing show request: {str(e)}")
        abort(500)


@api.route("/search/<type>/<query>")
@validate_search_type
@cache.memoize(timeout=300)
def search_resource(type: str, query: str):
    """Handle search requests"""
    try:
        result = run_deadwax_command(f"search/{type}", query)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing search request: {str(e)}")
        abort(500)


# Web Routes with HTMX
@web.route("/")
def index():
    """Main page with search interface"""
    return render_template("index.html")


@web.route("/search")
def search():
    query = request.args.get("q", "")
    search_type = request.args.get("type", "all")
    sort = request.args.get("sort", "relevance")

    results = []
    selected_item = None

    if query:
        try:
            results = run_deadwax_command(f"search/{search_type}", query)
            # Apply sorting if needed
            if sort == "name":
                results.sort(key=lambda x: x.get("name", ""))
            elif sort == "date":
                results.sort(key=lambda x: x.get("year", 0), reverse=True)
        except Exception as e:
            logger.error(f"Search error: {str(e)}")

    if request.headers.get("HX-Request"):
        return render_template("partials/search_results.html", results=results)

    return render_template("search.html", results=results, selected_item=selected_item)


@web.route("/<type>/<id>")
@validate_resource_type
def show_details(type: str, id: str):
    """Show detailed view of a resource"""
    try:
        result = run_deadwax_command(f"show/{type}", id)
        if request.headers.get("HX-Request"):
            return render_template(f"partials/{type}.html", item=result)
        return render_template(f"partials/{type}.html", item=result)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        abort(500)


@app.errorhandler(400)
def bad_request(error):
    if request.headers.get("HX-Request"):
        return render_template("errors/400.html", error=str(error.description)), 400
    return render_template("errors/400.html", error=str(error.description)), 400


@app.errorhandler(404)
def not_found(error):
    if request.headers.get("HX-Request"):
        return render_template("errors/404.html", error=str(error.description)), 404
    return render_template("errors/404.html", error=str(error.description)), 404


@app.errorhandler(500)
def server_error(error):
    if request.headers.get("HX-Request"):
        return render_template("errors/500.html", error="Internal server error"), 500
    return render_template("errors/500.html", error="Internal server error"), 500


# Register blueprints
app.register_blueprint(api)
app.register_blueprint(web)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
