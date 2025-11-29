import json
import os
from datetime import datetime
from uuid import uuid4

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
NOTES_FILE = os.path.join(DATA_DIR, 'notes.json')

def ensure_data_dir():
    """Create data directory if it doesn't exist"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, 'w') as f:
            json.dump({"notes": []}, f, indent=2)

def load_notes():
    """Load all notes from JSON file"""
    ensure_data_dir()
    try:
        with open(NOTES_FILE, 'r') as f:
            data = json.load(f)
            return data.get('notes', [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_notes(notes):
    """Save notes to JSON file"""
    ensure_data_dir()
    with open(NOTES_FILE, 'w') as f:
        json.dump({"notes": notes}, f, indent=2)

def add_note(note_type, title, content, metadata=None):
    """Add a new note to storage"""
    notes = load_notes()
    new_note = {
        "id": str(uuid4()),
        "type": note_type,
        "timestamp": datetime.now().isoformat(),
        "title": title,
        "content": content,
        "metadata": metadata or {}
    }
    notes.append(new_note)
    save_notes(notes)
    return new_note

def get_all_notes():
    """Get all notes"""
    return load_notes()

def get_note_by_id(note_id):
    """Get a specific note by ID"""
    notes = load_notes()
    for note in notes:
        if note['id'] == note_id:
            return note
    return None


