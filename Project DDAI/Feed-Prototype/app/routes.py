import os
import json
import shutil
import logging
import random
import openai
import requests
from datetime import datetime, timedelta
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app, session, flash
from flask_login import current_user, login_required, UserMixin, LoginManager
from flask_session import Session as FlaskSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app import db
from app.models.content import Content
from app.models.session import UserSession
from app.models.rating import Rating
from app.models.category import Category
from app.utils.export_utils import save_questionnaire_responses, export_session_data
from app.utils.session_utils import get_session_directory, move_to_session
from app.utils.user_logging import UserLogger
from app.utils.content_generator import generate_post, generate_posts

# Initialize Flask-Session
flask_session = FlaskSession()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create main Blueprint
main = Blueprint('main', __name__)

# Initialize login manager
login_manager = LoginManager()

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Initialize user logger
user_logger = UserLogger()

def create_default_posts(username, count=5):
    """Create default posts when no other content is available."""
    if not username:
        current_app.logger.error("Cannot create default posts: No username provided")
        return False
        
    current_app.logger.info(f"Creating {count} default posts for user: {username}")
    
    # Categories to generate posts for
    categories = ['general', 'technology', 'science', 'health', 'entertainment']
    
    posts_created = 0
    
    try:
        # Switch to the user's database
        current_app.switch_user_db(username)
        
        # Make sure tables exist
        try:
            db.create_all()
        except Exception as e:
            current_app.logger.warning(f"Table creation warning: {str(e)}")
            # Continue even if table creation fails - it might already exist
        
        # Generate and save posts
        for i in range(count):
            try:
                # Cycle through categories
                category = categories[i % len(categories)]
                
                # Generate post content
                post_text = generate_post(category)
                
                # Create post
                post = Content(
                    username=username,
                    text=post_text,
                    category=category.capitalize(),
                    likes=0,
                    dislikes=0,
                    views=0,
                    view_time=0.0,
                    created_at=datetime.utcnow()
                )
                db.session.add(post)
                posts_created += 1
                
                # Commit after each post to ensure we save at least some posts
                db.session.commit()
                current_app.logger.debug(f"Created post: {post_text[:50]}...")
                
            except IntegrityError:
                db.session.rollback()
                current_app.logger.warning("Duplicate post detected, skipping")
                continue
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error creating post: {str(e)}")
                continue
        
        current_app.logger.info(f"Successfully created {posts_created} posts for user: {username}")
        return posts_created > 0
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in create_default_posts: {str(e)}", exc_info=True)
        return False
    finally:
        try:
            db.session.remove()
        except:
            pass



