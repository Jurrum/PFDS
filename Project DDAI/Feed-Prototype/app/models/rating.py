# app/models/rating.py

from datetime import datetime
from app import db

class Rating(db.Model):
    __tablename__ = 'ratings'

    id          = db.Column(db.Integer, primary_key=True)
    session_id  = db.Column(db.String(64), nullable=False, index=True)
    content_id  = db.Column(db.Integer, db.ForeignKey('contents.id'), nullable=False)
    value       = db.Column(db.Integer, nullable=False)  # 1–5
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    content = db.relationship('Content', backref=db.backref('ratings', cascade='all,delete-orphan'))

    def __repr__(self):
        return f'<Rating session={self.session_id!r} content={self.content_id} value={self.value}>'
