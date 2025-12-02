import os
from google import genai
from dotenv import load_dotenv

# Load .env file from project root (one level up from backend directory)
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
env_path = os.path.abspath(env_path)  # Convert to absolute path
load_dotenv(dotenv_path=env_path, override=True)

# Configure Gemini API client (google-genai)
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not found in environment variables")

client = genai.Client(api_key=api_key)

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
    # Use Gemini 2.5 Flash for text + URL processing (matches official sample)
    model = "gemini-2.5-flash"
    
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
        response = client.models.generate_content(
            model=model,
            contents=[prompt]
        )
        return response.text.strip()
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
    # Use Gemini 2.5 Flash for audio + text (matches official sample syntax)
    model = "gemini-2.5-flash"
    
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
        # Check if file exists and get size
        if not os.path.exists(audio_file_path):
            raise Exception(f"Audio file not found: {audio_file_path}")
        
        file_size = os.path.getsize(audio_file_path)
        print(f"Audio file size: {file_size} bytes")
        
        if file_size == 0:
            raise Exception("Audio file is empty")
        
        # Upload audio file using official google-genai client
        print("Uploading audio file to Gemini via google-genai client...")
        uploaded_file = client.files.upload(file=audio_file_path)
        print(f"Audio file uploaded: {uploaded_file.name}")

        # Wait until file is ACTIVE before using it, to avoid FAILED_PRECONDITION
        max_wait_secs = 180
        waited = 0
        state = getattr(uploaded_file, "state", None)
        state_name = getattr(state, "name", None) if state else None
        print(f"Initial uploaded file state: {state_name}")

        while state_name not in ("ACTIVE", "FAILED") and waited < max_wait_secs:
            import time
            time.sleep(2)
            waited += 2
            uploaded_file = client.files.get(name=uploaded_file.name)
            state = getattr(uploaded_file, "state", None)
            state_name = getattr(state, "name", None) if state else None
            print(f"Polled file state: {state_name} (waited {waited}s)")

        if state_name != "ACTIVE":
            raise Exception(f"Uploaded audio file is not ready (state={state_name}). Please try again with a shorter recording.")

        print("Generating content with audio...")
        # Official pattern: contents=[prompt, uploaded_file]
        response = client.models.generate_content(
            model=model,
            contents=[prompt, uploaded_file]
        )

        print("Content generated successfully")
        result_text = response.text.strip()

        return result_text
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Exception(f"Error generating notes from audio: {str(e)}")


