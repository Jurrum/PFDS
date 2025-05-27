import os
import json
from flask import (
    Blueprint, render_template, request,
    jsonify, send_from_directory,
    url_for, redirect, session as flask_session, current_app
)
from werkzeug.utils import secure_filename
from app import db
from app.models.content import Content
from app.models.category import Category
from app.models.rating import Rating
from app.models.session import UserSession
from app.utils.generation import generate_texts
from app.utils.user_logging import user_logger
from datetime import datetime

main = Blueprint('main', __name__)

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


# ——— Routes ———
@main.route('/start')
def start():
    """Show the start page with instructions."""
    return render_template('start.html')

@main.route('/start-session', methods=['POST'])
def start_session():
    """Start a new user session."""
    # Get username from form data
    username = request.form.get('username')
    
    if not username:
        return redirect(url_for('main.start'))

    # Check if username already exists
    existing_session = UserSession.query.filter_by(username=username).first()
    if existing_session:
        # If session exists but is not completed, redirect to home
        if not existing_session.completed:
            flask_session['user_session_id'] = existing_session.id
            flask_session['username'] = username
            return redirect(url_for('main.index'))
        # If session exists and is completed, redirect back to start
        return redirect(url_for('main.start'))

    # Create new session
    user_session = UserSession(username=username)
    db.session.add(user_session)
    db.session.commit()

    # Store session ID in Flask session
    flask_session['user_session_id'] = user_session.id
    flask_session['username'] = username

    # Initialize logging
    user_logger.init_participant(username)
    
    # Start interaction timer
    flask_session['interaction_start'] = datetime.utcnow()

    # Redirect to home page
    return redirect(url_for('main.index'))



@main.route('/')
def index():
    """Render the home page; posts fetched via JS."""
    return render_template('home.html')


@main.route('/upload', methods=['GET', 'POST'])
def upload():
    """
    GET: render upload form
    POST: save new post (text + image + category)
    """
    if request.method == 'POST':
        text_content = request.form.get('text', '').strip() or None
        category     = request.form.get('category', 'General').strip() or 'General'
        image_file   = request.files.get('image')

        image_url = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            image_file.save(save_path)
            image_url = url_for('main.uploaded_file', filename=filename)

        new_post = Content(text=text_content, image=image_url, category=category)
        db.session.add(new_post)
        db.session.commit()

        # AJAX response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(new_post.to_dict()), 201

        return redirect(url_for('main.home'))

    # GET: load category list for dropdown
    cats = Category.query.order_by(Category.name).all()
    return render_template('upload.html', categories=[c.name for c in cats])


@main.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded images."""
    return send_from_directory(UPLOAD_FOLDER, filename)


@main.route('/get_posts')
def get_posts():
    """
    Return JSON posts, filtered by category, paginated,
    scored by dynamic weights, and session‐ordered.
    """
    q = Content.query
    cat = request.args.get('category')
    if cat:
        q = q.filter_by(category=cat)

    try:
        limit  = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
    except ValueError:
        limit, offset = 50, 0

    # Get posts
    posts = q.offset(offset).limit(limit).all()
    
    # Apply saved manual order
    order_key = f"order:{cat or 'all'}"
    saved = flask_session.get(order_key)
    if saved:
        id_map = {p.id: p for p in posts}
        ordered = []
        for pid in saved:
            if pid in id_map:
                ordered.append(id_map.pop(pid))
        ordered.extend(id_map.values())
        posts = ordered
    else:
        # Sort posts by creation date (newest first) if no manual order
        posts.sort(key=lambda p: p.created_at, reverse=True)

    # if no posts on first page, generate some
    if offset == 0 and not posts:
        # gather high‐rated examples
        ex_q = Content.query.filter(Content.rating_count > 0)
        if cat:
            ex_q = ex_q.filter_by(category=cat)
        examples = ex_q.order_by((Content.rating_total/Content.rating_count).desc()).limit(3).all()
        example_texts = [p.text for p in examples if p.text]
        generated = generate_texts(cat, 5, examples=example_texts)
        for txt in generated:
            p = Content(text=txt, category=cat or 'General')
            db.session.add(p)
            posts.append(p)
        db.session.commit()

    # dynamic scoring
    weights = flask_session.get('weights', DEFAULT_WEIGHTS)
    def score(p):
        return (
            p.likes    * weights['likes'] +
            p.shares   * weights['shares'] +
            p.comments * weights['comments'] -
            p.dislikes * weights['dislikes']
        )
    posts.sort(key=score, reverse=True)

    return jsonify([p.to_dict() for p in posts])


@main.route('/posts/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    post = Content.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()
    return jsonify({"id": post.id, "likes": post.likes}), 200


@main.route('/posts/<int:post_id>/dislike', methods=['POST'])
def dislike_post(post_id):
    post = Content.query.get_or_404(post_id)
    post.dislikes += 1
    db.session.commit()
    return jsonify({"id": post.id, "dislikes": post.dislikes}), 200


@main.route('/categories', methods=['GET', 'POST'])
def categories():
    if request.method == 'GET':
        cats = Category.query.order_by(Category.name).all()
        return jsonify([c.to_dict() for c in cats])

    data = request.get_json(force=True)
    name = data.get('name','').strip()
    if not name:
        return jsonify({"error":"Category name required"}), 400
    if Category.query.filter_by(name=name).first():
        return jsonify({"error":"Already exists"}), 400
    new_cat = Category(name=name)
    db.session.add(new_cat)
    db.session.commit()
    return jsonify(new_cat.to_dict()), 201


@main.route('/posts/<int:post_id>/category', methods=['PUT'])
def update_post_category(post_id):
    post = Content.query.get_or_404(post_id)
    data = request.get_json(force=True)
    cid = data.get('category_id')
    cat = Category.query.get(cid)
    if not cat:
        return jsonify({"error":"Invalid category"}), 400
    post.category = cat.name
    db.session.commit()
    user_logger.log_interaction(post_id, 'category_update')
    return jsonify(post.to_dict()), 200


@main.route('/posts/<int:post_id>/rate', methods=['POST'])
def rate_post(post_id):
    post = Content.query.get_or_404(post_id)
    data = request.get_json(force=True)
    val = data.get('value')
    if not isinstance(val, int) or not (1 <= val <= 5):
        return jsonify({"error":"Rating must be 1–5"}), 400
    
    # Update post ratings
    post.rating_total += val
    post.rating_count += 1
    
    # Log the rating event
    user_logger.log_rating(post_id, val, data.get('type', 'like'))
    
    # Commit the rating update
    db.session.commit()
    
    return jsonify({"id": post.id, "rating": post.rating_total/post.rating_count}), 200

@main.route('/user/preferences/<category>', methods=['POST'])
def update_user_preference(category):
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
    flask_session[key] = order
    return jsonify({"status":"ok"}), 200


@main.route('/debug_posts')
def debug_posts():
    all_posts = Content.query.all()
    return jsonify([p.to_dict() for p in all_posts])


@main.route('/generate', methods=['POST'])
def generate_posts():
    try:
        data = request.get_json(force=True)
        category = data.get('category', None)
        count = int(data.get('count', 3))
        
        print(f"Generating {count} posts for category: {category}")
        
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
        
        if not new_texts or len(new_texts) < count:
            print(f"Generated {len(new_texts) if new_texts else 0} posts, expected {count}")
            return jsonify({"error": "Failed to generate enough posts"}), 500

        new_posts = []
        for txt in new_texts:
            if txt:  # Only add non-empty posts
                p = Content(text=txt, category=category or 'General')
                db.session.add(p)
                new_posts.append(p)
        
        if not new_posts:
            print("No valid posts generated")
            return jsonify({"error": "Failed to generate valid posts"}), 500
        
        db.session.commit()
        print(f"Successfully added {len(new_posts)} new posts")
        return jsonify([p.to_dict() for p in new_posts]), 201
    
    except Exception as e:
        db.session.rollback()
        print(f"Error in generate_posts route: {str(e)}")
        return jsonify({"error": "Failed to generate posts"}), 500


@main.route('/dashboard')
def dashboard():
    """Show the dashboard with stop button."""
    if 'user_session_id' not in flask_session:
        return redirect(url_for('main.start'))

    user_session = UserSession.query.get(flask_session['user_session_id'])
    if not user_session:
        return redirect(url_for('main.start'))

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

    weights = flask_session.get('weights', DEFAULT_WEIGHTS)
    return render_template('dashboard.html',
        events=json.dumps(events),
        trends=json.dumps(trends),
        weights=weights,
        username=flask_session['username']
    )


@main.route('/dashboard/settings', methods=['POST'])
def dashboard_settings():
    data = request.get_json(force=True)
    weights = {k: float(data[k]) for k in DEFAULT_WEIGHTS.keys() if k in data}
    flask_session['weights'] = weights
    user_logger.log_action('weight_change', category=None)
    return jsonify({"status": "ok", "weights": flask_session['weights']}), 200


@main.route('/end-session')
def end_session():
    """End the current session and save data."""
    if 'user_session_id' not in flask_session:
        return redirect(url_for('main.start'))

    user_session = UserSession.query.get(flask_session['user_session_id'])
    if not user_session:
        return redirect(url_for('main.start'))

    try:
        # Calculate total interactions
        log_file = os.path.join(
            current_app.root_path,
            'logs',
            f'participant_{flask_session.get("username", "unknown")}.csv'
        )
        total_interactions = 0
        if os.path.exists(log_file):
            with open(log_file) as f:
                total_interactions = sum(1 for line in f) - 1  # subtract header

        # Update session data
        user_session.end_time = datetime.utcnow()
        user_session.completed = True
        user_session.total_interactions = total_interactions
        db.session.commit()

        # Save interaction data to CSV
        user_logger.save_session_data(user_session.username)

        # Clear Flask session
        flask_session.clear()

        return render_template('end.html', username=user_session.username)

    except Exception as e:
        print(f"Error ending session: {str(e)}")
        flask_session.clear()
        return redirect(url_for('main.start'))
