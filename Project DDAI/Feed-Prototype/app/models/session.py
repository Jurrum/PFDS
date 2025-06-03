from datetime import datetime
import json
import logging
from app import db

# Set up a module-level logger
logger = logging.getLogger(__name__)

class UserSession(db.Model):
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False, index=True)  # Removed unique=True
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    total_interactions = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    pre_questionnaire_completed = db.Column(db.Boolean, default=False)
    post_questionnaire_completed = db.Column(db.Boolean, default=False)
    questionnaire_data = db.Column(db.Text, default='{}')

    def __init__(self, **kwargs):
        super(UserSession, self).__init__(**kwargs)
        self.questionnaire_data = '{}'

    def __repr__(self):
        return f'<UserSession {self.username}>'

    @property
    def questionnaire_data_dict(self):
        """Get questionnaire data as a dictionary."""
        try:
            if not self.questionnaire_data:
                logger.debug("questionnaire_data is empty, returning empty dict")
                return {}
                
            if isinstance(self.questionnaire_data, dict):
                logger.debug("questionnaire_data is already a dict, returning as is")
                return self.questionnaire_data
                
            if not isinstance(self.questionnaire_data, str):
                logger.warning(f"questionnaire_data is not a string: {type(self.questionnaire_data)}")
                return {}
                
            result = json.loads(self.questionnaire_data)
            logger.debug("Successfully parsed questionnaire_data to dict")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from questionnaire_data: {str(e)}")
            logger.error(f"Problematic data: {self.questionnaire_data}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error in questionnaire_data_dict getter: {str(e)}", exc_info=True)
            return {}

    @questionnaire_data_dict.setter
    def questionnaire_data_dict(self, value):
        """Set questionnaire data from a dictionary."""
        try:
            logger.debug(f"Setting questionnaire_data_dict. Input type: {type(value) if value is not None else 'None'}")
            if value is None:
                self.questionnaire_data = '{}'
            elif isinstance(value, str):
                # If it's already a string, try to validate it's valid JSON
                try:
                    json.loads(value)  # Validate it's valid JSON
                    self.questionnaire_data = value
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON string provided to questionnaire_data_dict setter")
                    self.questionnaire_data = '{}'
            else:
                # Convert dict or other object to JSON string
                self.questionnaire_data = json.dumps(value)
                
            logger.debug("Successfully set questionnaire_data")
            
        except Exception as e:
            logger.error(f"Error in questionnaire_data_dict setter: {str(e)}", exc_info=True)
            self.questionnaire_data = '{}'  # Fallback to empty JSON object

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_interactions': self.total_interactions,
            'completed': self.completed,
            'pre_questionnaire_completed': self.pre_questionnaire_completed,
            'post_questionnaire_completed': self.post_questionnaire_completed,
            'questionnaire_data': self.questionnaire_data_dict
        }
