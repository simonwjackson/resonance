import json
import logging
import subprocess
from typing import Any, Dict, List, Optional, Union

import requests
from flask import Blueprint, Response, abort, jsonify, request, stream_with_context
from flask_caching import Cache

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
api = Blueprint("api", __name__, url_prefix="/api")


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
    from functools import wraps

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
    from functools import wraps

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


# API Routes
@api.route("/show/<type>/<id>")
@validate_resource_type
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
def search_resource(type: str, query: str):
    """Handle search requests"""
    try:
        result = run_deadwax_command(f"search/{type}", query)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing search request: {str(e)}")
        abort(500)


@api.route("/get/", defaults={"url": ""})
@api.route("/get/<path:url>")
def get_url(url):
    """
    Proxy endpoint that handles both YouTube audio extraction and general URL proxying.
    Takes the entire URL literally after /api/get/
    """
    try:
        # Get the full path after /api/get/
        full_path = request.full_path
        url = full_path[full_path.index("/get/") + 5 :]

        # Remove query string marker from request.full_path if it exists
        if url.endswith("?"):
            url = url[:-1]

        if not url:
            abort(400, description="No URL provided")

        # Check if it's a YouTube URL
        is_youtube = any(
            host in url
            for host in [
                "music.youtube.com",
                "youtube.com",
                "youtu.be",
                "www.youtube.com",
            ]
        )

        if is_youtube:
            try:
                # First get the best audio format URL
                cmd = [
                    "yt-dlp",
                    "-f",
                    "bestaudio",
                    "-g",  # Print URL only
                    "--no-warnings",
                    url,
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                direct_url = result.stdout.strip()

                if not direct_url:
                    abort(500, description="Could not extract audio URL")

                # Make request to the direct URL
                r = requests.get(direct_url, stream=True)

                # Get content type from response headers or default to audio/mpeg
                content_type = r.headers.get("content-type", "audio/mpeg")

            except subprocess.CalledProcessError as e:
                logger.error(f"yt-dlp error: {e.stderr}")
                abort(500, description="Failed to process YouTube URL")

        else:
            # For non-YouTube URLs, make a direct request
            r = requests.get(url, stream=True)

            if r.status_code != 200:
                abort(r.status_code, description="Failed to fetch URL")

            content_type = r.headers.get("content-type", "application/octet-stream")

        # Create streaming response
        return Response(
            stream_with_context(r.iter_content(chunk_size=8192)),
            content_type=content_type,
            headers={"Content-Disposition": f'inline; filename="download"'},
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        abort(500, description="Failed to fetch URL")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        abort(500, description="Internal server error")
