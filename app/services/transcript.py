import os
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def fetch_transcript_youtube(url: str) -> tuple:
    api_key = os.environ.get("YT_API_KEY")
    if not api_key:
        raise ValueError("YouTube API key is missing. Add it to secrets.toml or environment variables.")
    match = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", url)
    if not match:
        raise ValueError("Invalid YouTube URL.")
    video_id = match.group(1)
    youtube = build("youtube", "v3", developerKey=api_key)
    try:
        video_response = youtube.videos().list(part="snippet", id=video_id).execute()
        video_title = video_response["items"][0]["snippet"]["title"] if video_response["items"] else "Unknown Video"
        captions = youtube.captions().list(part="snippet", videoId=video_id).execute()
        caption_id = None
        for item in captions.get("items", []):
            if item["snippet"]["language"] == "en":
                caption_id = item["id"]
                break
        if not caption_id:
            raise ValueError("No English captions found.")
        # Note: Downloading captions requires OAuth; using placeholder for now
        return "Sample YouTube transcript", {"title": video_title}
    except HttpError as e:
        raise Exception(f"YouTube API error: {e}")
