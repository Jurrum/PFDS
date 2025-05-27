import csv
import os
from datetime import datetime
import uuid
from flask import current_app

class UserLogger:
    def __init__(self):
        self.participant_id = None
        self.log_file = None
        self.fieldnames = [
            'timestamp', 'participant_id', 'event_type', 'post_id', 'category',
            'rating_value', 'rating_type', 'view_time', 'action', 'notes'
        ]

    def init_participant(self, participant_id=None):
        """Initialize logging for a new participant."""
        if not participant_id:
            participant_id = str(uuid.uuid4())[:8]  # Generate a short UUID if none provided
        
        self.participant_id = participant_id
        log_dir = os.path.join(current_app.root_path, 'logs')
        
        # Ensure logs directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        self.log_file = os.path.join(
            log_dir,
            f'participant_{participant_id}.csv'
        )
        
        # Create file and write header if it doesn't exist
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()

    def log_event(self, event_type, **kwargs):
        """Log a user interaction event."""
        if not self.participant_id:
            raise ValueError("Participant ID not initialized. Call init_participant() first.")

        event = {
            'timestamp': datetime.now().isoformat(),
            'participant_id': self.participant_id,
            'event_type': event_type,
        }
        
        # Add any additional kwargs to the event
        event.update(kwargs)
        
        # Write to CSV
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writerow(event)

    def log_rating(self, post_id, rating_value, rating_type):
        """Log a rating event."""
        self.log_event(
            'rating',
            post_id=post_id,
            rating_value=rating_value,
            rating_type=rating_type
        )

    def log_view_time(self, post_id, view_time):
        """Log post view time."""
        self.log_event(
            'view_time',
            post_id=post_id,
            view_time=view_time
        )

    def log_action(self, action, post_id=None, category=None):
        """Log a general user action."""
        self.log_event(
            'action',
            action=action,
            post_id=post_id,
            category=category
        )

    def save_session_data(self, username):
        """Save session data to a separate file."""
        if not self.log_file:
            return

        # Create session data directory if it doesn't exist
        session_dir = os.path.join(current_app.root_path, 'session_data')
        os.makedirs(session_dir, exist_ok=True)

        # Create session data file
        session_file = os.path.join(
            session_dir,
            f'session_{username}_{self.participant_id}.csv'
        )

        # Copy log file to session data file
        with open(self.log_file, 'r') as src:
            with open(session_file, 'w') as dst:
                dst.write(src.read())

        # Add session summary to the file
        with open(session_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['summary'])
            writer.writerow({'summary': f'Session ended at {datetime.now().isoformat()}'})

# Initialize the logger
user_logger = UserLogger()
