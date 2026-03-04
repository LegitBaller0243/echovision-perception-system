from flask import Flask
from flask_cors import CORS
from routes import routes

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    CORS(app)

    app.register_blueprint(routes)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000, host="0.0.0.0")
