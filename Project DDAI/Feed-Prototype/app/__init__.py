from flask import Flask
import os

# Initialize SQLAlchemy (do not attach to an app yet)

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Database Configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///database.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Register the database with the app

    # Import blueprints (ensuring routes are inside app context)
    from app.routes import main
    app.register_blueprint(main)

    return app
