import sys
from pathlib import Path

from flask import Flask
from flask_cors import CORS

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.api.src.api.routes import routes

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    CORS(app)

    app.register_blueprint(routes)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000, host="0.0.0.0")
