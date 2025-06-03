import os
import csv
import json
from datetime import datetime
from pathlib import Path
from .session_utils import get_session_directory

def save_questionnaire_responses(username, questionnaire_type, responses):
    """
    Save questionnaire responses to a CSV file in the session directory.
    
    Args:
        username (str): The participant's username
        questionnaire_type (str): 'pre' or 'post'
        responses (dict): The questionnaire responses
        
    Returns:
        str: Path to the saved file
    """
    # Get or create session directory
    session_dir = get_session_directory(username)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create filename
    filename = f"{timestamp}_{questionnaire_type}_questionnaire.csv"
    filepath = session_dir / filename
    
    # Flatten the responses dictionary
    flat_data = {
        'timestamp': datetime.now().isoformat(),
        'username': username,
        'questionnaire_type': questionnaire_type
    }
    
    # Flatten nested dictionaries
    for key, value in responses.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                flat_data[f"{key}_{subkey}"] = subvalue
        else:
            flat_data[key] = value
    
    # Write to CSV
    file_exists = filepath.exists()
    
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=flat_data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(flat_data)
    
    return str(filepath)

def export_session_data(username, data, filename_prefix=''):
    """
    Export session data to a CSV file in the session directory.
    
    Args:
        username (str): The participant's username
        data (list): List of dictionaries containing the data to export
        filename_prefix (str, optional): Prefix for the filename
        
    Returns:
        str: Path to the saved file
    """
    if not data:
        return None
        
    session_dir = get_session_directory(username)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create filename
    filename = f"{filename_prefix}{timestamp}_session_data.csv"
    filepath = session_dir / filename
    
    # Get all unique fieldnames from the data
    fieldnames = set()
    for item in data:
        fieldnames.update(item.keys())
    
    # Write to CSV
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
        writer.writeheader()
        writer.writerows(data)
    
    return str(filepath)
