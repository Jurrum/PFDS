from app import create_app, db
from app.utils.user_logging import user_logger
from flask import session as flask_session
from flask_session import Session
import uuid

app = create_app()

if __name__ == '__main__':
    # Ensure the instance folder exists
    import os
    os.makedirs(app.instance_path, exist_ok=True)
    
    # Ensure the session directory exists
    session_dir = os.path.join(app.instance_path, 'flask_session')
    os.makedirs(session_dir, exist_ok=True)
    
    # Run the application
    app.run(debug=True, use_reloader=False)
3