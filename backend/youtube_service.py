import re
import json
import requests
from urllib.parse import urlparse, parse_qs
from collections import Counter
from datetime import datetime
import yt_dlp

# Stop words for key phrase extraction
STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
    'did', 'will', 'would', 'shall', 'should', 'may', 'might', 'must', 'can', 'could',
    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
    'my', 'your', 'his', 'its', 'our', 'their', 'this', 'that', 'these', 'those',
    'am', 'are', 'is', 'was', 'were', 'so', 'then', 'than', 'just', 'also', 'very',
    'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
    'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
    'no', 'nor', 'not', 'only', 'own', 'same', 'too', 'very', 's', 't', 'can', 'will',
    'don', 'don\'t', 'should', 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain',
    'aren', 'aren\'t', 'couldn', 'couldn\'t', 'didn', 'didn\'t', 'doesn', 'doesn\'t',
    'hadn', 'hadn\'t', 'hasn', 'hasn\'t', 'haven', 'haven\'t', 'isn', 'isn\'t',
    'ma', 'mightn', 'mightn\'t', 'mustn', 'mustn\'t', 'needn', 'needn\'t', 'shan',
    'shan\'t', 'shouldn', 'shouldn\'t', 'wasn', 'wasn\'t', 'weren', 'weren\'t',
    'won', 'won\'t', 'wouldn', 'wouldn\'t'
}

