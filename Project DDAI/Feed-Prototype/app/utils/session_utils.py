import os
import shutil
from pathlib import Path
from datetime import datetime

def get_session_directory(username):
    """
    Get or create a session directory for the given username.
    
    Args:
        username (str): The username/session identifier
        
    Returns:
        Path: Path to the session directory
    """
    # Base directory for all session data
    base_dir = Path(__file__).parent.parent / 'session_data'
    
    # Create session directory with username
    session_dir = base_dir / username
    session_dir.mkdir(parents=True, exist_ok=True)
    
    return session_dir

def get_database_path(username):
    """
    Get the path to the session-specific database file.
    
    Args:
        username (str): The username/session identifier
        
    Returns:
        str: Path to the SQLite database file
    """
    session_dir = get_session_directory(username)
    return f"sqlite:///{session_dir}/feed.db"

def get_export_path(username, file_type, prefix=''):
    """
    Get a path for exporting session data.
    
    Args:
        username (str): The username/session identifier
        file_type (str): Type of file (e.g., 'questionnaire', 'log')
        prefix (str, optional): Optional prefix for the filename
        
    Returns:
        Path: Path to the export file
    """
    session_dir = get_session_directory(username)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    filename = f"{prefix}{timestamp}_{file_type}.csv"
    return session_dir / filename

def move_to_session(username, src_path):
    """
    Move a file to the session directory.
    
    Args:
        username (str): The username/session identifier
        src_path (str): Source file path
        
    Returns:
        Path: New path in the session directory
    """
    if not os.path.exists(src_path):
        return None
        
    session_dir = get_session_directory(username)
    filename = os.path.basename(src_path)
    dst_path = session_dir / filename
    
    if os.path.exists(dst_path):
        # If file exists, add timestamp to avoid overwriting
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dst_path = session_dir / f"{name}_{timestamp}{ext}"
    
    shutil.move(src_path, dst_path)
    return dst_path
