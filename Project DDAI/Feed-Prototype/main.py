from app import create_app, db
from app.utils.user_logging import user_logger
from flask import session
import uuid

app = create_app()

@app.before_request
def before_request():
    """Initialize participant ID and logging."""
    if 'participant_id' not in session:
        session['participant_id'] = str(uuid.uuid4())[:8]
    user_logger.init_participant(session['participant_id'])

if __name__ == '__main__':
    app.run(debug=True)
