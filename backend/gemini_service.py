import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env file from project root (one level up from backend directory)
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
env_path = os.path.abspath(env_path)  # Convert to absolute path
load_dotenv(dotenv_path=env_path, override=True)

# Configure Gemini API
api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)

def get_model(for_audio=False):
    """Get Gemini model (using free tier model)
    
    Args:
        for_audio: If True, prioritize models that support audio processing
    """
    if for_audio:
        # Models that support audio processing (free tier)
        # Note: Native audio models may not be available, use standard models with file upload
        model_names = [
            'gemini-2.0-flash',      # Supports audio via file upload (most reliable)
            'gemini-2.5-flash',      # Supports audio via file upload
            'gemini-1.5-flash',      # Classic audio support
            'gemini-flash-latest',   # Latest with audio
        ]
    else:
        # General purpose models (free tier)
        model_names = [
            'gemini-2.0-flash',      # Latest free tier flash model
            'gemini-2.5-flash',      # Alternative free tier option
            'gemini-flash-latest',   # Latest flash model
            'gemini-pro',            # Classic free tier model
        ]
    
    for model_name in model_names:
        try:
            model = genai.GenerativeModel(model_name)
            # Test if model can be created (basic check)
            print(f"Using model: {model_name}")
            return model
        except Exception as e:
            print(f"Failed to load {model_name}: {e}")
            continue
    
    # If all fail, raise an error
    raise Exception("Could not initialize any Gemini model. Please check your API key and model availability.")

def generate_notes_from_youtube(youtube_url, detail_level='medium', format_type='bullet'):
    """
    Generate notes from YouTube video URL
    
    Args:
        youtube_url: YouTube video URL
        detail_level: 'brief', 'medium', or 'detailed'
        format_type: 'bullet' or 'paragraph'
    
    Returns:
        Generated notes as string
    """
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    model = get_model()
    
    # Build prompt based on customization options
    detail_instructions = {
        'brief': 'Provide a brief summary with only the most important points.',
        'medium': 'Provide a comprehensive summary covering all main topics and key details.',
        'detailed': 'Provide a very detailed summary with all topics, subtopics, examples, and important quotes or statements.'
    }
    
    format_instructions = {
        'bullet': 'Format the notes as bullet points with clear headings and sub-bullets.',
        'paragraph': 'Format the notes as well-structured paragraphs with clear sections and headings.'
    }
    
    prompt = f"""Please watch this YouTube video and generate comprehensive notes: {youtube_url}

{detail_instructions.get(detail_level, detail_instructions['medium'])}

{format_instructions.get(format_type, format_instructions['bullet'])}

Include:
- Main topics discussed
- Key points and takeaways
- Important details, examples, or quotes
- Any actionable items or recommendations

Generate the notes now:"""
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise Exception(f"Error generating notes from YouTube video: {str(e)}")

def generate_notes_from_audio(audio_file_path, detail_level='medium', format_type='bullet'):
    """
    Generate notes from audio file (transcribe and summarize)
    
    Args:
        audio_file_path: Path to audio file
        detail_level: 'brief', 'medium', or 'detailed'
        format_type: 'bullet' or 'paragraph'
    
    Returns:
        Generated notes as string
    """
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    model = get_model(for_audio=True)  # Use audio-capable model
    
    # Build prompt based on customization options
    detail_instructions = {
        'brief': 'Provide a brief summary with only the most important points.',
        'medium': 'Provide a comprehensive summary covering all main topics and key details.',
        'detailed': 'Provide a very detailed summary with all topics, subtopics, examples, and important statements.'
    }
    
    format_instructions = {
        'bullet': 'Format the notes as bullet points with clear headings and sub-bullets.',
        'paragraph': 'Format the notes as well-structured paragraphs with clear sections and headings.'
    }
    
    prompt = f"""Please transcribe this audio recording and generate comprehensive meeting notes.

{detail_instructions.get(detail_level, detail_instructions['medium'])}

{format_instructions.get(format_type, format_instructions['bullet'])}

Include:
- Main topics discussed
- Key points and decisions made
- Action items and next steps
- Important details or quotes
- Participants' contributions (if identifiable)

Generate the notes now:"""
    
    try:
        import os
        # Check if file exists and get size
        if not os.path.exists(audio_file_path):
            raise Exception(f"Audio file not found: {audio_file_path}")
        
        file_size = os.path.getsize(audio_file_path)
        print(f"Audio file size: {file_size} bytes")
        
        if file_size == 0:
            raise Exception("Audio file is empty")
        
        # Upload audio file
        print("Uploading audio file to Gemini...")
        audio_file = genai.upload_file(path=audio_file_path)
        print(f"Audio file uploaded: {audio_file.name}")
        
        # Wait for file to be processed (check state)
        import time
        max_wait = 60  # Maximum 60 seconds
        wait_time = 0
        while wait_time < max_wait:
            try:
                # Refresh file status
                audio_file = genai.get_file(audio_file.name)
                state = audio_file.state.name if hasattr(audio_file.state, 'name') else str(audio_file.state)
                print(f"File state: {state}")
                
                if state == "ACTIVE" or state == "active":
                    break
                elif state == "FAILED" or state == "failed":
                    raise Exception("Audio file processing failed")
                elif state == "PROCESSING" or state == "processing":
                    print("Waiting for file processing...")
                    time.sleep(2)
                    wait_time += 2
                else:
                    # Unknown state, try to proceed
                    print(f"Unknown state {state}, proceeding...")
                    break
            except Exception as e:
                print(f"Error checking file state: {e}, proceeding anyway...")
                break
        
        if wait_time >= max_wait:
            print("Warning: File processing timeout, proceeding anyway...")
        
        print("Generating content with audio...")
        # Generate content with audio
        response = model.generate_content([audio_file, prompt])
        
        print("Content generated successfully")
        result_text = response.text
        
        # Clean up uploaded file
        try:
            genai.delete_file(audio_file.name)
            print("Uploaded file deleted")
        except Exception as e:
            print(f"Warning: Could not delete uploaded file: {e}")
        
        return result_text
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Exception(f"Error generating notes from audio: {str(e)}")


