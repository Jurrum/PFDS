import os
import json
from flask import Blueprint, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from app.models.content import Content

# Ensure uploads are saved in the correct directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get absolute path of current file
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")  # Set path relative to app directory
FEED_FILE = os.path.join(UPLOAD_FOLDER, 'feed_data.json')

main = Blueprint('main', __name__)

# Ensure `uploads/` folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Ensure `feed_data.json` file exists
if not os.path.exists(FEED_FILE):
    with open(FEED_FILE, 'w') as file:
        json.dump([], file)

# Load existing posts from JSON file
def load_feed_data():
    if os.path.exists(FEED_FILE):
        with open(FEED_FILE, 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return []  # If file is corrupted, reset it
    return []

feed_data = load_feed_data()


def save_feed_data():
    """Save feed data to a JSON file and flush it properly."""
    with open(FEED_FILE, 'w') as file:
        json.dump(feed_data, file, indent=4)
        file.flush()
        os.fsync(file.fileno())  # Ensure the data is written to disk


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


@main.route('/')
def home():
    """Render the home page with stored feed data."""
    return render_template('home.html', feed=feed_data)


@main.route('/upload', methods=['GET', 'POST'])
def upload():
    """Handles content upload form."""
    if request.method == 'POST':
        text_content = request.form.get('text', '').strip()
        image = request.files.get('image')

        filename = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            image.save(image_path)
            image_url = f"/uploads/{filename}"  # ✅ Use route-based path
        else:
            image_url = None

        new_content = Content(text=text_content, image=image_url)
        feed_data.append(new_content.to_dict())  # ✅ Save with correct path
        save_feed_data()

        return jsonify(new_content.to_dict())

    return render_template('upload.html')


@main.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded images from the uploads folder."""
    return send_from_directory(UPLOAD_FOLDER, filename)

@main.route('/get_posts')
def get_posts():
    """Returns all posts from the JSON file."""
    return jsonify(feed_data)
