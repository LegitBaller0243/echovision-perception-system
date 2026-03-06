import sys
from pathlib import Path
import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIST = PROJECT_ROOT / "apps" / "frontend" / "dist"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.api.src.routes import routes
from services.app_core.observability import configure_logging

def create_app():
    """Create and configure the Flask application."""
    configure_logging()
    app = Flask(__name__, static_folder=str(FRONTEND_DIST), static_url_path="")

    CORS(app)

    app.register_blueprint(routes)

    @app.route("/", defaults={"path": ""}, methods=["GET"])
    @app.route("/<path:path>", methods=["GET"])
    def serve_frontend(path):
        if not FRONTEND_DIST.exists():
            return jsonify({"error": "Frontend build not found. Run `npm run build` in apps/frontend."}), 503

        requested = FRONTEND_DIST / path
        if path and requested.is_file():
            return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, "index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=int(os.getenv("PORT", "5001")), host="0.0.0.0")