@main.route('/posts/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    """Like a post and track interactions."""
    # Track interaction
    session['interaction_count'] = session.get('interaction_count', 0) + 1
    session.modified = True
    request._cached_data = json.dumps({'rating': 'like'})
    return rate_post(post_id)


@main.route('/posts/<int:post_id>/dislike', methods=['POST'])
def dislike_post(post_id):
    """Dislike a post and track interactions."""
    # Track interaction
    session['interaction_count'] = session.get('interaction_count', 0) + 1
    session.modified = True
    request._cached_data = json.dumps({'rating': 'dislike'})
    return rate_post(post_id)

def init_session_files(username):
    """Initialize session files and directories."""
    try:
        logger.info(f"Initializing session files for user: {username}")
        
        # Create session directory
        session_dir = get_session_directory(username)
        logger.info(f"Session directory: {session_dir}")
        
        # Ensure the session directory exists
        session_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Verified/created session directory")
        
        # Move existing database if it exists
        old_db_path = os.path.join(current_app.instance_path, 'feed.db')
        logger.info(f"Checking for existing database at: {old_db_path}")
        
        if os.path.exists(old_db_path):
            new_db_path = session_dir / 'feed.db'
            logger.info(f"Found existing database, moving to: {new_db_path}")
            
            if not new_db_path.exists():
                shutil.move(old_db_path, new_db_path)
                logger.info("Moved existing database to session directory")
            else:
                logger.info("Database already exists in session directory, not moving")
        
        # Update database URI for this session
        db_uri = f'sqlite:///{session_dir}/feed.db'
        logger.info(f"Setting database URI to: {db_uri}")
        
        current_app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        logger.info("Updated SQLALCHEMY_DATABASE_URI in app config")
        
        # Reinitialize SQLAlchemy with the new database URI
        logger.info("Reinitializing SQLAlchemy with new database URI")
        db.session.remove()
        logger.info("Closed existing database sessions")
        
        # Get engine to force initialization with new URI
        engine = db.get_engine(current_app, bind=None)
        logger.info(f"Created new database engine: {engine}")
        
        # Create all tables
        logger.info("Creating database tables...")
        db.create_all()
        logger.info("Database tables created/verified")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in init_session_files: {str(e)}", exc_info=True)
        return False

# ——— Configuration ———
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Default scoring weights
DEFAULT_WEIGHTS = {
    'likes': 2.0,
    'shares': 3.0,
    'comments': 1.5,
    'dislikes': 1.0
}

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# Questions for the algorithm relationship scale
ALGORITHM_RELATIONSHIP_QUESTIONS = [
    "I feel able to influence what appears in my feed.",
    "I understand how the feed's algorithm works.",
    "I trust the recommendations I receive.",
    "The feed reflects my personal interests accurately.",
    "Content diversity is high (varied viewpoints, topics).",
    "The feed sometimes feels manipulative.",
    "Using the feed leaves me feeling mentally refreshed.",
    "I experience time distortion or lose track of time.",
    "I perceive the feed as transparent about how it works.",
    "It is easy to correct the feed when it shows unwanted content.",
    "I am satisfied with the overall relevance of posts.",
    "I feel the algorithm respects my privacy.",
    "The feed frequently surprises me in a pleasant way.",
    "Interacting with the feed requires little mental effort.",
    "My well-being is positively affected by the feed."
]

# ——— Routes ———
@main.route('/start')
def start():
    """Show the start page with instructions."""
    return render_template('start.html')

@main.route('/end-session', methods=['GET', 'POST'])
@login_required
def end_session():
    """
    Handle session end process.
    
    GET: Display end session page and clean up resources
    POST: Mark session as ended and redirect to post-questionnaire
    """
    username = session.get('username')
    if not username:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Not logged in'}), 401
        return redirect(url_for('main.start'))
    
    current_app.logger.info(f"Ending session for user: {username}")
    
    try:
        # Get the current user session
        user_session = UserSession.query.filter_by(username=username, completed=False).order_by(UserSession.id.desc()).first()
        
        if user_session:
            # Mark the session as completed
            user_session.completed = True
            user_session.end_time = datetime.utcnow()
            user_session.interaction_count = session.get('interaction_count', 0)
            db.session.commit()
            current_app.logger.info(f"Marked session {user_session.id} as completed")
        
        # Set flags to show post-questionnaire and ensure proper redirect
        session['show_post_questionnaire'] = True
        session['post_questionnaire_redirect'] = True  # Additional flag for extra safety
        session.modified = True
        
        # Commit session changes
        db.session.commit()
        
        # Get the URL for the post-questionnaire
        post_questionnaire_url = url_for('main.post_questionnaire')
        current_app.logger.info(f"Redirecting to post-questionnaire: {post_questionnaire_url}")
        
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'success',
                'redirect': post_questionnaire_url,
                'message': 'Session ended successfully'
            })
            
        # For non-AJAX requests, redirect directly
        return redirect(post_questionnaire_url, code=303)
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in end_session: {str(e)}", exc_info=True)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'error',
                'message': 'Failed to end session',
                'error': str(e)
            }), 500
            
        flash('An error occurred while ending your session. Please try again.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # For GET requests, handle session cleanup and show end page
    try:
        user_session = UserSession.query.filter_by(username=username).order_by(UserSession.id.desc()).first()
        if not user_session:
            return redirect(url_for('main.start'))

        # Calculate total interactions
        log_file = os.path.join(
            current_app.root_path,
            'logs',
            f'participant_{username}.csv'
        )
        total_interactions = 0
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                total_interactions = sum(1 for line in f) - 1  # subtract header

        # Update session data
        user_session.end_time = datetime.utcnow()
        user_session.completed = True
        user_session.total_interactions = total_interactions
        db.session.commit()

        # Save interaction data to CSV
        user_logger.save_session_data(username)


        # Get the database path
        db_path = os.path.join(current_app.instance_path, 'feed.db')
        new_db_path = os.path.join(
            current_app.root_path,
            'databases',
            f'{username}_feed.db'
        )
        
        # Create databases directory if it doesn't exist
        os.makedirs(os.path.dirname(new_db_path), exist_ok=True)

        # Close all database connections
        try:
            # Close all sessions
            db.session.close_all()
            db.session.remove()
            
            # Dispose engine
            engine = db.engine
            engine.dispose()
            
            # Wait a moment
            import time
            time.sleep(0.1)

            # Copy the database to new location
            if os.path.exists(db_path):
                import shutil
                shutil.copy2(db_path, new_db_path)

            # Clear Flask session
            session.clear()

            return render_template('end.html', username=username)

        except Exception as e:
            current_app.logger.error(f"Error handling database: {str(e)}")
            raise

    except Exception as e:
        current_app.logger.error(f"Error in end_session: {str(e)}")
        session.clear()
        return redirect(url_for('main.start'))



@main.route('/thank-you')
def thank_you():
    """Show thank you page after completing the study."""
    return render_template('thank_you.html')

@main.route('/start-session', methods=['POST'])
def start_session():
    try:
        logger.info("=== Starting new session ===")
        username = request.form.get('username')
        logger.info(f"Username from form: {username}")
        
        if not username:
            logger.error("No username provided")
            return jsonify({'error': 'Username is required'}), 400
        
        logger.info("Initializing session files...")
        # Initialize session files and directories
        if not init_session_files(username):
            logger.error("Failed to initialize session files")
            return jsonify({'error': 'Failed to initialize session files'}), 500
        
        logger.info("Checking for existing user session...")
        # Check if a session already exists for this username
        existing_session = UserSession.query.filter_by(username=username).first()
        
        if existing_session:
            logger.info(f"Found existing session for user {username}, updating it")
            # Update existing session
            existing_session.start_time = datetime.utcnow()
            existing_session.end_time = None
            existing_session.completed = False
            existing_session.pre_questionnaire_completed = False
            existing_session.post_questionnaire_completed = False
            existing_session.questionnaire_data = '{}'
            user_session = existing_session
        else:
            logger.info("No existing session found, creating new one...")
            # Create a new user session
            user_session = UserSession(username=username)
            logger.info(f"Created new user session: {user_session}")
            db.session.add(user_session)
        
        logger.info("Committing session changes to database...")
        db.session.commit()
        logger.info("Successfully committed session to database")
        
        # Store session data
        session.permanent = True
        session['user_session_id'] = user_session.id
        session['username'] = username
        session['pre_questionnaire_completed'] = False
        session['post_questionnaire_completed'] = False
        session.modified = True
        logger.info("Stored session data in session")
        
        # Force session to be saved
        session.modified = True
        logger.info("Session modified flag set to True")
        
        # Initialize user logger with session directory
        session_dir = get_session_directory(username)
        logger.info(f"Session directory: {session_dir}")
        
        log_file = session_dir / 'session_log.csv'
        logger.info(f"Log file path: {log_file}")
        
        user_logger.initialize_logger(username, log_file=str(log_file))
        logger.info("Initialized user logger")
        
        # Log session start
        user_logger.log_event('session_start', {'status': 'started'})
        logger.info("Logged session start event")
        
        # Prepare response data
        response_data = {
            'message': 'Session started',
            'session_id': user_session.id,
            'username': username,
            'redirect_url': url_for('main.pre_questionnaire', _external=True)
        }
        
        # If it's an AJAX request, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            response = jsonify(response_data)
            response.headers['Content-Type'] = 'application/json'
            return response
            
        # Otherwise, redirect directly
        return redirect(url_for('main.pre_questionnaire'))
        
    except Exception as e:
        logger.error(f"Error in start_session: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Failed to start session: {str(e)}'}), 500

@main.route('/start-new-session/<username>')
def start_new_session(username):
    """
    Start a new session for an existing user.
    This will completely reset all data for a clean start.
    """
    try:
        logger.info(f"Starting new session for user: {username}")
        
        # Clear any existing session data
        session.clear()
        session.modified = True
        logger.info("Cleared existing session data")
        
        # Ensure we have a clean database state for this user
        with current_app.app_context():
            # Switch to the user's database
            db_uri = current_app.switch_user_db(username)
            logger.info(f"Switched to database: {db_uri}")
            
            # Clear existing data
            logger.info("Dropping all tables...")
            db.drop_all()
            logger.info("Creating all tables...")
            db.create_all()
            
            # Create a new user session
            logger.info("Creating new user session...")
            user_session = UserSession(username=username)
            db.session.add(user_session)
            db.session.commit()
            
            # Initialize session data
            session.permanent = True
            session['user_session_id'] = user_session.id
            session['username'] = username
            session['pre_questionnaire_completed'] = False
            session['post_questionnaire_completed'] = False
            session.modified = True
            logger.info("Initialized new session data")
            logger.info(f"Created new user session with ID: {user_session.id}")
            
            # Initialize user logger
            logger.info("Initializing user logger...")
            session_dir = get_session_directory(username)
            log_file = session_dir / 'session_log.csv'
            user_logger.initialize_logger(username, log_file=str(log_file))
            user_logger.log_event('session_start', {'status': 'started'})
            logger.info("User logger initialized")
            
            # Force session save
            session.modified = True
            
            # Redirect to the pre-questionnaire
            logger.info("Redirecting to pre-questionnaire")
            return redirect(url_for('main.pre_questionnaire'))
        
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                response = jsonify(response_data)
                response.headers['Content-Type'] = 'application/json'
                return response
                
            return redirect(url_for('main.pre_questionnaire'), code=303)
            

    except Exception as e:
        error_msg = f"Error starting new session: {str(e)}"
        logger.error(error_msg, exc_info=True)
        try:
            # Clear the session by removing all attributes
            for key in list(flask_session.keys()):
                flask_session.pop(key, None)
            flask_session.modified = True
        except Exception as clear_error:
            logger.error(f"Error clearing session: {str(clear_error)}", exc_info=True)
        return redirect(url_for('main.start'))

@main.route('/pre-questionnaire', methods=['GET', 'POST'])
def pre_questionnaire():
    """Show the pre-interaction questionnaire."""
    current_app.logger.info("=== Starting pre_questionnaire view ===")
    current_app.logger.info(f"Request method: {request.method}")
    
    # Log session data safely
    session_data = dict(session)
    current_app.logger.info(f"Session data: {session_data}")
    
    username = session.get('username')
    if not username:
        logger.warning("No username in session, redirecting to start")
        return redirect(url_for('main.start'))
    
    logger.info(f"Current username from session: {username}")
    
    # Get or create user session
    user_session = UserSession.query.filter_by(username=username).first()
    if not user_session:
        logger.warning(f"No user session found for {username}, creating new one")
        user_session = UserSession(username=username)
        db.session.add(user_session)
        db.session.commit()
    
    logger.info(f"User session ID: {user_session.id}")
    
    # Check if pre-questionnaire is already completed
    if session.get('pre_questionnaire_completed', False):
        logger.info(f"Pre-questionnaire already completed for {username}, redirecting to index")
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        logger.info("Processing POST request")
        logger.info(f"Form data: {request.form}")
        
        try:
            # Create responses dictionary
            responses = {
                'timestamp': datetime.utcnow().isoformat(),
                'daily_use': request.form.get('daily_use'),
                'primary_platform': request.form.get('primary_platform'),
                'mental_model': request.form.get('mental_model'),
                'keywords': request.form.get('keywords'),
                'control_experience': request.form.get('control_experience'),
                'scale_responses': {f"c{i+1}": request.form[f"c{i+1}"] for i in range(15) if f"c{i+1}" in request.form}
            }
            
            # Save to database
            user_session.questionnaire_data = json.dumps({'pre_questionnaire': responses})
            user_session.pre_questionnaire_completed = True
            
            # Save to CSV
            try:
                save_questionnaire_responses(username, 'pre', responses)
            except Exception as e:
                logger.error(f"Error saving questionnaire to CSV: {str(e)}", exc_info=True)
            
            db.session.commit()
            
            # Update session
            session['pre_questionnaire_completed'] = True
            session.modified = True
            
            logger.info("Pre-questionnaire submitted successfully")
            return redirect(url_for('main.index'))
            
        except Exception as e:
            logger.error(f"Error processing form data: {str(e)}", exc_info=True)
            db.session.rollback()
            flash('An error occurred while saving your responses. Please try again.', 'error')
    
    # For GET request or form validation errors, show the form
    logger.info("Rendering pre-questionnaire form")
    return render_template('pre_questionnaire.html',
                         username=username,
                         questions=ALGORITHM_RELATIONSHIP_QUESTIONS)

@main.route('/post-questionnaire', methods=['GET', 'POST'])
@login_required
def post_questionnaire():
    """Show and handle the post-interaction questionnaire."""
    # Log session data for debugging
    current_app.logger.info(f"=== POST-QUESTIONNAIRE ROUTE START ===")
    current_app.logger.info(f"Session ID: {session.sid}")
    current_app.logger.info(f"Session data: {dict(session)}")
    
    username = session.get('username')
    
    # Check if user is coming from the end session flow
    show_post_questionnaire = session.get('show_post_questionnaire', False)
    post_questionnaire_redirect = session.get('post_questionnaire_redirect', False)
    
    # Log the current state for debugging
    current_app.logger.info(
        f"Post-questionnaire access - User: {username}, "
        f"Show: {show_post_questionnaire}, "
        f"Redirect: {post_questionnaire_redirect}, "
        f"Method: {request.method}"
    )
    
    # If not showing post-questionnaire and not a POST request, check if pre-questionnaire is completed
    if not show_post_questionnaire and not post_questionnaire_redirect and request.method != 'POST':
        current_app.logger.warning("Not showing post-questionnaire and not a redirect, checking pre-questionnaire")
        pre_questionnaire_completed = session.get('pre_questionnaire_completed', False)
        if not username or not pre_questionnaire_completed:
            current_app.logger.warning("No username or pre-questionnaire not completed, redirecting to start")
            current_app.logger.info(f"Session data before redirect: {dict(session)}")
            return redirect(url_for('main.start'))
    
    current_app.logger.info(f"Session user: {username}")
    
    # Get user session from database
    user_session_id = session.get('user_session_id')
    current_app.logger.info(f"Looking up user session with ID: {user_session_id}")
    
    user_session = UserSession.query.get(user_session_id) if user_session_id else None
    if not user_session:
        current_app.logger.error(f"No user session found for ID: {user_session_id}")
        current_app.logger.info(f"Available sessions: {[s.id for s in UserSession.query.all()]}")
        current_app.logger.info(f"Session data before redirect: {dict(session)}")
        return redirect(url_for('main.start'))
    
    current_app.logger.info(f"Found user session: {user_session.id} for {user_session.username}")
    
    # If we got here from the end session flow, clear the flags
    if show_post_questionnaire or post_questionnaire_redirect:
        current_app.logger.info("Clearing post-questionnaire flags from session")
        session.pop('show_post_questionnaire', None)
        session.pop('post_questionnaire_redirect', None)
        session.modified = True
        try:
            db.session.commit()
            current_app.logger.info("Successfully committed session changes")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error committing session changes: {str(e)}", exc_info=True)
    
    current_app.logger.info("=== POST-QUESTIONNAIRE ROUTE END ===")
    
    current_app.logger.info(f"Found user session: {user_session.id} for {user_session.username}")
    
    if request.method == 'POST':
        current_app.logger.info("Processing POST request for post-questionnaire")
        
        try:
            # Get interaction data
            interactions = request.form.getlist('interaction', [])
            other_interaction = request.form.get('other_interaction', '').strip()
            if other_interaction and 'other' in interactions:
                interactions[interactions.index('other')] = f"other: {other_interaction}"
                
            # Store responses in the session or database
            responses = {
                'timestamp': datetime.utcnow().isoformat(),
                'interactions_used': interactions,
                'ease_of_use': request.form.get('ease_of_use', ''),
                'understanding': request.form.get('understanding', ''),
                'control_level': request.form.get('control_level', ''),
                'scale_responses': {f"q{i+1}": request.form.get(f"q{i+1}", '') for i in range(15) if f"q{i+1}" in request.form},
                'feedback': request.form.get('feedback', '')
            }
            
            current_app.logger.info("Collected post-questionnaire responses")
            
            # Get existing data
            current_app.logger.info("Getting existing questionnaire data")
            current_data = user_session.questionnaire_data_dict
            current_app.logger.info(f"Current data type: {type(current_data).__name__}")
            
            if not isinstance(current_data, dict):
                current_app.logger.warning("Current data is not a dictionary, initializing new dict")
                current_data = {}
            
            # Update with new responses
            current_data['post_questionnaire'] = responses
            user_session.questionnaire_data = json.dumps(current_data)
            
            # Mark session as completed
            user_session.completed = True
            user_session.end_time = datetime.utcnow()
            
            db.session.commit()
            current_app.logger.info("Successfully saved post-questionnaire responses")
            
            # Clear session data
            session.clear()
            
            # Redirect to thank you page
            return redirect(url_for('main.thank_you'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving post-questionnaire: {str(e)}", exc_info=True)
            flash('Error saving your responses. Please try again.', 'error')
    
    # For GET request, show the form
    return render_template('post_questionnaire.html',
                         username=username,
                         questions=ALGORITHM_RELATIONSHIP_QUESTIONS)


@main.route('/')
def index():
    """
    Render the home page; posts fetched via JS.
    Redirects to pre-questionnaire if not completed.
    """
    logger.info("=== Entering index route ===")
    
    # Check if user is logged in
    username = session.get('username')
    if not username:
        logger.warning("No username in session, redirecting to start")
        return redirect(url_for('main.start'))
    
    logger.info(f"Current username: {username}")
    
    try:
        # Switch to the correct database for this user
        current_app.switch_user_db(username)
        logger.info("Switched to user's database")
        
        # Check pre-questionnaire status in session first (faster)
        if not session.get('pre_questionnaire_completed', False):
            logger.info("Pre-questionnaire not completed according to session, checking database...")
            
            # Get user session from database
            user_session = UserSession.query.filter_by(username=username).order_by(UserSession.id.desc()).first()
            
            if not user_session or not user_session.pre_questionnaire_completed:
                logger.info("Pre-questionnaire not completed, redirecting to pre-questionnaire")
                return redirect(url_for('main.pre_questionnaire'))
            else:
                # Update session to reflect database state
                session['pre_questionnaire_completed'] = True
                session.modified = True
                logger.info("Updated session to reflect completed pre-questionnaire")
        
        # Check if post-questionnaire is completed (for ending the session)
        user_session = UserSession.query.filter_by(username=username).order_by(UserSession.id.desc()).first()
        if user_session and user_session.post_questionnaire_completed:
            logger.info("Post-questionnaire completed, redirecting to thank you page")
            return redirect(url_for('main.thank_you'))
        
        logger.info("Rendering home page")
        return render_template('home.html')
        
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}", exc_info=True)
        flash('An error occurred while loading the page. Please try again.', 'error')
        return redirect(url_for('main.start'))


@main.route('/upload', methods=['GET', 'POST'])
def upload():
    """
    GET: render upload form
    POST: save new post (text + image + category)
    """
    username = session.get('username')
    if not username:
        flash('You must be logged in to upload posts', 'error')
        return redirect(url_for('main.index'))
    
    # Switch to the correct database for this user
    current_app.switch_user_db(username)
    
    if request.method == 'POST':
        try:
            # Get form data
            text_content = request.form.get('text', '').strip()
            category = request.form.get('category', 'General').strip()
            image_file = request.files.get('image')
            image_url = None

            if not text_content and not image_file:
                flash('Please provide either text or an image', 'error')
                return redirect(request.url)

            if image_file and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                save_path = os.path.join(upload_dir, filename)
                image_file.save(save_path)
                image_url = url_for('static', filename=f'uploads/{filename}')
            
            # Create the post with the current user's username
            new_post = Content(
                username=username,
                text=text_content, 
                image=image_url, 
                category=category
            )
            
            db.session.add(new_post)
            db.session.commit()
            flash('Post created successfully!', 'success')
            
            # AJAX response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(new_post.to_dict())
                
            return redirect(url_for('main.index'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in upload: {str(e)}", exc_info=True)
            flash(f'Error creating post: {str(e)}', 'error')
            return redirect(request.url)

    # GET: load category list for dropdown
    try:
        categories = [c[0] for c in db.session.query(Category.name).distinct().all()]
        return render_template('upload.html', categories=categories)
    except Exception as e:
        current_app.logger.error(f"Error loading categories: {str(e)}", exc_info=True)
        return render_template('upload.html', categories=['General'])


@main.route('/categories', methods=['GET', 'POST'])
def handle_categories():
    """Handle getting and creating categories."""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        # Switch to the user's database
        current_app.switch_user_db(username)
        
        if request.method == 'POST':
            # Handle category creation
            data = request.get_json()
            if not data or 'name' not in data:
                return jsonify({'error': 'Category name is required'}), 400
                
            category_name = data['name'].strip()
            if not category_name:
                return jsonify({'error': 'Category name cannot be empty'}), 400
                
            # Check if category already exists
            existing = db.session.query(Content).filter_by(category=category_name).first()
            if existing:
                return jsonify({'error': 'Category already exists'}), 400
                
            # Return success without actually creating a category in the database
            # since we're using a simple string field for categories
            return jsonify({'message': 'Category added successfully', 'name': category_name}), 201
        
        # GET request - return all categories
        # Initialize Content with username to ensure correct table
        Content(username=username)
        
        # Get unique categories from the database
        categories = db.session.query(Content.category).distinct().all()
        # Flatten the list of tuples and filter out None values
        categories = [c[0] for c in categories if c[0]]
        
        # Add some default categories if none exist
        if not categories:
            categories = ['General', 'News', 'Entertainment', 'Sports', 'Technology', 'Science', 'Health']
            
        return jsonify(categories)
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in categories endpoint: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to process request'}), 500


@main.route('/get_posts')
def get_posts():
    """Get posts for the feed from static JSON file."""
    offset = request.args.get('offset', 0, type=int)
    limit = request.args.get('limit', 5, type=int)  # Default to 5 posts
    category = request.args.get('category')
    username = session.get('username')

    if not username:
        return jsonify({'error': 'Not logged in'}), 401

    try:
        current_app.logger.info(f"Getting posts for user: {username}")
        
        # Load posts from JSON file in the data directory
        with open(os.path.join(current_app.root_path, 'data', 'posts.json')) as f:
            data = json.load(f)
            posts = data.get('posts', [])
        
        # Filter by category if specified
        if category and category.lower() != 'all':
            posts = [p for p in posts if p.get('category', '').lower() == category.lower()]
        
        # Get total count for pagination
        total = len(posts)
        
        # Apply pagination
        paginated_posts = posts[offset:offset + limit]
        
        # Update view counts (in-memory only for this example)
        for post in paginated_posts:
            post['views'] = post.get('views', 0) + 1
            post['last_viewed'] = datetime.utcnow().isoformat()
        
        current_app.logger.info(f"Returning {len(paginated_posts)} posts")
        
        return jsonify({
            'posts': paginated_posts,
            'total': total,
            'offset': offset,
            'limit': limit,
            'has_more': (offset + len(paginated_posts)) < total
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_posts: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to fetch posts', 'details': str(e)}), 500


@main.route('/posts/<int:post_id>/view_time', methods=['POST'])
def track_view_time(post_id):
    """Track how long a post was viewed."""
    try:
        username = session.get('username')
        if not username:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
            
        # Since we're using static data, just log the view time
        data = request.get_json(silent=True) or {}
        view_time = float(data.get('view_time', 1))
        
        current_app.logger.debug(
            f"Tracked view time for post {post_id}: "
            f"{view_time:.2f} seconds (static data, not saved)"
        )
        
        return jsonify({
            'status': 'success',
            'post_id': post_id,
            'views': 1,  # Dummy value since we're not persisting
            'total_view_time': view_time,
            'last_viewed': datetime.utcnow().isoformat()
        })
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error tracking view time for post {post_id}: {str(e)}",
            exc_info=True
        )
        return jsonify({
            'status': 'error',
            'message': 'Failed to track view time',
            'error': str(e)
        }), 500
    finally:
        # Always ensure the session is removed to prevent connection leaks
        try:
            db.session.remove()
        except Exception as e:
            current_app.logger.warning(f"Error removing session: {str(e)}")


@main.route('/posts/<int:post_id>/rate', methods=['POST'])
def rate_post(post_id):
    """
    Rate a post with either like/dislike or numeric rating.
    
    Expected JSON payload:
    - For like/dislike: {'rating': 'like'|'dislike'}
    - For numeric rating: {'value': 1-5, 'type': 'rating'}
    """
    try:
        username = session.get('username')
        if not username:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
            
        # Load posts from JSON file
        posts_file = os.path.join(current_app.root_path, 'data', 'posts.json')
        try:
            with open(posts_file, 'r') as f:
                data = json.load(f)
                posts = data.get('posts', [])
        except (json.JSONDecodeError, FileNotFoundError):
            # If file doesn't exist or is invalid, start with empty posts
            posts = []
            
        # Find the post by ID
        post = next((p for p in posts if p.get('id') == post_id), None)
        if not post:
            return jsonify({'status': 'error', 'message': 'Post not found'}), 404
            
        # Get JSON data from request
        data = request.get_json() or {}
        
        # Handle like/dislike rating
        if 'rating' in data and data['rating'] in ['like', 'dislike']:
            if data['rating'] == 'like':
                post['likes'] = (post.get('likes', 0) or 0) + 1
            else:
                post['dislikes'] = (post.get('dislikes', 0) or 0) + 1
            
            # Save the updated posts back to the file
            with open(posts_file, 'w') as f:
                json.dump({'posts': posts}, f, indent=2)
            
            # Log the interaction if user_logger is available
            try:
                if hasattr(user_logger, 'log_rating'):
                    if not hasattr(user_logger, 'participant_id') or not user_logger.participant_id:
                        if hasattr(user_logger, 'init_participant'):
                            user_logger.init_participant(username)
                    user_logger.log_rating(post_id, 1 if data['rating'] == 'like' else -1, 'like')
            except Exception as e:
                current_app.logger.error(f"Error logging rating: {str(e)}", exc_info=True)
            
            return jsonify({
                'status': 'success',
                'post_id': post_id,
                'likes': post['likes'],
                'dislikes': post['dislikes']
            })
            
        # Handle numeric rating (1-5)
        elif 'value' in data and isinstance(data.get('value'), int) and 1 <= data['value'] <= 5:
            rating = data['value']
            rating_type = data.get('type', 'rating')
            
            # Update post ratings
            post['rating_total'] = (post.get('rating_total', 0) or 0) + rating
            post['rating_count'] = (post.get('rating_count', 0) or 0) + 1
            
            # Save the updated posts back to the file
            with open(posts_file, 'w') as f:
                json.dump({'posts': posts}, f, indent=2)
            
            # Log the rating event if user_logger is available
            try:
                if hasattr(user_logger, 'log_rating'):
                    if not hasattr(user_logger, 'participant_id') or not user_logger.participant_id:
                        if hasattr(user_logger, 'init_participant'):
                            user_logger.init_participant(username)
                    user_logger.log_rating(post_id, rating, rating_type)
            except Exception as e:
                current_app.logger.error(f"Error logging rating: {str(e)}", exc_info=True)
            
            return jsonify({
                'status': 'success',
                'post_id': post_id,
                'rating': rating,
                'average_rating': post['rating_total'] / post['rating_count'] if post.get('rating_count') else 0,
                'rating_count': post.get('rating_count', 0)
            })
        else:
            return jsonify({'status': 'error', 'message': 'Invalid rating format'}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error in rate_post: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Failed to process rating'}), 500


@main.route('/categories', methods=['GET'])
def get_categories():
    """Get all available categories."""
    try:
        username = session.get('username')
        if not username:
            return jsonify([])
            
        # Switch to the user's database
        current_app.switch_user_db(username)
        
        # Initialize Content with username to ensure correct table
        Content(username=username)
        
        # Get unique categories from the database
        categories = db.session.query(Content.category).distinct().all()
        # Flatten the list of tuples and filter out None values
        categories = [c[0] for c in categories if c[0]]
        
        # Add some default categories if none exist
        if not categories:
            categories = ['General', 'News', 'Entertainment', 'Sports', 'Technology', 'Science', 'Health']
            
        return jsonify(categories)
    except Exception as e:
        current_app.logger.error(f"Error fetching categories: {str(e)}", exc_info=True)
        # Return default categories on error
        return jsonify(['General', 'News', 'Entertainment', 'Sports', 'Technology', 'Science', 'Health'])


def update_user_preference(category, rating_value=None, is_positive=None):
    """
    Update user preferences for a specific category based on their ratings.
    
    Args:
        category (str): The category to update preferences for
        rating_value (int, optional): The rating value (1-5)
        is_positive (bool, optional): Whether the interaction was positive
    
    Returns:
        bool: True if preferences were updated, False otherwise
    """
    try:
        username = session.get('username')
        if not username:
            current_app.logger.warning("Cannot update preferences: No user in session")
            return False
            
        # Switch to the user's database
        current_app.switch_user_db(username)
        
        # If rating_value is not provided, try to get it from the request
        if rating_value is None:
            data = request.get_json(silent=True) or {}
            rating_value = data.get('rating')
            is_positive = data.get('is_positive', rating_value and rating_value >= 3) if is_positive is None else is_positive
        
        # If we still don't have a rating value, we can't update preferences
        if rating_value is None and is_positive is None:
            current_app.logger.warning("No rating value or positivity indicator provided")
            return False
            
        # Log the preference update
        current_app.logger.info(f"Updating preferences for user {username} in category {category}: "
                               f"rating={rating_value}, is_positive={is_positive}")
        
        # Here you would update the user's preferences in the database
        # For now, we'll just log it
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error updating user preferences: {str(e)}", exc_info=True)
        return False


@main.route('/user/preferences/<category>', methods=['POST'])
def update_user_preference_endpoint(category):
    """
    Update user preferences for a specific category based on their ratings.
    """
    session_id = request.cookies.get('session_id', '')
    if not session_id:
        return jsonify({"error": "No session ID"}), 400
    
    data = request.get_json(force=True)
    rating = data.get('rating')
    is_positive = data.get('is_positive', False)
    
    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({"error": "Invalid rating"}), 400
    
    # Get or create user preference
    pref = UserPreference.query.filter_by(session_id=session_id, category=category).first()
    if not pref:
        pref = UserPreference(session_id=session_id, category=category)
        db.session.add(pref)
    
    # Update preference
    pref.update_preference(rating, is_positive)
    db.session.commit()
    
    return jsonify(pref.to_dict()), 200
    db.session.commit()
    return jsonify({
        "average_rating": post.average_rating,
        "rating_count": post.rating_count
    }), 200


@main.route('/posts/reorder', methods=['POST'])
def reorder_posts():
    """Save manual post order."""
    data = request.get_json(force=True)
    order = data.get('order', [])
    category = data.get('category')
    key = f"order:{category or 'all'}"
    setattr(flask_session, key, order)
    return jsonify({"status":"ok"}), 200


@main.route('/debug_posts')
def debug_posts():
    all_posts = Content.query.all()
    return jsonify([p.to_dict() for p in all_posts])


def generate_texts(category, count, examples=None):
    """Generate example texts for the given category with rich, engaging content."""
    import random
    from faker import Faker
    
    fake = Faker()
    
    # Define more detailed content templates
    content_templates = {
        'Fun': [
            "Just had the most amazing experience {activity}! {emoji} Has anyone else tried this? #FunTimes #Adventure",
            "Laughing so hard at this {funny_thing}! {emoji} What's the funniest thing you've seen today? #LOL #FunnyMoments",
            "{emoji} {funny_quote} {emoji} This made my day! What's making you smile today? #GoodVibes",
            "Just discovered {cool_thing} and it's absolutely {positive_adj}! Who else is a fan? #NewDiscovery #Exciting"
        ],
        'News': [
            "{emoji} BREAKING: {headline} More details to follow. #BreakingNews #LatestUpdates",
            "{headline} - What are your thoughts on this development? #CurrentEvents #InTheNews",
            "Interesting analysis on {topic}. Do you agree with these perspectives? #NewsAnalysis #InformedOpinion",
            "{emoji} Just in: {headline} This could have significant implications. #NewsUpdate #StayInformed"
        ],
        'Education': [
            "Fascinating fact about {topic}: {fact} #DidYouKnow #LearningEveryday",
            "{emoji} Today I learned about {topic}. Here's what's interesting: {fact} #KnowledgeIsPower #ContinuousLearning",
            "Educational insight: {insight} What are your thoughts on this? #LifelongLearning #EducationMatters",
            "Breaking down complex concepts: {concept} explained in simple terms. #Learning #EducationForAll"
        ],
        'General': [
            "{emoji} {thought} What's on your mind today? #Thoughts #Discussion",
            "Sharing this because {reason}. What do you think? #SharingIsCaring #Community",
            "{question} I'd love to hear your perspective! #Discussion #CommunityEngagement",
            "{emoji} {observation} Has anyone else noticed this? #Observations #CommunityThoughts"
        ]
    }
    
    # Get the appropriate templates for the category
    templates = content_templates.get(category, content_templates['General'])
    
    # Generate content using the templates
    generated_texts = []
    for _ in range(count):
        template = random.choice(templates)
        
        # Prepare dynamic content
        replacements = {
            '{activity}': random.choice(['hiking', 'trying new food', 'traveling', 'exploring the city', 'learning something new']),
            '{emoji}': random.choice(['😊', '🌟', '🎉', '💡', '👀', '🤔', '🎯', '✨', '🔥', '📚']),
            '{funny_thing}': random.choice(['meme', 'video', 'story', 'situation', 'conversation']),
            '{funny_quote}': fake.sentence(),
            '{cool_thing}': random.choice(['this new app', 'this book', 'this podcast', 'this technique', 'this place']),
            '{positive_adj}': random.choice(['amazing', 'incredible', 'mind-blowing', 'fantastic', 'wonderful']),
            '{headline}': fake.sentence(nb_words=8).capitalize(),
            '{topic}': random.choice(['science', 'technology', 'history', 'art', 'culture', 'society']),
            '{fact}': fake.sentence(nb_words=12),
            '{insight}': fake.paragraph(nb_sentences=2),
            '{concept}': random.choice(['quantum physics', 'blockchain', 'AI', 'climate change', 'economic theory']),
            '{thought}': fake.sentence(nb_words=8).capitalize(),
            '{reason}': random.choice(['it made me think', 'I found it inspiring', "it's important to discuss", 'I value your opinions']),
            '{question}': fake.sentence(nb_words=8).capitalize() + '?',
            '{observation}': fake.sentence(nb_words=10).capitalize()
        }
        
        # Replace placeholders in the template
        text = template
        for key, value in replacements.items():
            text = text.replace(key, value)
            
        # Ensure the text is not too short
        if len(text.split()) < 5:  # If too short, add more content
            text += ' ' + fake.sentence()
            
        generated_texts.append(text)
    
    # If we have examples, mix them in with the generated content
    if examples and len(examples) > 0:
        # Take up to half the count from examples
        num_from_examples = min(len(examples), count // 2)
        generated_texts = generated_texts[:(count - num_from_examples)]
        generated_texts.extend(random.sample(examples, min(num_from_examples, len(examples))))
    
    # Ensure we return exactly the requested count
    return generated_texts[:count]

@main.route('/generate', methods=['POST'])
def generate_posts():
    try:
        # Get data from JSON body or form data
        if request.is_json:
            data = request.get_json(force=True)
        else:
            data = request.form
            
        category = data.get('category')
        try:
            count = int(data.get('count', 3))
        except (ValueError, TypeError):
            count = 3
        
        current_app.logger.info(f"Generating {count} posts for category: {category}")
        
        # Get examples if they exist
        q = Content.query
        if category:
            q = q.filter_by(category=category)
        
        # Get top-rated posts or any posts if none are rated
        examples = (
            q.filter(Content.rating_count > 0)
             .order_by((Content.rating_total/Content.rating_count).desc())
             .limit(3).all()
        )
        
        # If no rated posts, fall back to any posts
        if not examples:
            examples = q.limit(3).all()
        
        example_texts = [p.text for p in examples if p.text]
        
        # Generate new posts
        new_texts = generate_texts(category, count, examples=example_texts)
        
        if not new_texts:
            current_app.logger.error(f"Failed to generate any posts for category: {category}")
            return jsonify({"error": "Failed to generate posts"}), 500

        new_posts = []
        # Try to get username from session first, then from request data
        username = session.get('username') or data.get('username')
        if not username:
            current_app.logger.error("No username in session or request data when generating posts")
            return jsonify({'error': 'No username in session or request data'}), 400
            
        # Ensure we're using the correct database for this user
        current_app.switch_user_db(username)
        
        # Set the username in the session for future requests
        session['username'] = username
        session.modified = True
            
        for txt in new_texts:
            if txt:  # Only add non-empty posts
                try:
                    p = Content(
                        username=username, 
                        text=txt, 
                        category=category or 'General'
                    )
                    db.session.add(p)
                    new_posts.append(p)
                except Exception as e:
                    current_app.logger.error(f"Error creating post: {str(e)}", exc_info=True)
                    continue
        
        try:
            db.session.commit()
            current_app.logger.info(f"Successfully added {len(new_posts)} new posts")
            return jsonify([p.to_dict() for p in new_posts]), 201
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error when saving posts: {str(e)}", exc_info=True)
            return jsonify({"error": "Database error when saving posts"}), 500
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error in generate_posts: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500


@main.route('/dashboard')
def dashboard():
    """Show the dashboard with stop button."""
    # Debug: Log all session data
    current_app.logger.info(f"Session data: {dict(session)}")
    current_app.logger.info(f"Session ID from session: {session.get('user_session_id')}")
    
    user_session_id = session.get('user_session_id')
    if not user_session_id:
        current_app.logger.warning("No user_session_id in session, redirecting to start")
        return redirect(url_for('main.start'))

    user_session = UserSession.query.get(user_session_id)
    if not user_session:
        current_app.logger.warning(f"No user session found for ID: {user_session_id}")
        return redirect(url_for('main.start'))
        
    current_app.logger.info(f"Found user session: {user_session.id} for user: {user_session.username}")

    # recent interactions (last 20)
    events = []
    for p in Content.query.order_by(Content.created_at.desc()).limit(20):
        if p.rating_count > 0:
            events.append({
                'time': p.created_at.isoformat(),
                'type': 'rating',
                'category': p.category,
                'rating': p.average_rating
            })
    
    # trends by category
    cats = db.session.query(
        Content.category,
        db.func.avg(Content.rating_total/Content.rating_count).label('avg')
    ).filter(Content.rating_count>0).group_by(Content.category).all()
    trends = [{"category":c, "avg":float(a)} for c,a in cats]

    weights = getattr(flask_session, 'weights', DEFAULT_WEIGHTS)
    username = getattr(flask_session, 'username', '')
    return render_template('dashboard.html',
        events=json.dumps(events),
        trends=json.dumps(trends),
        weights=weights,
        username=username
    )


@main.route('/post-questionnaire', methods=['POST'])
def submit_post_questionnaire():
    return post_questionnaire()


@main.route('/dashboard/settings', methods=['POST'])
def dashboard_settings():
    data = request.get_json(force=True)
    weights = {k: float(data[k]) for k in DEFAULT_WEIGHTS.keys() if k in data}
    flask_session.weights = weights
    user_logger.log_action('weight_change', category=None)
    return jsonify({"status": "ok", "weights": flask_session.weights}), 200



