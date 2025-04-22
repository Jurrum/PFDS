# app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'replace-with-a-secure-random-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///feed.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # import models so tables get created
    from app.models.content  import Content
    from app.models.category import Category
    from app.models.rating   import Rating

    with app.app_context():
        db.create_all()

    from app.routes import main
    app.register_blueprint(main)

    return app
