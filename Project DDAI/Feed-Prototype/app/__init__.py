# app/__init__.py
from dotenv import load_dotenv
load_dotenv()
import os
from flask import Flask, session, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from flask_session import Session
from config import config, Config
from pathlib import Path
import openai



# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()

# Initialize session extension
# The original 'flask_session = Session()' is kept, but 'session' imported above is the request session proxy.
# This was a source of confusion. 'flask_session_ext' might be a clearer name for the extension instance.
flask_session_ext = Session() # Renamed for clarity to avoid conflict with request 'session'
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("Missing OPENAI_API_KEY in environment")

def create_app(config_name='default'):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Apply configuration
    app.config.from_object(config[config_name])
    app.config.from_prefixed_env()  # Load environment variables with FLASK_ prefix
    
    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        
        # Ensure session directory exists
        session_dir = os.path.join(app.instance_path, 'flask_session')
        os.makedirs(session_dir, exist_ok=True)
        app.config['SESSION_FILE_DIR'] = session_dir
        
    except OSError as e:
        print(f"Error creating instance folder: {e}")
    
    # Ensure the database directory exists
    db_dir = os.path.join(app.instance_path, 'database')
    os.makedirs(db_dir, exist_ok=True)
    
    # Configure session settings
    app.config.update(
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR=os.path.join(app.instance_path, 'flask_session'),
        SESSION_PERMANENT=True,  # Make session permanent
        SESSION_USE_SIGNER=True,
        SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
        SESSION_COOKIE_HTTPONLY=True,
        PERMANENT_SESSION_LIFETIME=86400,  # 1 day in seconds
        SESSION_COOKIE_NAME='session',
        SESSION_REFRESH_EACH_REQUEST=True
    )
    
    # Initialize session
    flask_session_ext.init_app(app) # Use renamed extension instance
    
    # Set a default database URI that will be updated per user session
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_BINDS'] = {}
    
    def get_user_db_uri(username):
        """Get or create a database URI for a specific user."""
        if not username:
            return 'sqlite:///:memory:'
        user_db_dir = os.path.join(db_dir, 'users')
        os.makedirs(user_db_dir, exist_ok=True)
        return f'sqlite:///{os.path.join(user_db_dir, f"{username}.db")}'
    
    def switch_user_db(username):
        """Switch the database connection to the specified user's database."""
        db_uri = get_user_db_uri(username)
        
        # Only update if the URI has changed
        if app.config.get('SQLALCHEMY_DATABASE_URI') != db_uri:
            app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
            app.config['SQLALCHEMY_BINDS'] = {}
            
            # Create database and tables if they don't exist
            with app.app_context():
                db.create_all()
        
        return db_uri
    
    def cleanup_old_sessions(username, max_sessions=5):
        """Clean up old session data for a user, keeping only the most recent sessions."""
        if not username:
            return
            
        sessions_dir = os.path.join(db_dir, 'sessions')
        if not os.path.exists(sessions_dir):
            return
            
        # Get all session files for this user
        user_sessions = []
        for f in os.listdir(sessions_dir):
            if f.startswith(f"{username}_") and f.endswith('.json'):
                user_sessions.append(f)
                
        # Sort by modification time (newest first)
        user_sessions.sort(key=lambda x: os.path.getmtime(os.path.join(sessions_dir, x)), reverse=True)
        
        # Delete old sessions if we have more than max_sessions
        for old_session in user_sessions[max_sessions:]:
            try:
                os.remove(os.path.join(sessions_dir, old_session))
                logger.info(f"Removed old session file: {old_session}")
            except Exception as e:
                logger.error(f"Error removing old session {old_session}: {e}")
    
    # Make functions available to the app context
    app.switch_user_db = switch_user_db
    app.cleanup_old_sessions = cleanup_old_sessions
    
    # Initialize database
    db.init_app(app)
    
    # Initialize other extensions
    migrate.init_app(app, db)
    
    # Session configuration is already set up earlier
    
    # Register blueprints
    from .routes import main as main_bp
    if 'main' not in app.blueprints:
        app.register_blueprint(main_bp)
    
    # Register other blueprints if they exist
    try:
        from .auth import bp as auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
    except ImportError:
        print("Auth blueprint not found, skipping...")
    
    try:
        from .api import bp as api_bp
        app.register_blueprint(api_bp, url_prefix='/api')
    except ImportError:
        print("API blueprint not found, skipping...")
    
    # Create necessary directories
    required_dirs = [
        app.config.get('UPLOAD_FOLDER', 'uploads'),
        'session_data',
        'logs'
    ]
    
    for dir_path in required_dirs:
        try:
            os.makedirs(dir_path, exist_ok=True)
        except OSError as e:
            print(f"Warning: Could not create directory {dir_path}: {e}")
    
    # Initialize database
    with app.app_context():
        db.create_all()
    
    # import models so tables get created
    from app.models.content  import Content
    from app.models.category import Category
    from app.models.session import UserSession
    from app.models.rating   import Rating
    
    with app.app_context():
        db.create_all()

    return app
