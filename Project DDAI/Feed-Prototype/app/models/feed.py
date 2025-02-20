from app.models.content import Content

class Feed:
    """A feed that loads and stores different content items."""
    def __init__(self):
        self.contents = []

    def add_content(self, content: Content):
        """Adds content to the feed."""
        if isinstance(content, Content):
            self.contents.append(content)

    def get_all_content(self):
        """Returns all content items."""
        return self.contents
