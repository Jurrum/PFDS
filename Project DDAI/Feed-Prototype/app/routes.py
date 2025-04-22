
import os
from uuid import uuid4
from flask import (
    Blueprint, render_template, request,
    jsonify, send_from_directory, url_for,
    redirect, session
)
from werkzeug.utils import secure_filename

from app import db
from app.models.content  import Content
from app.models.category import Category
from app.models.rating   import Rating

main = Blueprint('main', __name__)

# ——— Configuration ———
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER   = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ——— Routes ———

@main.route('/')
def home():
    """Render the home page; posts are fetched via JS."""
    return render_template('home.html')


from flask import redirect, url_for

@main.route('/upload', methods=['GET', 'POST'])
def upload():
    """
    GET:  render form with category dropdown
    POST: handle new post creation (text + optional image + category),
          returning JSON for AJAX or redirecting for regular form submits
    """
    if request.method == 'POST':
        text_content = request.form.get('text', '').strip() or None
        category     = request.form.get('category', 'General').strip() or 'General'
        image_file   = request.files.get('image')

        image_url = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            image_file.save(path)
            image_url = url_for('main.uploaded_file', filename=filename)

        new_post = Content(
            text     = text_content,
            image    = image_url,
            category = category
        )
        db.session.add(new_post)
        db.session.commit()

        # AJAX requests get JSON back
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(new_post.to_dict()), 201

        # regular form submits get redirected back to the feed
        return redirect(url_for('main.home'))

    # GET → load existing categories for the dropdown
    cats = Category.query.order_by(Category.name).all()
    category_names = [c.name for c in cats]
    return render_template('upload.html', categories=category_names)



@main.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve user‑uploaded images."""
    return send_from_directory(UPLOAD_FOLDER, filename)


@main.route('/get_posts')
def get_posts():
    """
    Return JSON list of posts, optionally filtered by category,
    and sorted by the recommendation scoring function.
    """
    q = Content.query
    cat = request.args.get('category')
    if cat:
        q = q.filter_by(category=cat)

    # simple pagination parameters (for future infinite scroll)
    try:
        limit  = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
    except ValueError:
        limit, offset = 50, 0

    posts = q.offset(offset).limit(limit).all()

    # scoring: 2*likes + 3*shares + 1.5*comments - 1*dislikes
    def score(p):
        return (p.likes * 2 + p.shares * 3 + p.comments * 1.5 - p.dislikes)

    posts.sort(key=score, reverse=True)
    return jsonify([p.to_dict() for p in posts])


@main.route('/posts/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    """Increment the like count for a given post."""
    post = Content.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()
    return jsonify({"id": post.id, "likes": post.likes}), 200


@main.route('/posts/<int:post_id>/dislike', methods=['POST'])
def dislike_post(post_id):
    """Increment the dislike count for a given post."""
    post = Content.query.get_or_404(post_id)
    post.dislikes += 1
    db.session.commit()
    return jsonify({"id": post.id, "dislikes": post.dislikes}), 200


@main.route('/categories', methods=['GET', 'POST'])
def categories():
    """
    GET  → list all categories
    POST → create a new category with JSON payload { "name": "<CategoryName>" }
    """
    if request.method == 'GET':
        cats = Category.query.order_by(Category.name).all()
        return jsonify([c.to_dict() for c in cats])

    # POST
    data = request.get_json(force=True)
    name = data.get('name', '').strip()
    if not name:
        return jsonify({"error": "Category name required"}), 400
    if Category.query.filter_by(name=name).first():
        return jsonify({"error": "Category already exists"}), 400

    new_cat = Category(name=name)
    db.session.add(new_cat)
    db.session.commit()
    return jsonify(new_cat.to_dict()), 201


@main.route('/posts/<int:post_id>/category', methods=['PUT'])
def update_post_category(post_id):
    """
    Change a post’s category
    Expects JSON payload: { "category_id": <id> }
    """
    post = Content.query.get_or_404(post_id)
    data = request.get_json(force=True)
    cid  = data.get('category_id')
    cat  = Category.query.get(cid)
    if not cat:
        return jsonify({"error": "Invalid category ID"}), 400

    post.category = cat.name
    db.session.commit()
    return jsonify(post.to_dict()), 200

@main.route('/posts/<int:post_id>/rate', methods=['POST'])
def rate_post(post_id):
    """Submit a 1–5 rating for a post."""
    post = Content.query.get_or_404(post_id)
    data = request.get_json(force=True)
    val  = data.get('value')
    if not isinstance(val, int) or val < 1 or val > 5:
        return jsonify({"error": "Rating must be an integer 1–5"}), 400

    post.rating_total += val
    post.rating_count += 1
    db.session.commit()

    return jsonify({
        "average_rating": post.average_rating,
        "rating_count": post.rating_count
    }), 200


@main.route('/debug_posts')
def debug_posts():
    """Return every post in the DB, unfiltered."""
    posts = Content.query.all()
    
    return jsonify([p.to_dict() for p in posts])

