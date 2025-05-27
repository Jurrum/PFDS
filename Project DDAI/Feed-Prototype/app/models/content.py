# app/models/content.py

from datetime import datetime
from app import db

class Content(db.Model):
    def __init__(self, username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__table_args__ = {'extend_existing': True}
        self.__tablename__ = f'contents_{username.lower()}'
        self.username = username

    id          = db.Column(db.Integer, primary_key=True)
    text        = db.Column(db.Text)
    image       = db.Column(db.String(256))
    category    = db.Column(db.String(64))
    likes       = db.Column(db.Integer, default=0)
    dislikes    = db.Column(db.Integer, default=0)
    shares      = db.Column(db.Integer, default=0)
    comments    = db.Column(db.Integer, default=0)
    rating_total = db.Column(db.Integer, default=0)
    rating_count = db.Column(db.Integer, default=0)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def ratings_table_name(self):
        """Return the name of the ratings table for this user."""
        return f'ratings_{self.username.lower()}'

    @property
    def user(self):
        """Get the user for this content."""
        return UserSession.query.filter_by(username=self.username).first()

    def __repr__(self):
        return f'<Content {self.id}>'

    @property
    def average_rating(self):
        """Return the average rating for this post."""
        return self.rating_total / self.rating_count if self.rating_count > 0 else 0

    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'image': self.image,
            'category': self.category,
            'likes': self.likes,
            'dislikes': self.dislikes,
            'shares': self.shares,
            'comments': self.comments,
            'rating': self.average_rating,
            'created_at': self.created_at.isoformat()
        }
