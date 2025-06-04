import os
import re
from typing import Optional, List, Dict
from cerebras.cloud.sdk import Cerebras
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


# --- URL Validation and Video ID Extraction ---

def is_valid_youtube_url(url: str) -> bool:
    pattern = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-]{11}'
    return re.match(pattern, url) is not None


def extract_video_id(url: str) -> str:
    patterns = [
        r'youtu\.be/([\w\-]{11})',
        r'youtube\.com/watch\?v=([\w\-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Invalid YouTube URL format")


# --- Transcript Retrieval and Processing ---

def fetch_transcript(video_id: str) -> Optional[List[Dict[str, str]]]:
    try:
        return YouTubeTranscriptApi.get_transcript(video_id)
    except (TranscriptsDisabled, NoTranscriptFound, Exception):
        # Add comprehensive details as to what has happened
        print(f"Transcript not available for video ID: {video_id}")
        print(Exception)
        return None

def format_transcript(transcript: List[Dict[str, str]], max_chars: int = 5000) -> str:
    full_text = " ".join(entry.get('text', '') for entry in transcript)
    return full_text[:max_chars].strip()


# --- Prompt Generation ---

def generate_summary_prompt(transcript_text: str, language='en') -> str:
    prompt = (
        "Please summarize the following YouTube video transcript in 2-3 clear and concise sentences. Only provide the summary—no additional commentary or explanations.only include the summary in your response\n\n Your response should be explicitly in this language: "
        f"{language}.\n\n"
        "Here is the transcript:\n\n"
        f"{transcript_text}"
    )
    return prompt
    

def generate_takeaways_prompt(transcript_text: str, language='en') -> str:
    prompt = (
        "Please extract the main takeaways from the following YouTube video transcript. Provide a list of key points or insights, formatted as bullet points. Only include the takeaways in your response.\n\n Your response should be explicitly in this language: "
        f"{language}.\n\n"
        "Here is the transcript:\n\n"
        f"{transcript_text}"
    )
    return prompt
    
    
# --- LLM Takeaways via Cerebras ---

def takeaways_with_cerebras(prompt: str, model: str = "llama-4-scout-17b-16e-instruct") -> str:
    try:
        client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY"))
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Failed to generate takeaways: {e}"
    
def summarize_takeaways_youtube_video(url: str, language='English') -> str:
    if not is_valid_youtube_url(url):
        return "Invalid YouTube URL."

    try:
        video_id = extract_video_id(url)
    except ValueError as e:
        return str(e)

    transcript = fetch_transcript(video_id)
    if not transcript:
        return "Transcript is not available for this video."

    transcript_text = format_transcript(transcript)
    if len(transcript_text) < 100:
        return "This video is very short and doesn't need summarizing."
    prompt = generate_takeaways_prompt(transcript_text, language=language)
    takeaways = takeaways_with_cerebras(prompt)
    return takeaways

# --- LLM Summarization via Cerebras ---

def summarize_with_cerebras(prompt: str, model: str = "llama-4-scout-17b-16e-instruct") -> str:
    try:
        client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY"))
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Failed to generate summary: {e}"


# --- End-to-End Summarization ---

def summarize_youtube_video(url: str, language = 'English') -> str:
    if not is_valid_youtube_url(url):
        return "Invalid YouTube URL."

    try:
        video_id = extract_video_id(url)
    except ValueError as e:
        return str(e)

    transcript = fetch_transcript(video_id)
    if not transcript:
        return "Transcript is not available for this video."

    transcript_text = format_transcript(transcript)
    if len(transcript_text) < 100:
        return "This video is very short and doesn't need summarizing."

    prompt = generate_summary_prompt(transcript_text, language=language)
    summary = summarize_with_cerebras(prompt)
    return summary
