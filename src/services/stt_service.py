from pathlib import Path
from typing import List
from pydantic import BaseModel
import whisper
import json

class STTError(Exception):
    """custom exception for speech-to-text errors."""
    pass

class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str

class TranscriptResult(BaseModel):
    text: str
    segments: List[TranscriptSegment]


# Lazy-loaded Whisper model (load on first use, with clear error)
model = None

def get_whisper_model():
    global model
    if model is not None:
        return model
    try:
        import whisper
    except Exception as e:
        raise STTError(f"Failed to import Whisper package: {e}")
    try:
        model = whisper.load_model("base")
    except Exception as e:
        raise STTError(f"Failed to load Whisper model: {e}")
    return model


def transcribe_audio_file(audio_path : Path) -> TranscriptResult :
    """
    Transcribe audio using local Whisper model.
    Requires audio to be in a compatible format.
    """

    if not audio_path.exists() :
        raise STTError(f"Audio file not found: {audio_path}")
    
    model = get_whisper_model()

    try:
        result = model.transcribe(str(audio_path), verbose=False)
    except Exception as e:
        raise STTError(f"Whisper transcription failed: {e}")

    full_text = result.get("text","") or ""

    raw_segments = result.get("segments",[]) or []

    segments : List[TranscriptSegment] = [
        TranscriptSegment(
            start=float(seg.get("start", 0.0)),
            end=float(seg.get("end", 0.0)),
            text=str(seg.get("text", "")),
        )
        for seg in raw_segments
    ]

    return TranscriptResult(text=full_text.strip(), segments=segments)


def save_transcript_to_json(transcript: TranscriptResult,output_dir: Path,base_name: str) -> Path :
    """
    Store transcription (text + timestamps) as a JSON file on disk.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{base_name}_transcript.json"

    data = transcript.model_dump()
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path

