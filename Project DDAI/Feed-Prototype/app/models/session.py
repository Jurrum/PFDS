from datetime import datetime
from app import db

class UserSession(db.Model):
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    total_interactions = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<UserSession {self.username}>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_interactions': self.total_interactions,
            'completed': self.completed
        }
