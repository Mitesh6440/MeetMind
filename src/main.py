from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .services.audio_handler import save_audio_file, AudioValidationError
from .services.audio_preprocessing import preprocess_audio_file, AudioPreprocessingError
from .services.stt_service import transcribe_audio_file,save_transcript_to_json,STTError
from .services.team_loader import load_team, TeamDataError
from .services.text_preprocessing import preprocess_transcript
from .services.task_extraction import extract_tasks_from_sentences
from .services.ner import enrich_tasks_with_entities



app = FastAPI(
    title="MeetMind - Meeting Task Assignment",
    version="0.1.0",
    description="API to upload meeting audio and process it step by step.",
)

# Base path for uploads: <project_root>/data/uploads
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
PROCESSED_DIR = UPLOAD_DIR / "processed"
TRANSCRIPTS_DIR = BASE_DIR / "data" / "transcripts"

@app.get("/")
def root():
    return {"message": "MeetMind API is running"}

@app.post("/api/v1/audio/upload")
async def upload_audio(file: UploadFile = File(...)):
    """
    1. Accept an uploaded audio file
    2. Validate + save original
    3. Preprocess (normalize, noise reduction, convert to wav 16k mono)
    4. Run Speech-to-Text on processed audio
    5. Store transcript (with timestamps) to JSON
    """
    try:
        # 1. Read file bytes from UploadFile
        file_bytes = await file.read()

        # 2. Validate + save using our audio handler
        saved_path = save_audio_file(
            original_filename=file.filename,
            file_bytes=file_bytes,
            upload_dir=UPLOAD_DIR,
        )

        # 3. Preprocess audio (normalize, noise reduce, convert to wav 16k mono)
        processed_path = preprocess_audio_file(
            input_path=saved_path,
            output_dir=PROCESSED_DIR,
            enable_noise_reduction=True,   
        )

        # 4. Transcribe audio using STT
        transcript = transcribe_audio_file(processed_path)

        # 5. Store transcript JSON (text + timestamps)
        base_name = processed_path.stem  # e.g. "meeting_processed"
        transcript_path = save_transcript_to_json(
            transcript=transcript,
            output_dir=TRANSCRIPTS_DIR,
            base_name=base_name,
        )

        # 6. Preprocess transcript text 
        preprocessed_sentences = preprocess_transcript(transcript)

        # 7. Identify task-related sentences 
        tasks = extract_tasks_from_sentences(preprocessed_sentences)

        # 8. Enrich task with entites
        tasks = enrich_tasks_with_entities(tasks, preprocessed_sentences)
        # 8. Return info
        return {
            "message": "Audio uploaded, preprocessed, and transcribed successfully",
            "original_filename": file.filename,
            "saved_path": str(saved_path),
            "processed_path": str(processed_path),
            "transcript_path": str(transcript_path),
            "transcript_text": transcript.text,
            "transcript_segments": [seg.model_dump() for seg in transcript.segments],
            "preprocessed_sentences": [
                s.model_dump() for s in preprocessed_sentences[:10]  # send first 10 only
                ],
            "tasks": [t.model_dump() for t in tasks],
        }


    except AudioValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AudioPreprocessingError as e:
        raise HTTPException(status_code=500, detail=f"Preprocessing error: {e}")
    except STTError as e:
        raise HTTPException(status_code=502, detail=f"STT error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
    

@app.get("/api/v1/team")
def get_team():
    try:
        team = load_team()
        return {
            "count": len(team.members),
            "members": [member.model_dump() for member in team.members],
        }
    except TeamDataError as e:
        raise HTTPException(status_code=500, detail=str(e))