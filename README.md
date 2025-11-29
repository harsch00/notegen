# NoteGen - Note Generation App

Generate comprehensive notes from YouTube videos and Google Meet recordings using Google's Gemini AI.

## Features

- 📹 **YouTube Video Notes**: Paste a YouTube video URL and get AI-generated notes
- 🎙️ **Google Meet Recording**: Automatically record meetings and generate notes
- ⚙️ **Customizable**: Choose detail level (Brief/Medium/Detailed) and format (Bullet Points/Paragraphs)
- 📚 **History**: View all previously generated notes in one place

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key (free tier available)
- Chrome browser (for extension)

### Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the root directory:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

   To get a Gemini API key:
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account
   - Create a new API key
   - Copy the key to your `.env` file

3. Start the backend server:
```bash
cd backend
python app.py
```

The server will run on `http://localhost:5000`

### Frontend Setup

The frontend is automatically served by the Flask backend. Once you start the backend server, you can access the web app at:

```
http://localhost:5000
```

No separate frontend server is needed!

### Chrome Extension Setup

1. Open Chrome and go to `chrome://extensions/`

2. Enable "Developer mode" (toggle in top right)

3. Click "Load unpacked"

4. Select the `chrome-extension` folder

5. The extension icon should appear in your toolbar

6. **Important**: Make sure the backend server is running on port 5000 before using the extension

7. **Note**: The extension icon files (icon16.png, icon48.png, icon128.png) are currently placeholders. You can create proper PNG icons or the extension will work with default Chrome icons. See `chrome-extension/ICONS_README.md` for details.

## Usage

### Generating Notes from YouTube Videos

1. Open the web app in your browser
2. Paste a YouTube video URL in the input field
3. Select your preferred detail level and format
4. Click "Generate Notes"
5. Wait for the AI to process the video and generate notes
6. View your notes and access them later in the History tab

### Recording Google Meet Meetings

1. Join a Google Meet meeting
2. Click the NoteGen extension icon in your Chrome toolbar
3. Configure your note preferences (detail level and format)
4. Click "Start Recording"
5. The extension will record the meeting audio
6. Click "Stop Recording" when done
7. The audio will be automatically sent to the backend for processing
8. Notes will be generated and saved to your history
9. The web app will open automatically to show your notes

### Viewing History

1. Click the "History" tab in the web app
2. Filter notes by type (All/YouTube/Meet)
3. Click on any note to view full details

## Project Structure

```
notegen/
├── frontend/           # Web frontend (HTML/CSS/JS)
├── backend/            # Python Flask backend
├── chrome-extension/   # Chrome extension for Meet recording
├── data/              # JSON storage for notes
├── uploads/           # Temporary audio file storage
├── .env              # Environment variables (API key)
└── requirements.txt  # Python dependencies
```

## API Endpoints

- `POST /api/generate-notes/youtube` - Generate notes from YouTube URL
- `POST /api/generate-notes/audio` - Generate notes from audio file
- `GET /api/notes` - Get all notes
- `GET /api/notes/<id>` - Get specific note

## Notes

- The app uses Gemini 1.5 Flash model (free tier)
- Audio recordings are temporarily stored and deleted after processing
- All notes are stored locally in `data/notes.json`
- Make sure CORS is enabled if accessing from different ports

## Troubleshooting

- **Extension not recording**: Make sure you grant microphone permissions when prompted
- **API errors**: Verify your Gemini API key is correct in `.env`
- **CORS errors**: Ensure the backend is running and CORS is enabled
- **Audio upload fails**: Check that the backend server is running on port 5000

## License

MIT

