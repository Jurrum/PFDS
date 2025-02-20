from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Initialize SQLAlchemy (do not attach to an app yet)
db = SQLAlchemy()

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Database Configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///database.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Register the database with the app
    db.init_app(app)

    # Import blueprints (ensuring routes are inside app context)
    from app.routes import main
    app.register_blueprint(main)

    # Create database tables within the app context
    with app.app_context():
        db.create_all()

    return app
