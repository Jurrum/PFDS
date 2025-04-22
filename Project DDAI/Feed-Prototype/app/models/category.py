from app import db

class Category(db.Model):
    __tablename__ = 'categories'

    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f'<Category {self.name!r}>'

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }
