# app/models/content.py

from datetime import datetime
from app import db

class Content(db.Model):
    __tablename__ = 'contents'

    id            = db.Column(db.Integer, primary_key=True)
    text          = db.Column(db.Text, nullable=True)
    image         = db.Column(db.String(256), nullable=True)
    likes         = db.Column(db.Integer, default=0, nullable=False)
    dislikes      = db.Column(db.Integer, default=0, nullable=False)
    shares        = db.Column(db.Integer, default=0, nullable=False)
    comments      = db.Column(db.Integer, default=0, nullable=False)
    category      = db.Column(db.String(50), default='General', nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    rating_total  = db.Column(db.Integer, default=0, nullable=False)
    rating_count  = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f'<Content id={self.id} category={self.category!r}>'

    @property
    def average_rating(self):
        return (self.rating_total / self.rating_count) if self.rating_count else None

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "image": self.image,
            "likes": self.likes,
            "dislikes": self.dislikes,
            "shares": self.shares,
            "comments": self.comments,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "rating_total": self.rating_total,
            "rating_count": self.rating_count,
            "average_rating": self.average_rating
        }
