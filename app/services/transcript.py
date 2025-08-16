from typing import Optional, Tuple, List
from ..utils.logging import get_logger
logger = get_logger("transcript")

def fetch_transcript_youtube(url: str) -> Tuple[Optional[str], Optional[List[Tuple[str,float]]]]:
    """
    Try youtube-transcript-api first (if subtitles exist and are public).
    Return: (plain_text_transcript, timed_bullets[(text, start_sec)])
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
        import re
        vid = None
        m = re.search(r"v=([A-Za-z0-9_-]{11})", url)
        if m: vid = m.group(1)
        if not vid:  # short links
            m = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", url)
            if m: vid = m.group(1)
        if not vid:
            return None, None
        transcript = YouTubeTranscriptApi.get_transcript(vid)
        text = " ".join([seg["text"] for seg in transcript])
        timed = [(seg["text"], seg["start"]) for seg in transcript]
        return text, timed
    except Exception as e:
        logger.info(f"No transcript via API: {e}")
        return None, None

# Optional: local Whisper transcription if user opts in (requires ffmpeg & model)
def transcribe_with_whisper(local_mp3_path: str) -> str:
    import subprocess, json, os, tempfile
    # Minimal stub; users can replace with faster-whisper
    out = subprocess.check_output(["whisper", local_mp3_path, "--model", "base", "--output_format", "txt"])
    # whisper writes .txt next to source; return content
    txt_path = local_mp3_path.rsplit(".",1)[0] + ".txt"
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read()
