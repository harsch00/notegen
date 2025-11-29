from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from gemini_service import generate_notes_from_youtube, generate_notes_from_audio
from storage import add_note, get_all_notes, get_note_by_id
from audio_processor import save_audio_file, cleanup_file

app = Flask(__name__, static_folder=None)
CORS(app)  # Enable CORS for frontend

# Serve frontend files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')

@app.route('/api/generate-notes/youtube', methods=['POST'])
def generate_youtube_notes():
    """Generate notes from YouTube video URL"""
    try:
        data = request.json
        youtube_url = data.get('url')
        detail_level = data.get('detail_level', 'medium')
        format_type = data.get('format_type', 'bullet')
        
        if not youtube_url:
            return jsonify({'error': 'YouTube URL is required'}), 400
        
        # Generate notes using Gemini
        notes_content = generate_notes_from_youtube(youtube_url, detail_level, format_type)
        
        # Extract video title from URL or use default
        video_title = youtube_url.split('v=')[-1].split('&')[0] if 'v=' in youtube_url else 'YouTube Video'
        
        # Save to storage
        note = add_note(
            note_type='youtube',
            title=f"YouTube Video: {video_title}",
            content=notes_content,
            metadata={
                'url': youtube_url,
                'detail_level': detail_level,
                'format_type': format_type
            }
        )
        
        return jsonify({
            'success': True,
            'note': note
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-notes/audio', methods=['POST'])
def generate_audio_notes():
    """Generate notes from uploaded audio file"""
    try:
        print("=== Audio Notes Request Received ===")
        print(f"Files: {list(request.files.keys())}")
        print(f"Form data: {dict(request.form)}")
        
        if 'audio' not in request.files:
            print("ERROR: No audio file in request")
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        detail_level = request.form.get('detail_level', 'medium')
        format_type = request.form.get('format_type', 'bullet')
        
        print(f"Audio file: {audio_file.filename}, size: {audio_file.content_length}")
        
        if audio_file.filename == '':
            print("ERROR: Empty filename")
            return jsonify({'error': 'No file selected'}), 400
        
        # Save audio file temporarily
        try:
            audio_path = save_audio_file(audio_file)
            print(f"Audio saved to: {audio_path}")
        except Exception as e:
            print(f"ERROR saving file: {str(e)}")
            return jsonify({'error': f'Error saving audio file: {str(e)}'}), 500
        
        try:
            # Generate notes using Gemini
            print("Calling generate_notes_from_audio...")
            notes_content = generate_notes_from_audio(audio_path, detail_level, format_type)
            print(f"Notes generated, length: {len(notes_content)}")
            
            # Save to storage
            note = add_note(
                note_type='meet',
                title=f"Google Meet Recording: {audio_file.filename}",
                content=notes_content,
                metadata={
                    'filename': audio_file.filename,
                    'detail_level': detail_level,
                    'format_type': format_type
                }
            )
            print("Note saved to storage")
            
            return jsonify({
                'success': True,
                'note': note
            }), 200
            
        except Exception as e:
            print(f"ERROR generating notes: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error generating notes: {str(e)}'}), 500
        finally:
            # Clean up temporary file
            try:
                cleanup_file(audio_path)
            except:
                pass
        
    except Exception as e:
        print(f"ERROR in audio endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/notes', methods=['GET'])
def get_notes():
    """Get all notes from history"""
    try:
        notes = get_all_notes()
        # Sort by timestamp (newest first)
        notes.sort(key=lambda x: x['timestamp'], reverse=True)
        return jsonify({'notes': notes}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notes/<note_id>', methods=['GET'])
def get_note(note_id):
    """Get a specific note by ID"""
    try:
        note = get_note_by_id(note_id)
        if note:
            return jsonify({'note': note}), 200
        else:
            return jsonify({'error': 'Note not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200

@app.route('/api/test-audio', methods=['POST'])
def test_audio():
    """Test endpoint to debug audio upload"""
    try:
        print("=== Test Audio Endpoint ===")
        print(f"Files: {list(request.files.keys())}")
        if 'audio' in request.files:
            audio_file = request.files['audio']
            print(f"Audio file received: {audio_file.filename}")
            print(f"Content type: {audio_file.content_type}")
            print(f"Content length: {audio_file.content_length}")
            
            # Save and check file
            audio_path = save_audio_file(audio_file)
            import os
            file_size = os.path.getsize(audio_path)
            print(f"File saved, size: {file_size} bytes")
            
            return jsonify({
                'success': True,
                'filename': audio_file.filename,
                'saved_path': audio_path,
                'file_size': file_size
            }), 200
        else:
            return jsonify({'error': 'No audio file'}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Serve frontend static files (must be after API routes)
@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_frontend(path):
    # Don't serve API routes as static files
    if path.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    # For SPA routing, return index.html
    return send_from_directory(FRONTEND_DIR, 'index.html')

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('data', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    
    app.run(debug=True, port=5000)

