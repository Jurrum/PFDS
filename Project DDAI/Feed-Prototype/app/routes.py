# app/routes.py

import os
from flask import (
    Blueprint, render_template, request,
    jsonify, send_from_directory, url_for, current_app
)
from werkzeug.utils import secure_filename

from app import db
from app.models.content import Content

main = Blueprint('main', __name__)

# ——— Configuration ———
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ——— Routes ———

@main.route('/')
def home():
    """
    Render the home page; the client will fetch posts
    via JS from /get_posts (so we can do infinite scroll later).
    """
    return render_template('home.html')


@main.route('/upload', methods=['GET', 'POST'])
def upload():
    """
    GET: render a form allowing text/image/category input
    POST: save new Content row, return its JSON.
    """
    if request.method == 'POST':
        text_content = request.form.get('text', '').strip()
        category     = request.form.get('category', 'General').strip()
        image_file   = request.files.get('image')

        image_url = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            image_file.save(save_path)
            # Build a URL to serve it:
            image_url = url_for('main.uploaded_file', filename=filename)

        # create & persist
        new_post = Content(
            text     = text_content or None,
            image    = image_url,
            category = category or 'General'
        )
        db.session.add(new_post)
        db.session.commit()

        return jsonify(new_post.to_dict()), 201

    # GET: show form; you might want to pass existing categories for a dropdown
    distinct_cats = [row[0] for row in db.session.query(Content.category).distinct()]
    return render_template('upload.html', categories=distinct_cats)


@main.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve user‑uploaded images."""
    return send_from_directory(UPLOAD_FOLDER, filename)


@main.route('/get_posts')
def get_posts():
    """
    Return JSON list of posts.
    Optional query args:
      - category=Foo   → filter by category
      - limit=20&offset=0 for pagination/infinite scroll
    """
    # filtering
    q = Content.query
    cat = request.args.get('category')
    if cat:
        q = q.filter_by(category=cat)

    # pagination (for infinite scroll later)
    try:
        limit  = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
    except ValueError:
        limit, offset = 50, 0

    posts = q.offset(offset).limit(limit).all()

    # apply your scoring algorithm:
    def score(p):
        return (
            p.likes   * 2 +
            p.shares  * 3 +
            p.comments * 1.5 -
            p.dislikes * 1
        )
    posts.sort(key=score, reverse=True)

    return jsonify([p.to_dict() for p in posts])

# ─── app/routes.py (continuing below your /get_posts) ───

@main.route('/posts/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    """Increment likes for a post."""
    post = Content.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()
    return jsonify({"id": post.id, "likes": post.likes}), 200

@main.route('/posts/<int:post_id>/dislike', methods=['POST'])
def dislike_post(post_id):
    """Increment dislikes for a post."""
    post = Content.query.get_or_404(post_id)
    post.dislikes += 1
    db.session.commit()
    return jsonify({"id": post.id, "dislikes": post.dislikes}), 200

