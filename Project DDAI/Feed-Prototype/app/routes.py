# app/routes.py

import os
from flask import (
    Blueprint, render_template, request, jsonify,
    send_from_directory, url_for, redirect, session, current_app
)
from werkzeug.utils import secure_filename

from app import db
from app.models.content import Content
from app.models.category import Category
from app.utils.generation import generate_texts

main = Blueprint('main', __name__)

# ——— Configuration ———
BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER     = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

@main.route('/')
def home():
    return render_template('home.html')

@main.route('/upload', methods=['GET','POST'])
def upload():
    if request.method == 'POST':
        text    = request.form.get('text','').strip() or None
        category= request.form.get('category','General').strip() or 'General'
        imgfile = request.files.get('image')
        img_url = None
        if imgfile and allowed_file(imgfile.filename):
            fn   = secure_filename(imgfile.filename)
            path = os.path.join(UPLOAD_FOLDER, fn)
            imgfile.save(path)
            img_url = url_for('main.uploaded_file', filename=fn)

        post = Content(text=text, image=img_url, category=category)
        db.session.add(post)
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(post.to_dict()), 201
        return redirect(url_for('main.home'))

    cats = Category.query.order_by(Category.name).all()
    return render_template('upload.html',
        categories=[c.name for c in cats]
    )

@main.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@main.route('/get_posts')
def get_posts():
    q   = Content.query
    cat = request.args.get('category')
    if cat:
        q = q.filter_by(category=cat)

    try:
        limit  = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
    except ValueError:
        limit, offset = 50, 0

    posts = q.offset(offset).limit(limit).all()

    if offset == 0 and not posts:
        # seed empty feed
        ex_q = Content.query
        if cat:
            ex_q = ex_q.filter_by(category=cat)
        examples = (
            ex_q
            .filter(Content.rating_count > 0)
            .order_by((Content.rating_total/Content.rating_count).desc())
            .limit(3)
            .all()
        )
        example_texts = [p.text for p in examples if p.text]
        generated = generate_texts(cat, 5, examples=example_texts)
        for txt in generated:
            p = Content(text=txt, category=cat or 'General')
            db.session.add(p)
            posts.append(p)
        db.session.commit()

    def score(p):
        return p.likes*2 + p.shares*3 + p.comments*1.5 - p.dislikes
    posts.sort(key=score, reverse=True)

    # apply manual reorder from session
    order_key   = f"order:{cat or 'all'}"
    saved_order = session.get(order_key)
    if saved_order:
        id_map  = {p.id:p for p in posts}
        ordered = []
        for pid in saved_order:
            if pid in id_map:
                ordered.append(id_map.pop(pid))
        ordered.extend(id_map.values())
        posts = ordered

    return jsonify([p.to_dict() for p in posts])

@main.route('/posts/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    current_app.logger.debug(f"LIKE endpoint called for post {post_id}")
    post = Content.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()
    # return both counts
    return jsonify({
        "id": post.id,
        "likes": post.likes,
        "dislikes": post.dislikes
    }), 200

@main.route('/posts/<int:post_id>/dislike', methods=['POST'])
def dislike_post(post_id):
    current_app.logger.debug(f"DISLIKE endpoint called for post {post_id}")
    post = Content.query.get_or_404(post_id)
    post.dislikes += 1
    db.session.commit()
    return jsonify({
        "id": post.id,
        "likes": post.likes,
        "dislikes": post.dislikes
    }), 200

@main.route('/categories', methods=['GET','POST'])
def categories():
    if request.method == 'GET':
        cats = Category.query.order_by(Category.name).all()
        return jsonify([c.to_dict() for c in cats])

    data = request.get_json(force=True)
    name = data.get('name','').strip()
    if not name:
        return jsonify({"error":"Category required"}),400
    if Category.query.filter_by(name=name).first():
        return jsonify({"error":"Already exists"}),400

    c = Category(name=name)
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()),201

@main.route('/posts/<int:post_id>/category', methods=['PUT'])
def update_post_category(post_id):
    post = Content.query.get_or_404(post_id)
    cid  = request.get_json(force=True).get('category_id')
    cat  = Category.query.get(cid)
    if not cat:
        return jsonify({"error":"Invalid category"}),400
    post.category = cat.name
    db.session.commit()
    return jsonify(post.to_dict()),200

@main.route('/posts/<int:post_id>/rate', methods=['POST'])
def rate_post(post_id):
    post = Content.query.get_or_404(post_id)
    val  = request.get_json(force=True).get('value')
    if not isinstance(val,int) or not (1<=val<=5):
        return jsonify({"error":"Rating must be 1–5"}),400
    post.rating_total += val
    post.rating_count += 1
    db.session.commit()
    return jsonify({
        "average_rating": post.average_rating,
        "rating_count": post.rating_count
    }),200

@main.route('/posts/reorder', methods=['POST'])
def reorder_posts():
    data     = request.get_json(force=True)
    order    = data.get('order',[])
    category = data.get('category')
    key      = f"order:{category or 'all'}"
    session[key] = order
    return jsonify({"status":"ok"}),200

@main.route('/generate', methods=['POST'])
def generate_posts():
    data     = request.get_json(force=True)
    category = data.get('category',None)
    count    = int(data.get('count',3))

    q = Content.query
    if category:
        q = q.filter_by(category=category)
    examples = (
        q
        .filter(Content.rating_count>0)
        .order_by((Content.rating_total/Content.rating_count).desc())
        .limit(3)
        .all()
    )
    example_texts = [p.text for p in examples if p.text]
    new_texts = generate_texts(category, count, examples=example_texts)

    new_posts = []
    for txt in new_texts:
        p = Content(text=txt, category=category or 'General')
        db.session.add(p)
        new_posts.append(p)
    db.session.commit()

    return jsonify([p.to_dict() for p in new_posts]),201

@main.route('/debug_posts')
def debug_posts():
    all_posts = Content.query.all()
    return jsonify([p.to_dict() for p in all_posts])
