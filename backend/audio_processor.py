import os
from werkzeug.utils import secure_filename
import subprocess

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


def convert_to_mp3(input_path: str) -> str:
    """
    Convert an audio file (e.g. webm) to mp3 using ffmpeg.
    Returns the path to the mp3 file.
    """
    ensure_upload_dir()

    if not os.path.exists(input_path):
        raise ValueError(f"Input audio file does not exist: {input_path}")

    base, _ = os.path.splitext(input_path)
    output_path = base + ".mp3"

    cmd = [
        "ffmpeg",
        "-y",  # overwrite without asking
        "-i", input_path,
        "-vn",  # no video
        "-acodec", "libmp3lame",
        output_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return output_path
    except FileNotFoundError:
        # ffmpeg executable not found on PATH
        raise RuntimeError(
            "ffmpeg is not installed or not found on PATH. "
            "Please install ffmpeg and ensure the 'ffmpeg' command is available."
        )
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"ffmpeg conversion failed: {err}")

