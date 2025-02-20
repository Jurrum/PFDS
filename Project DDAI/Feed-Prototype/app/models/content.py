class Content:
    """Represents a social media post (text or image)."""

    def __init__(self, text=None, image=None):
        self.text = text
        self.image = image

    def to_dict(self):
        """Convert content to dictionary format."""
        return {"text": self.text, "image": self.image}
