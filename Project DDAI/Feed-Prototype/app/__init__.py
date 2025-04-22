# app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///feed.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # ---- Make sure your models are imported before you create tables ----
    # this causes SQLAlchemy to register the Content class (and any others)
    from app.models.content import Content
    from app.models.category import Category    

    # Automatically create any missing tables
    
    with app.app_context():
        db.create_all()

    # Import and register your blueprints
    from app.routes import main
    app.register_blueprint(main)

    return app
