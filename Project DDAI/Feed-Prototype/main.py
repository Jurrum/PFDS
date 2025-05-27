from app import create_app, db
from app.utils.user_logging import user_logger
from flask import session as flask_session
import uuid

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
