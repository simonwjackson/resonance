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


def parse_jsonl_output(output: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Parse JSONL output from deadwax command

    Args:
        output: String containing one or more JSON objects, one per line

    Returns:
        Either a single JSON object or a list of JSON objects
    """
    try:
        # Split output into lines and filter out empty lines
        lines = [line.strip() for line in output.splitlines() if line.strip()]

        if not lines:
            raise ValueError("Empty output from deadwax command")

        # Parse each line as JSON
        results = [json.loads(line) for line in lines]

        # If there's only one result, return it as a single object
        # Otherwise return the list of results
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
    """
    Run a deadwax command and return the parsed JSONL result

    Args:
        command: The deadwax command (show/search)
        target: The target ID or search query
        recommend: Optional recommendation tag

    Returns:
        Either a single JSON object or a list of JSON objects
    """
    try:
        cmd = [
            "nix",
            "run",
            "/snowscape/code/github/simonwjackson/mountainous/main#deadwax",
            "--",
        ]
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


@app.errorhandler(400)
def bad_request(error):
    return jsonify(error=str(error.description)), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify(error=str(error.description)), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify(error="Internal server error"), 500


@app.route("/api/show/<type>/<id>")
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


@app.route("/api/search/<type>/<query>")
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


@app.route("/")
def index():
    """Simple API documentation page"""
    endpoints = {
        "show": {
            "artist": "/api/show/artist/<id>",
            "album": "/api/show/album/<id>",
            "playlist": "/api/show/playlist/<id>",
            "song": "/api/show/song/<id>",
        },
        "search": {
            "artist": "/api/search/artist/<query>",
            "album": "/api/search/album/<query>",
            "playlist": "/api/search/playlist/<query>",
            "song": "/api/search/song/<query>",
            "all": "/api/search/all/<query>",
        },
    }
    return jsonify(endpoints)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