def extract_video_id(youtube_url):
    """Extract video ID from YouTube URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([^&]+)',
        r'(?:youtu\.be\/)([^?]+)',
        r'(?:youtube\.com\/embed\/)([^?]+)',
        r'(?:youtube\.com\/v\/)([^?]+)',
        r'(?:youtube\.com\/shorts\/)([^?]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    
    parsed = urlparse(youtube_url)
    if 'youtube.com' in parsed.netloc:
        query = parse_qs(parsed.query)
        if 'v' in query:
            return query['v'][0]
    
    match = re.search(r'(?:v=|be\/|embed\/|v\/|shorts\/)([\w\-_]{11})', youtube_url)
    if match:
        return match.group(1)
    
    return None

def get_video_info(video_id):
    """Get video title and duration using yt-dlp"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)
            
            title = info.get('title', 'Unknown Title')
            duration = info.get('duration', 0)
            description = info.get('description', '')
            
            return title, duration, description
    except Exception as e:
        print(f"Error getting video info: {e}")
        
        try:
            response = requests.get(
                f'https://www.youtube.com/oembed?url=https://youtube.com/watch?v={video_id}&format=json',
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                title = data.get('title', f'YouTube Video ({video_id})')
                return title, 0, ''
        except:
            pass
        
        return f'YouTube Video ({video_id})', 0, ''

def get_transcript_direct(video_id):
    """Get transcript directly from YouTube using yt-dlp"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'en-US', 'en-GB', 'en-AU', 'a.en', 'v.en'],
            'outtmpl': '-',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)
            
            subtitles = info.get('subtitles', {})
            auto_captions = info.get('automatic_captions', {})
            
            english_variants = ['en', 'en-US', 'en-GB', 'en-AU', 'a.en', 'v.en']
            
            for lang in english_variants:
                if lang in subtitles:
                    for sub_info in subtitles[lang]:
                        if sub_info.get('ext') in ['vtt', 'srt', 'json3']:
                            sub_url = sub_info.get('url')
                            if sub_url:
                                try:
                                    response = requests.get(sub_url, timeout=10)
                                    if response.status_code == 200:
                                        text = parse_subtitles(response.text)
                                        if text and len(text) > 100:
                                            return text, True
                                except:
                                    continue
                
                if lang in auto_captions:
                    for sub_info in auto_captions[lang]:
                        if sub_info.get('ext') in ['vtt', 'srt', 'json3']:
                            sub_url = sub_info.get('url')
                            if sub_url:
                                try:
                                    response = requests.get(sub_url, timeout=10)
                                    if response.status_code == 200:
                                        text = parse_subtitles(response.text)
                                        if text and len(text) > 100:
                                            return text, True
                                except:
                                    continue
            
            try:
                player_response = info.get('player_response', '{}')
                if isinstance(player_response, str):
                    player_data = json.loads(player_response)
                    captions = player_data.get('captions', {})
                    if captions:
                        caption_tracks = captions.get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
                        for track in caption_tracks:
                            if track.get('languageCode', '').startswith('en'):
                                sub_url = track.get('baseUrl')
                                if sub_url:
                                    response = requests.get(sub_url, timeout=10)
                                    if response.status_code == 200:
                                        text = parse_subtitles(response.text)
                                        if text and len(text) > 100:
                                            return text, True
            except:
                pass
            
    except Exception as e:
        print(f"Direct transcript fetch failed: {e}")
    
    return None, False

def get_transcript_alternative(video_id):
    """Alternative method to get transcript"""
    try:
        url = f"https://youtube.com/watch?v={video_id}"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'writeinfojson': False,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            transcript_parts = []
            
            chapters = info.get('chapters', [])
            for chapter in chapters:
                if 'title' in chapter:
                    transcript_parts.append(chapter['title'])
            
            description = info.get('description', '')
            if description:
                lines = description.split('\n')
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['chapter', 'topic', 'section', 'part', '00:', '0:', '1:', '2:', '3:', '4:', '5:', '6:', '7:', '8:', '9:']):
                        transcript_parts.append(line)
            
            if transcript_parts:
                return ' '.join(transcript_parts), True
                
    except Exception as e:
        print(f"Alternative transcript method failed: {e}")
    
    return None, False

def parse_subtitles(subtitle_text):
    """Parse VTT/SRT subtitle format to plain text"""
    if not subtitle_text:
        return ""
    
    if subtitle_text.strip().startswith('{'):
        try:
            data = json.loads(subtitle_text)
            if 'events' in data:
                text_parts = []
                for event in data['events']:
                    if 'segs' in event:
                        for seg in event['segs']:
                            if 'utf8' in seg:
                                text_parts.append(seg['utf8'])
                return ' '.join(text_parts)
        except:
            pass
    
    lines = subtitle_text.split('\n')
    text_lines = []
    
    for line in lines:
        if '-->' in line or line.strip().isdigit() or line.strip() == '':
            continue
        
        if line.startswith('WEBVTT') or line.startswith('STYLE') or line.startswith('NOTE'):
            continue
        
        cleaned = re.sub(r'<[^>]+>', '', line)
        cleaned = cleaned.strip()
        if cleaned:
            text_lines.append(cleaned)
    
    return ' '.join(text_lines)

def get_video_transcript(video_id):
    """Try multiple methods to get transcript"""
    methods = [
        get_transcript_direct,
        get_transcript_alternative,
    ]
    
    for method in methods:
        transcript, success = method(video_id)
        if success and transcript and len(transcript.strip()) > 50:
            return transcript
    
    raise Exception("Could not fetch transcript. The video might not have English captions enabled or available.")

def clean_transcript(transcript):
    """Clean and format transcript"""
    if not transcript:
        return ""
    
    transcript = re.sub(r'\s+', ' ', transcript)
    
    filler_patterns = [
        r'\b(um|uh|like|you know|actually|basically|literally|sort of|kind of|i mean|okay|so|right|well|hmm|ah|er|umm|uhh|guys|yaar|dude|bro|hey|hello|hi|welcome back|folks)\b',
        r'\b(subscribe|like the video|hit the bell|notification|channel|please share|comment below|don\'t forget to|smash that|ring the bell|hit that like button)\b.*?\.',
        r'\[.*?\]',
        r'\(.*?\)',
        r'♪.*?♪',
        r'^\s*[0-9]+\s*$',
    ]
    
    for pattern in filler_patterns:
        transcript = re.sub(pattern, '', transcript, flags=re.IGNORECASE)
    
    transcript = re.sub(r'\b(\w+)\s+\1\b', r'\1', transcript, flags=re.IGNORECASE)
    
    transcript = re.sub(r'\.\s+\.', '.', transcript)
    transcript = re.sub(r'\s+([.,!?;:])', r'\1', transcript)
    
    transcript = re.sub(r'\.([A-Z])', r'. \1', transcript)
    transcript = re.sub(r'!([A-Z])', r'! \1', transcript)
    transcript = re.sub(r'\?([A-Z])', r'? \1', transcript)
    
    transcript = transcript.strip()
    
    return transcript

def extract_key_phrases(text, num_phrases=10):
    """Extract key phrases from text"""
    if not text:
        return []
    
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    
    filtered_words = [word for word in words if word not in STOP_WORDS]
    
    if not filtered_words:
        return []
    
    word_freq = Counter(filtered_words)
    
    common_words = [word for word, freq in word_freq.most_common(num_phrases * 2)]
    
    sentences = re.split(r'[.!?]+', text)
    key_phrases = []
    
    for word in common_words[:num_phrases]:
        for sentence in sentences:
            if word in sentence.lower():
                clean_sentence = ' '.join(sentence.split()[:15])
                if clean_sentence and len(clean_sentence) > 20 and clean_sentence not in key_phrases:
                    key_phrases.append(clean_sentence)
                    break
    
    return key_phrases[:num_phrases]

def extract_important_elements(text):
    """Extract numbers, dates, definitions, examples, and steps"""
    elements = {
        'numbers': [],
        'dates': [],
        'definitions': [],
        'examples': [],
        'steps': []
    }
    
    numbers = re.findall(r'\b\d+\.?\d*\b', text)
    elements['numbers'] = list(set(numbers[:10]))
    
    date_patterns = [
        r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'
    ]
    for pattern in date_patterns:
        dates = re.findall(pattern, text, re.IGNORECASE)
        elements['dates'].extend(dates[:5])
    
    definition_patterns = [
        r'([^.!?]*\b(?:is defined as|means|refers to|is called|is known as)\b[^.!?]*[.!?])',
        r'([^.!?]*\b(?:definition of|define)\b[^.!?]*[.!?])'
    ]
    for pattern in definition_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches[:5]:
            if match.strip() and len(match.strip()) > 20:
                elements['definitions'].append(match.strip())
    
    example_patterns = [
        r'([^.!?]*\b(?:for example|for instance|such as|like|including|e\.g\.)\b[^.!?]*[.!?])',
        r'([^.!?]*\b(?:example|instance)\b[^.!?]*[.!?])'
    ]
    for pattern in example_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches[:5]:
            if match.strip() and len(match.strip()) > 20:
                elements['examples'].append(match.strip())
    
    step_patterns = [
        r'([^.!?]*\b(?:step \d+|first|second|third|fourth|fifth|next|then|finally|lastly)\b[^.!?]*[.!?])',
        r'([^.!?]*\b\d+\.\s+[^.!?]*[.!?])'
    ]
    for pattern in step_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches[:10]:
            if match.strip() and len(match.strip()) > 20:
                elements['steps'].append(match.strip())
    
    return elements

def generate_summary(text, max_sentences=4):
    """Generate a summary from text"""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
    
    if not sentences:
        return "No summary available."
    
    if len(sentences) <= max_sentences:
        return ' '.join(sentences) + '.'
    
    summary_indices = [0]
    if len(sentences) > 3:
        summary_indices.append(len(sentences) // 3)
        summary_indices.append(2 * len(sentences) // 3)
    if len(sentences) > 1:
        summary_indices.append(-1)
    
    summary_sentences = [sentences[i] for i in summary_indices if i < len(sentences)]
    return ' '.join(summary_sentences) + '.'

def organize_content_by_topic(text):
    """Organize content by topic areas"""
    
    topic_indicators = {
        'Introduction': ['introduction', 'overview', 'welcome', 'start', 'beginning'],
        'Background': ['background', 'history', 'context', 'previous', 'before'],
        'Method': ['method', 'approach', 'technique', 'process', 'procedure'],
        'Results': ['result', 'finding', 'outcome', 'conclusion', 'summary'],
        'Application': ['application', 'use', 'practice', 'implementation', 'example'],
        'Advantages': ['advantage', 'benefit', 'pro', 'strength', 'positive'],
        'Disadvantages': ['disadvantage', 'limitation', 'drawback', 'con', 'negative'],
        'Conclusion': ['conclusion', 'summary', 'wrap up', 'final', 'ending']
    }
    
    sentences = re.split(r'[.!?]+', text)
    organized = {topic: [] for topic in topic_indicators.keys()}
    organized['Other'] = []
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        matched = False
        
        for topic, keywords in topic_indicators.items():
            if any(keyword in sentence_lower for keyword in keywords):
                if len(sentence.strip()) > 20:
                    organized[topic].append(sentence.strip())
                    matched = True
                    break
        
        if not matched and len(sentence.strip()) > 30:
            organized['Other'].append(sentence.strip())
    
    organized = {k: v for k, v in organized.items() if v}
    
    return organized

def generate_notes_from_youtube(youtube_url, detail_level='medium', format_type='bullet'):
    """
    Generate notes from YouTube video URL using transcript extraction
    
    Args:
        youtube_url: YouTube video URL
        detail_level: 'brief', 'medium', or 'detailed' (affects summary length)
        format_type: 'bullet' or 'paragraph' (currently always uses structured format)
    
    Returns:
        Tuple of (notes_markdown, video_title, video_id)
    """
    # Extract video ID
    video_id = extract_video_id(youtube_url)
    if not video_id:
        raise Exception("Invalid YouTube URL. Please check the link.")
    
    # Get video info
    video_title, duration, description = get_video_info(video_id)
    
    # Get transcript
    raw_transcript = get_video_transcript(video_id)
    if not raw_transcript:
        raise Exception("No transcript available. This video might not have English captions enabled.")
    
    # Clean transcript
    cleaned_transcript = clean_transcript(raw_transcript)
    
    if len(cleaned_transcript) < 100:
        raise Exception("Transcript too short to generate meaningful notes. Try a video with more substantial content and enabled captions.")
    
    # Adjust summary length based on detail level
    max_summary_sentences = {
        'brief': 2,
        'medium': 4,
        'detailed': 6
    }.get(detail_level, 4)
    
    # Generate notes
    summary = generate_summary(cleaned_transcript, max_summary_sentences)
    key_phrases = extract_key_phrases(cleaned_transcript, 8)
    elements = extract_important_elements(cleaned_transcript)
    organized_content = organize_content_by_topic(cleaned_transcript)
    
    # Format duration
    if duration > 0:
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        if hours > 0:
            duration_str = f"{hours}h {minutes}m {seconds}s"
        else:
            duration_str = f"{minutes}m {seconds}s"
    else:
        duration_str = "Unknown"
    
    # Build notes in markdown format
    notes = f"""# 📝 VIDEO NOTES: {video_title}

**⏱️ Duration:** {duration_str}  
**📄 Transcript Length:** {len(cleaned_transcript)} characters  
**📅 Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📋 EXECUTIVE SUMMARY

{summary}

## 🔑 KEY PHRASES & CONCEPTS

"""
    
    for i, phrase in enumerate(key_phrases, 1):
        notes += f"{i}. {phrase}.\n"
    
    notes += f"\n## 📊 IMPORTANT NUMERICAL DATA\n"
    if elements['numbers']:
        for i, num in enumerate(elements['numbers'][:8], 1):
            notes += f"- {num}\n"
    else:
        notes += "No specific numerical data found.\n"
    
    if elements['dates']:
        notes += f"\n## 📅 DATES MENTIONED\n"
        for date in elements['dates'][:5]:
            notes += f"- {date}\n"
    
    notes += f"\n## 📖 KEY DEFINITIONS\n"
    if elements['definitions']:
        for i, definition in enumerate(elements['definitions'][:5], 1):
            notes += f"{i}. {definition}\n"
    else:
        notes += "No explicit definitions found in transcript.\n"
    
    notes += f"\n## 💡 EXAMPLES PROVIDED\n"
    if elements['examples']:
        for i, example in enumerate(elements['examples'][:5], 1):
            notes += f"{i}. {example}\n"
    else:
        notes += "No specific examples identified.\n"
    
    notes += f"\n## 🚀 STEP-BY-STEP PROCESSES\n"
    if elements['steps']:
        for i, step in enumerate(elements['steps'][:10], 1):
            clean_step = re.sub(r'\b(step\s+\d+|first|second|third|fourth|fifth|next|then|finally|lastly)\b', '', step, flags=re.IGNORECASE).strip()
            if clean_step:
                notes += f"**Step {i}:** {clean_step}\n"
    else:
        notes += "No clear step-by-step process identified.\n"
    
    notes += f"\n## 🗂️ CONTENT ORGANIZED BY TOPIC\n"
    for topic, sentences in organized_content.items():
        if sentences:
            notes += f"\n### {topic.upper()}\n"
            for i, sentence in enumerate(sentences[:5], 1):
                notes += f"{i}. {sentence}.\n"
    
    notes += f"\n## 📈 CONTENT ANALYSIS\n"
    notes += f"- **Total meaningful content:** {len(re.findall(r'[.!?]', cleaned_transcript))} sentences\n"
    notes += f"- **Key topics identified:** {len(organized_content)}\n"
    notes += f"- **Technical terms:** {len(key_phrases)}\n"
    notes += f"- **Procedural content:** {'Yes' if elements['steps'] else 'No'}\n"
    
    notes += f"\n## 💎 KEY TAKEAWAYS\n"
    takeaways = [
        "Focus on the main concepts mentioned in key phrases",
        "Review numerical data and dates for important facts",
        "Understand definitions provided in the video",
        "Follow step-by-step processes for practical application",
        "Note examples for better understanding"
    ]
    
    for i, takeaway in enumerate(takeaways, 1):
        notes += f"{i}. {takeaway}\n"
    
    notes += f"\n---\n"
    notes += f"*Notes automatically generated from YouTube transcript.*\n"
    notes += f"*For optimal results, use videos with clear English captions and educational content.*\n"
    
    return notes, video_title, video_id

