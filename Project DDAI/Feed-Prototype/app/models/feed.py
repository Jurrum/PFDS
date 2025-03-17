from flask import Flask, jsonify, request
from app.models.content import Content

app = Flask(__name__)
feed = []  # Temporary storage for posts

@app.route('/upload', methods=['POST'])
def upload():
    """Handles new content upload."""
    data = request.form
    new_content = Content(
        id=len(feed) + 1,
        text=data.get('text', ''),
        image=data.get('image', None),
        likes=int(data.get('likes', 0)),
        shares=int(data.get('shares', 0)),
        comments=int(data.get('comments', 0)),
        category=data.get('category', 'General'),
        created_at=data.get('created_at', None)
    )
    feed.append(new_content)
    return jsonify({"message": "Post added successfully!"})

@app.route('/get_posts', methods=['GET'])
def get_posts():
    """Fetches all posts sorted by recommendation algorithm."""
    sorted_feed = recommend_posts(feed)
    return jsonify([content.to_dict() for content in sorted_feed])

def recommend_posts(posts):
    """More sophisticated recommendation algorithm."""
    return sorted(posts, key=lambda post: (post.likes * 2 + post.shares * 3 + post.comments * 1.5), reverse=True)

if __name__ == '__main__':
    app.run(debug=True)
