import os
import tempfile
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'webm', 'm4a'}

def ensure_upload_dir():
    """Create upload directory if it doesn't exist"""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_audio_file(file):
    """
    Save uploaded audio file temporarily
    
    Args:
        file: File object from Flask request
    
    Returns:
        Path to saved file
    """
    ensure_upload_dir()
    
    if not file or not allowed_file(file.filename):
        raise ValueError("Invalid audio file format")
    
    # Create temporary file
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    file.save(filepath)
    return filepath

def cleanup_file(filepath):
    """Delete temporary audio file"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Error cleaning up file {filepath}: {e}")


