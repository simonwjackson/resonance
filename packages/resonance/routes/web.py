import logging

from flask import Blueprint, abort, render_template, request
from flask_caching import Cache
from routes.api import run_deadwax_command

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
web = Blueprint("web", __name__)


# Web Routes
@web.route("/")
def index():
    """Main page with search interface"""
    return render_template("index.html")


@web.route("/search")
def search():
    """Handle search requests"""
    query = request.args.get("q", "")
    search_type = request.args.get("type", "all")
    sort = request.args.get("sort", "relevance")

    results = []
    selected_item = None

    if query:
        try:
            results = run_deadwax_command(f"search/{search_type}", query)

            if sort == "name":
                results.sort(key=lambda x: x.get("name", ""))
            elif sort == "date":
                results.sort(key=lambda x: x.get("year", 0), reverse=True)

        except Exception as e:
            logger.error(f"Search error: {str(e)}")

    # For HTMX requests, return only results
    if request.headers.get("HX-Request"):
        try:
            return render_template(
                "default/components/search/results/index.html", results=results
            )
        except:
            return render_template("search/results/index.html", results=results)

    # For full page requests
    try:
        return render_template(
            "default/pages/search/index.html",
            results=results,
            selected_item=selected_item,
        )
    except:
        return render_template(
            "search/index.html", results=results, selected_item=selected_item
        )


@web.route("/album/<id>")
def show_album(id: str):
    """Show detailed view of an album"""
    try:
        result = run_deadwax_command(f"show/album", id)

        # For HTMX requests, check if new template exists, otherwise fall back
        if request.headers.get("HX-Request"):
            try:
                return render_template("default/pages/album/[id].html", item=result)
            except:
                return render_template("partials/album.html", item=result)

        # For full page requests, try new path first, fall back to old
        try:
            return render_template("default/pages/album/[id].html", item=result)
        except:
            return render_template("partials/album.html", item=result)

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        abort(500)


@web.route("/artist/<id>")
def show_artist(id: str):
    """Show detailed view of an artist"""
    try:
        result = run_deadwax_command(f"show/artist", id)

        # For HTMX requests, check if new template exists, otherwise fall back
        if request.headers.get("HX-Request"):
            try:
                return render_template("default/pages/artist/[id].html", item=result)
            except:
                return render_template("partials/artist.html", item=result)

        # For full page requests, try new path first, fall back to old
        try:
            return render_template("default/pages/artist/[id].html", item=result)
        except:
            return render_template("partials/artist.html", item=result)

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        abort(500)


@web.route("/<type>/<id>")
def show_details(type: str, id: str):
    """Show detailed view of a resource"""
    try:
        result = run_deadwax_command(f"show/{type}", id)

        # For HTMX requests, only return the partial content
        if request.headers.get("HX-Request"):
            template = f"partials/{type}.html"
            return render_template(template, item=result)

        # For full page requests, return the complete page
        return render_template(f"{type}.html", item=result)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        abort(500)


# Error handlers
@web.app_errorhandler(400)
def bad_request(error):
    if request.headers.get("HX-Request"):
        return render_template("errors/400.html", error=error.description), 400
    return render_template("errors/400.html", error=error.description), 400


@web.app_errorhandler(404)
def not_found(error):
    if request.headers.get("HX-Request"):
        return render_template("errors/404.html", error=error.description), 404
    return render_template("errors/404.html", error=error.description), 404


@web.app_errorhandler(500)
def server_error(error):
    if request.headers.get("HX-Request"):
        return render_template("errors/500.html", error="Internal server error"), 500
    return render_template("errors/500.html", error="Internal server error"), 500
