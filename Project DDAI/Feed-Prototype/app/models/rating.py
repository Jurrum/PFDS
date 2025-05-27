# app/models/rating.py

from datetime import datetime
from app import db

class Rating(db.Model):
    def __init__(self, username, content_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__table_args__ = {'extend_existing': True}
        self.__tablename__ = f'ratings_{username.lower()}'
        self.username = username
        self.content_id = content_id

    id          = db.Column(db.Integer, primary_key=True)
    session_id  = db.Column(db.String(64), nullable=False, index=True)
    content_id  = db.Column(db.Integer, nullable=False)
    value       = db.Column(db.Integer, nullable=False)  # 1–5
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def content_table_name(self):
        """Return the name of the content table for this user."""
        return f'contents_{self.username.lower()}'

    @property
    def content(self):
        """Get the related content."""
        return Content.query.filter_by(id=self.content_id).first()

    @content.setter
    def content(self, content):
        """Set the related content."""
        self.content_id = content.id

    def __repr__(self):
        return f'<Rating session={self.session_id!r} content={self.content_id} value={self.value}>'
