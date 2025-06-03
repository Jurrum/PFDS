import csv
import json
import logging
import os
from datetime import datetime
import uuid
from pathlib import Path
from flask import current_app

# Set up logging
logger = logging.getLogger(__name__)

class UserLogger:
    def __init__(self):
        self.participant_id = None
        self.log_file = None
        self.log_entries = []
        self.initialized = False
    
    def initialize_logger(self, participant_id, log_file=None):
        """
        Initialize the logger with a participant ID and optional log file path.
        
        Args:
            participant_id (str): Unique identifier for the participant
            log_file (str, optional): Path to the log file. If not provided, a default will be used.
        """
        self.participant_id = participant_id
        self.log_entries = []
        
        # Use provided log file or create a default one
        if log_file:
            self.log_file = Path(log_file)
        else:
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            self.log_file = log_dir / f'participant_{participant_id}.csv'
        
        # Ensure parent directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize log file with header if it doesn't exist
        if not self.log_file.exists():
            try:
                with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['timestamp', 'event_type', 'data'])
                self.initialized = True
                logger.info(f"Initialized new log file at {self.log_file}")
            except Exception as e:
                logger.error(f"Failed to initialize log file: {e}")
                self.initialized = False
        else:
            self.initialized = True
            logger.info(f"Using existing log file at {self.log_file}")
    
    def log_event(self, event_type, data=None, **kwargs):
        """
        Log an event with the given type and data.
        
        Args:
            event_type (str): Type of event (e.g., 'view', 'rating', 'share')
            data (dict, optional): Additional event data
            **kwargs: Additional fields to include in the log
        """
        if not self.initialized:
            logger.warning("Logger not initialized. Call initialize_logger() first.")
            return
        
        timestamp = datetime.utcnow().isoformat()
        log_data = {
            'timestamp': timestamp,
            'event_type': event_type,
            'participant_id': self.participant_id,
            **(data or {}),
            **kwargs
        }
        
        # Add to in-memory log
        self.log_entries.append(log_data)
        
        # Append to log file
        try:
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    event_type,
                    json.dumps(log_data, ensure_ascii=False)
                ])
        except Exception as e:
            logger.error(f"Error writing to log file: {e}")
    
    def log_rating(self, post_id, rating, rating_type='like', **kwargs):
        """Log a rating event."""
        self.log_event(
            'rating',
            post_id=post_id,
            rating=rating,
            rating_type=rating_type,
            **kwargs
        )
    
    def log_view(self, post_id, duration=None, **kwargs):
        """Log a post view event."""
        self.log_event(
            'view',
            post_id=post_id,
            duration=duration,
            **kwargs
        )
    
    def log_share(self, post_id, platform=None, **kwargs):
        """Log a post share event."""
        self.log_event(
            'share',
            post_id=post_id,
            platform=platform,
            **kwargs
        )
    
    def log_comment(self, post_id, comment_text=None, **kwargs):
        """Log a comment event."""
        self.log_event(
            'comment',
            post_id=post_id,
            comment_length=len(comment_text) if comment_text else 0,
            **kwargs
        )
    
    def get_all_events(self):
        """Return all logged events as a list of dictionaries."""
        return self.log_entries
    
    def clear_logs(self):
        """Clear all log entries from memory (does not clear the log file)."""
        self.log_entries = []
    
    def export_logs(self, output_file=None):
        """
        Export logs to a CSV file.
        
        Args:
            output_file (str, optional): Path to the output file. If not provided,
                                      defaults to the current log file with .csv extension.
        """
        output_file = Path(output_file) if output_file else self.log_file
        
        try:
            # Just copy the existing log file if it exists
            if self.log_file.exists():
                import shutil
                shutil.copy2(self.log_file, output_file)
                logger.info(f"Exported logs to {output_file}")
                return str(output_file)
            else:
                logger.warning("No log file exists to export")
                return None
        except Exception as e:
            logger.error(f"Error exporting logs: {e}")
            return None
    
    def save_session_data(self, username):
        """Save session data to a separate file."""
        if not self.log_file or not self.participant_id:
            logger.warning("Cannot save session data: logger not properly initialized")
            return

        try:
            # Create session data directory if it doesn't exist
            session_dir = Path('session_data')
            session_dir.mkdir(parents=True, exist_ok=True)

            # Create session data file path
            session_file = session_dir / f'session_{username}_{self.participant_id}.csv'
            
            # Copy log file to session data file
            if self.log_file.exists():
                import shutil
                shutil.copy2(self.log_file, session_file)
                logger.info(f"Saved session data to {session_file}")
            
            # Add session summary to the file
            with open(session_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['--- SESSION SUMMARY ---'])
                writer.writerow(['end_time', datetime.utcnow().isoformat()])
                writer.writerow(['total_events', len(self.log_entries)])
                
            return str(session_file)
            
        except Exception as e:
            logger.error(f"Error saving session data: {e}")
            return None

# Initialize the logger
user_logger = UserLogger()
