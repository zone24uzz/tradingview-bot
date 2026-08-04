import sys
from youtube_transcript_api import YouTubeTranscriptApi

try:
    video_id = "2TI-tCVhe9k"
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    
    # Try fetching manual or generated transcripts
    try:
        transcript = transcript_list.find_transcript(['uz', 'ru', 'en'])
    except:
        transcript = transcript_list.find_transcript(['uz'])
        
    data = transcript.fetch()
    text = " ".join([item['text'] for item in data])
    print(text)
except Exception as e:
    print(f"Error fetching transcript: {e}")
